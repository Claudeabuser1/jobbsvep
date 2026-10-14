#!/usr/bin/env python3
"""Translate web/jobbsvep.html into another language at build time.

The dictionary (web/i18n/<lang>.json) maps whole Swedish texts to translations. A text is only
replaced where it stands on its own: a complete string literal ("..." or '...'), a complete
attribute value, or a complete text node between tags. Parts of words are never touched.
Regions between i18n-skip-start and i18n-skip-end markers are left as they are.

  python3 scripts/i18n.py en            # writes nothing, prints missing and leftover texts
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = re.compile(r"(<!--i18n-skip-start-->.*?<!--i18n-skip-end-->|/\*i18n-skip-start\*/.*?/\*i18n-skip-end\*/)", re.S)
SWEDISH_HINT = re.compile(r"[åäöÅÄÖ]|\b(och|att|jobb|jobbet|jobben|du|dig|din|ditt|dina|är|för|med|som|inte|eller|på|till|av|ett|det|vi|har|kan|ska|här|kvar|ingen|inga|alla|nu|så|vill|när|mer|fler|Skicka|Spara|Hej|Visa|Kopiera|Annonsen|Karta|Ansök|Nytt|Gratis|Vecka|Månad|Profil|Svepa|Hjälp|Villkor|Kontakt|Tillbaka|Avbryt|Namn|Telefon|Plats|Krav|Rubrik|Svep|Butik|Hotell|Restaurang|Snabbmat|Sommarjobb|Deltid|Heltid|Tillsvidare|Visstid|Vikariat|Skickar|Skrivs|Skickad|Referens)\b")


def load(lang):
    return json.load(open(os.path.join(ROOT, "web", "i18n", lang + ".json"), encoding="utf-8"))


def esc_for(delim, text):
    if delim in ("'", '"'):
        return text.replace("\\", "\\\\").replace(delim, "\\" + delim) if delim in text else text
    return text


def translate(src, table):
    parts = SKIP.split(src)
    used = set()
    keys = sorted(table, key=len, reverse=True)
    for i in range(0, len(parts), 2):  # even parts are translatable, odd parts are skipped regions
        seg = parts[i]
        for k in keys:
            v = table[k]
            if v is None or k not in seg:
                continue
            ek = re.escape(k)
            new, n1 = re.subn(r'(["\'])' + ek + r'\1', lambda m: m.group(1) + esc_for(m.group(1), v) + m.group(1), seg)
            new, n2 = re.subn(r">(\s*)" + ek + r"(\s*)<", lambda m: ">" + m.group(1) + v + m.group(2) + "<", new)
            if n1 or n2:
                used.add(k)
                seg = new
        parts[i] = seg
    return "".join(parts), used


def leftovers(out):
    """Texts in the translated page that still look Swedish (skipped regions excluded)."""
    found = set()
    body = SKIP.sub("", out)
    cut = body.find("<script>")
    markup, script = (body[:cut], body[cut:]) if cut >= 0 else (body, "")
    markup = re.sub(r"<style>.*?</style>", "", markup, flags=re.S)
    pieces = [m.group(1) for m in re.finditer(r">([^<>]+)<", markup)]
    pieces += [m.group(1) for m in re.finditer(r'(?:placeholder|aria-label|title|content)="([^"]+)"', markup)]
    for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'', script):
        lit = m.group(1) if m.group(1) is not None else m.group(2)
        texts = [x for x in re.findall(r">([^<>]+)<", lit)] if "<" in lit else []
        pieces += texts or [lit]
        if "<" in lit:  # text before the first tag or after the last tag in an html fragment
            pieces += [lit.split("<", 1)[0], lit.rsplit(">", 1)[-1]]
    for t in pieces:
        t = t.strip()
        if t and SWEDISH_HINT.search(t) and not t.startswith(("http", "data:")):
            found.add(t)
    return found


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    d = load(lang)
    src = open(os.path.join(ROOT, "web", "jobbsvep.html"), encoding="utf-8").read()
    out, used = translate(src, d["strings"])
    missing = [k for k in d["strings"] if k not in used]
    left = sorted(leftovers(out) - set(d.get("keep", [])))
    print("%d texts translated, %d dictionary entries not found, %d possible Swedish texts left" % (len(used), len(missing), len(left)))
    for k in missing:
        print("  NOT FOUND:", repr(k)[:140])
    for t in left:
        print("  LEFT:", repr(t)[:160])


if __name__ == "__main__":
    main()
