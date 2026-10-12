const $ = (id) => document.getElementById(id);
const FIELDS = ["name", "email", "phone", "street", "postcode", "city", "linkedin", "website"];
let state = { profile: {}, apps: [], cv: null, synced: 0 };

function render() {
  for (const k of FIELDS) $(k).value = state.profile[k] || "";
  $("cvname").textContent = state.cv ? "Sparad: " + state.cv.name : "Ingen CV-fil sparad än.";
  $("sync").textContent = state.synced
    ? "Synkad med Jobbsvep " + new Date(state.synced).toLocaleString("sv-SE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) + " · " + state.apps.length + " ansökningar"
    : "Inte synkad med Jobbsvep än. Öppna Jobbsvep i en flik, eller fyll i dina uppgifter nedan.";
  const sel = $("app"), cur = sel.value;
  sel.length = 1;
  for (const a of state.apps) sel.add(new Option((a.e || "") + " – " + (a.h || ""), a.id));
  sel.value = cur;
  if (!state.profile.name && !state.profile.email) $("me").open = true;
}
const save = () => chrome.storage.local.set({ jobbsvep: state });
async function tab() { const [t] = await chrome.tabs.query({ active: true, currentWindow: true }); return t; }

chrome.storage.local.get("jobbsvep", async (r) => {
  state = Object.assign(state, r.jobbsvep || {});
  render();
  // preselect the application whose employer appears in the tab's title or address
  const t = await tab(), hay = ((t && t.title) || "") + " " + ((t && t.url) || "");
  const hit = state.apps.find((a) => { const w = String(a.e || "").split(/\s+/)[0]; return w.length > 2 && hay.toLowerCase().includes(w.toLowerCase()); });
  if (hit) $("app").value = hit.id;
});
for (const k of FIELDS) $(k).addEventListener("change", () => { state.profile[k] = $(k).value.trim(); save(); });

$("cv").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return;
  if (f.size > 8 * 1024 * 1024) { $("status").textContent = "Filen är större än 8 MB."; return; }
  const buf = new Uint8Array(await f.arrayBuffer()); let s = "";
  for (let i = 0; i < buf.length; i += 8192) s += String.fromCharCode.apply(null, buf.subarray(i, i + 8192));
  state.cv = { name: f.name, type: f.type, b64: btoa(s) }; save(); render();
});

$("load").addEventListener("click", () => {
  try {
    const d = JSON.parse($("paste").value);
    if (!d || d.v !== 1) throw 0;
    for (const k of ["name", "email", "phone", "linkedin"]) if (d.profile && d.profile[k]) state.profile[k] = d.profile[k];
    state.apps = Array.isArray(d.apps) ? d.apps : []; state.synced = Date.now();
    save(); render(); $("paste").value = ""; $("status").textContent = "Inläst.";
  } catch (_) { $("status").textContent = "Det där såg inte ut som data från Jobbsvep."; }
});

$("fill").addEventListener("click", async () => {
  const t = await tab(), a = state.apps.find((x) => x.id === $("app").value);
  $("status").textContent = "Fyller i…";
  try {
    const res = await chrome.scripting.executeScript({
      target: { tabId: t.id, allFrames: true },
      func: (d) => (globalThis.__jobbsvepFill ? globalThis.__jobbsvepFill(d) : null),
      args: [{ profile: state.profile, letter: a ? a.body : "", cv: state.cv }],
    });
    let filled = 0, files = 0;
    for (const r of res) if (r.result) { filled += r.result.filled; files += r.result.files; }
    $("status").textContent = filled || files
      ? "Fyllde i " + filled + " fält" + (files ? " och bifogade ditt CV" : "") + ". Kontrollera allt innan du skickar."
      : "Hittade inga tomma fält att fylla i på den här sidan.";
  } catch (e) { $("status").textContent = "Det går inte att fylla i på den här sidan. Ladda om sidan och försök igen."; }
});

$("grab").addEventListener("click", async () => {
  const t = await tab();
  try {
    const [r] = await chrome.scripting.executeScript({ target: { tabId: t.id }, func: () => (globalThis.__jobbsvepGrab ? globalThis.__jobbsvepGrab() : null) });
    if (!r || !r.result || !r.result.text) throw 0;
    await navigator.clipboard.writeText(r.result.title + "\n" + r.result.url + "\n\n" + r.result.text);
    $("status").textContent = "Kopierad. Klistra in den under Importera en annons i Jobbsvep.";
  } catch (e) { $("status").textContent = "Kunde inte läsa sidan. Markera annonstexten och kopiera den själv."; }
});
