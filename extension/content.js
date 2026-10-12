// Jobbsvep content script. Runs in every frame.
// 1. Fills job application forms when the popup asks (never submits, never ticks boxes).
// 2. Picks up profile + drafted applications from the Jobbsvep page when it is open.
(() => {
  if (globalThis.__jobbsvepLoaded) return;
  globalThis.__jobbsvepLoaded = true;
  const store = typeof chrome !== "undefined" && chrome.storage ? chrome.storage.local : null;

  /* ---------- sync from the Jobbsvep page ---------- */
  let lastBridge = "";
  function syncBridge() {
    const el = document.getElementById("jobbsvep-bridge");
    if (!el || !store || el.textContent === lastBridge) return;
    lastBridge = el.textContent;
    try {
      const d = JSON.parse(lastBridge);
      if (!d || d.v !== 1) return;
      store.get("jobbsvep", (r) => {
        const cur = r.jobbsvep || {};
        const profile = Object.assign({}, cur.profile || {});
        for (const k of ["name", "email", "phone", "linkedin"]) if (d.profile && d.profile[k]) profile[k] = d.profile[k];
        store.set({ jobbsvep: Object.assign({}, cur, { profile, apps: Array.isArray(d.apps) ? d.apps : [], synced: Date.now() }) });
      });
    } catch (_) {}
  }
  if (/claude/i.test(location.hostname) || document.getElementById("jobbsvep-bridge")) {
    syncBridge();
    setInterval(syncBridge, 3000);
  }

  /* ---------- form filling ---------- */
  const RULES = [
    ["skip", /person(al)?.?n(umme)?r|social.?security|ssn|national.?id|födelse|birth|password|lösenord|captcha|salary|lön(e|$)|otp|verification/],
    ["email", /e-?mail|e-?post|epost/],
    ["linkedin", /linkedin/],
    ["first", /first.?name|given.?name|f(ö|o)rnamn|fname|vorname|prenom/],
    ["last", /last.?name|family.?name|surname|efternamn|lname|nachname/],
    ["phone", /phone|telefon|mobil|\btel\b|cell/],
    ["postcode", /zip|postal|post.?code|postnummer|postnr/],
    ["city", /\bcity\b|\bort\b|\bstad\b|postort|town|locality/],
    ["street", /street|address|adress|gatuadress/],
    ["website", /website|webbplats|hemsida|portfolio|homepage|github/],
    ["country", /country|\bland\b/],
    ["letter", /cover|letter|personligt brev|\bbrev\b|message|meddelande|motivation|why|varf(ö|o)r|about you|om dig|ber(ä|a)tta|presentation|introduc|additional|övrigt/],
    ["name", /full.?name|\bname\b|\bnamn\b/],
  ];
  function descriptor(el) {
    const parts = [el.name, el.id, el.getAttribute("autocomplete"), el.placeholder, el.getAttribute("aria-label"), el.getAttribute("data-testid")];
    if (el.labels) for (const l of el.labels) parts.push(l.textContent);
    const lb = el.getAttribute("aria-labelledby");
    if (lb) for (const id of lb.split(/\s+/)) { const n = document.getElementById(id); if (n) parts.push(n.textContent); }
    if (!el.labels || !el.labels.length) {
      const wrap = el.closest("label, .field, .form-group, .form-field, [class*=field], [class*=Field], li, p, div");
      if (wrap && wrap.textContent.length < 160) parts.push(wrap.textContent);
    }
    return parts.filter(Boolean).join(" ").replace(/\s+/g, " ").toLowerCase().slice(0, 300);
  }
  function kindOf(el) {
    const type = (el.type || "").toLowerCase(), ac = (el.getAttribute("autocomplete") || "").toLowerCase();
    if (ac === "given-name") return "first";
    if (ac === "family-name") return "last";
    if (ac === "name") return "name";
    if (ac === "postal-code") return "postcode";
    if (ac === "address-level2") return "city";
    if (ac.startsWith("street-address") || ac === "address-line1") return "street";
    const d = descriptor(el);
    if (RULES[0][1].test(d)) return "skip";
    if (type === "email") return "email";
    if (type === "tel") return "phone";
    for (const [k, re] of RULES) {
      if (k === "letter" && el.tagName !== "TEXTAREA") continue;
      if (re.test(d)) return k;
    }
    if (el.tagName === "TEXTAREA") return "letter";
    return null;
  }
  function setValue(el, v) {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : el.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    el.focus();
    setter.call(el, v);
    for (const t of ["input", "change", "blur"]) el.dispatchEvent(new Event(t, { bubbles: true }));
  }
  function mark(el) { el.style.outline = "2px solid #5b4fd6"; el.style.outlineOffset = "1px"; }
  function visible(el) { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden"; }

  globalThis.__jobbsvepFill = async function (data) {
    const p = data.profile || {}, nameParts = String(p.name || "").trim().split(/\s+/);
    const val = {
      email: p.email, phone: p.phone, linkedin: p.linkedin, website: p.website, street: p.street, postcode: p.postcode, city: p.city,
      name: p.name, first: nameParts[0] || "", last: nameParts.slice(1).join(" "), letter: data.letter || "",
    };
    let filled = 0, files = 0, letterDone = false;
    const els = [...document.querySelectorAll("input, textarea, select")];
    for (const el of els) {
      const type = (el.type || "").toLowerCase();
      if (el.disabled || el.readOnly || ["hidden", "password", "checkbox", "radio", "submit", "button", "search", "image", "reset"].includes(type)) continue;
      if (type === "file") {
        if (!data.cv || el.files.length) continue;
        const d = descriptor(el);
        if (/photo|bild|avatar|picture|logo/.test(d) && !/cv|resume/.test(d)) continue;
        try {
          const bin = atob(data.cv.b64), buf = new Uint8Array(bin.length);
          for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
          const dt = new DataTransfer();
          dt.items.add(new File([buf], data.cv.name, { type: data.cv.type || "application/pdf" }));
          el.files = dt.files;
          for (const t of ["input", "change"]) el.dispatchEvent(new Event(t, { bubbles: true }));
          files++;
          if (el.parentElement) mark(el.parentElement);
        } catch (_) {}
        continue;
      }
      if (!visible(el) || (el.value && el.tagName !== "SELECT")) continue;
      const k = kindOf(el);
      if (!k || k === "skip") continue;
      if (el.tagName === "SELECT") {
        if (k !== "country" || el.selectedIndex > 0) continue;
        const o = [...el.options].find((o) => /^(sverige|sweden)$/i.test(o.textContent.trim()));
        if (o) { setValue(el, o.value); mark(el); filled++; }
        continue;
      }
      if (k === "country") { setValue(el, document.documentElement.lang.startsWith("sv") ? "Sverige" : "Sweden"); mark(el); filled++; continue; }
      if (k === "letter") { if (letterDone || !val.letter) continue; letterDone = true; }
      if (!val[k]) continue;
      setValue(el, val[k]); mark(el); filled++;
    }
    return { filled, files, fields: els.length };
  };

  globalThis.__jobbsvepGrab = function () {
    const sel = String(getSelection() || "").trim();
    const main = document.querySelector("main, [role=main], article") || document.body;
    const text = (sel.length > 80 ? sel : main.innerText || "").replace(/\n{3,}/g, "\n\n").trim().slice(0, 8000);
    return { title: document.title, url: location.href, text };
  };
})();
