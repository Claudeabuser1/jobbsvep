#!/usr/bin/env python3
"""Fetch every open job ad in Stockholms län from the public JobTech APIs
(free, no key) and write compact data files into web/data for the Jobbsvep page.

Sources
  jobsearch.api.jobtechdev.se   Arbetsförmedlingen / Platsbanken (full ads)
  links.api.jobtechdev.se       JobAd Links: ads collected from other Swedish
                                job sites (studentjob.se, company sites ...)

Output
  data/meta.json        fields, chunk list, snapshot time
  data/places.json      place name / street / postcode -> coordinates
  data/i-<f>.json       search index per occupation field (rows as arrays)
  data/d-<f>-<k>.json   full ad details, ~1 MB chunks

Run:  python3 scripts/build_data.py
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timezone

API = "https://jobsearch.api.jobtechdev.se/search"
LINKS = "https://links.api.jobtechdev.se/joblinks"
REGION, REGION_ID = "01", "CifL_Rzy_Mku"  # Stockholms län
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "data")
CHUNK_BYTES = 1_100_000
DESC_CAP = 6000
SNIPPET = 320


def get(base, params):
    url = base + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "jobbsvep-build/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:  # network hiccup: back off and retry
            if attempt == 4:
                raise
            time.sleep(2 + attempt * 3)


def lab(x):
    return (x or {}).get("label") or ""


def clean(s):
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", (s or "").replace("\r", ""))).strip()


def short_emp(label):
    l = label.lower()
    if "tillsvidare" in l: return "Permanent"
    if "sommarjobb" in l or "feriejobb" in l: return "Summer job"
    if "behov" in l: return "On-call"
    if "vikariat" in l: return "Temporary cover"
    if "tidsbegränsad" in l or "säsong" in l: return "Fixed-term"
    return label


def hours(label):
    l = label.lower()
    if "heltid" in l: return "Full-time"
    if "deltid" in l: return "Part-time"
    return label


# ---- how suitable is an ad for someone aged about 16-21 with little experience? ----
YOUTH_OCC = re.compile(r"butik|kassa|kassör|dagligvaror|varuplock|lagerarbet|lagermedarbet|terminalarbet|restaurangbiträde|snabbmat|servitör|servitris|"
                       r"serveringspersonal|diskare|köksbiträde|kaf[ée]biträde|barista|pizzabagare|städare|lokalvårdare|hotellstäd|\bbud\b|cykelbud|"
                       r"tidnings(distribut|bud)|reklamutdelare|brevbärare|kundtjänst|telefonförsäljare|telemarketing|vaktmästare|barnvakt|barnpassning|"
                       r"läxhjälp|fritidsledare|simlärare|siminstruktör|ungdomsledare|personlig assistent|vårdbiträde|parkarbetare|trädgårdsarbet|eventpersonal|"
                       r"promotor|flyttarbet|biltvätt|rekond|frukostvärd|garderob|biograf|nöjespark|glass|kiosk|stationsbiträde|hundrastare|medhjälpare|"
                       r"biträde|extrapersonal|säsongsarbet|plockare|crew|team member|värd(inna)?\b|badvakt|funktionär|flyerutdelare|inventerare", re.I)
YOUTH_HEAD = re.compile(r"sommarjobb|extrajobb|feriejobb|helgjobb|kvällsjobb|ungdom|skolungdom|gymnasie|student|studerande|praktik|lärling|"
                        r"timanställ|extra\b|jobba extra|ingen erfarenhet|no experience|första jobb|trainee|internship|intern\b", re.I)
YOUTH_TEXT = re.compile(r"extrajobb|jobba extra|vid sidan (av|om) (dina |sina )?studier|under studierna|sommarjobb|feriejobb|helgjobb|kvällar och helger|"
                        r"ingen (tidigare )?erfarenhet (krävs|behövs)|inga förkunskaper|vi lär upp dig|upplärning|first job|no experience (needed|required)|"
                        r"student|studerande|gymnasie", re.I)
BLOCK = re.compile(r"sjuksköterska|läkare|undersköterska|barnmorska|tandläkare|tandsköterska|tandhygienist|psykolog|fysioterapeut|arbetsterapeut|socionom|"
                   r"socialsekreterare|kurator|lärare(?! *assistent)|förskollärare|specialpedagog|rektor|ingenjör|arkitekt|jurist|advokat|revisor|controller|"
                   r"ekonom|redovisning|utvecklare|developer|engineer|programmerare|projektledare|\bchef|manager|director|specialist|konsult|elektriker|"
                   r"rörläggare|\bvvs|svetsare|snickare|målare|murare|plåtslagare|mekaniker|tekniker|lastbil|bussförare|taxiförare|väktare|ordningsvakt|"
                   r"\bkock|frisör|optiker|apotekare|farmaceut|handläggare|utredare|forskare|doktorand|analytiker|analyst|senior|erfaren|legitimerad|behörig|"
                   r"adjunkt|professor|biomedicinsk|veterinär|pilot|mäklare|key account|account manager|inköpare|rekryterare|lönespecialist|\blead\b|head of|"
                   r"architect|scientist|\bphd\b|överläkare|skötare|behandlingsassistent|stödpedagog|maskinförare|kranförare|operatör|säkerhetsskyddad|truck|koordinator|samordnare|administratör|fastighetsskötare", re.I)
REQS = re.compile(r"(minst|minimum|least)\s+(\d+|ett|två|tre|fyra|fem|flera|one|two|three|several)\s+(års?|years?)|flerårig|\d\+?\s*years? of|"
                  r"högskole(utbildning|examen)|universitets(utbildning|examen)|akademisk examen|civilingenjör|yrkesbevis|yrkesexamen|legitimation", re.I)
AGE = re.compile(r"(?:fyllt|minst|över|lägst|vara|at least|över)\s*(1[5-9]|2[0-5])\s*(?:år|years)", re.I)
LICENSE = re.compile(r"(b-?körkort|körkort)[^.]{0,30}(krav|krävs|måste|required)|(krav|krävs|kräver)[^.]{0,30}körkort", re.I)


def youth_score(head, occ, text, hrs, exp, edu=False):
    """0-3. 3 = made for young beginners, 2 = likely fine, 1 = no stated barriers, 0 = needs training or experience."""
    hay = head + " " + occ
    if BLOCK.search(hay) or REQS.search(text):
        return 0
    friendly = bool(YOUTH_OCC.search(hay) or YOUTH_HEAD.search(head))
    if friendly and not exp:
        y = 3
    elif friendly or YOUTH_TEXT.search(text):
        y = 2
    elif not exp:
        y = 1
    else:
        y = 0
    return min(y, 1) if edu else y


def min_age(text):
    m = AGE.search(text)
    return int(m.group(1)) if m else 0


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))

    # fixed list: the API's own field statistics sometimes drop a field
    fields = {"X82t_awd_Qyc": "Administration, ekonomi, juridik", "j7Cq_ZJe_GkT": "Bygg och anläggning", "bh3H_Y3h_5eD": "Chefer och verksamhetsledare",
              "apaJ_2ja_LuF": "Data/IT", "RPTn_bxG_ExZ": "Försäljning, inköp, marknadsföring", "PaxQ_o1G_wWH": "Hantverk",
              "ScKy_FHB_7wT": "Hotell, restaurang, storhushåll", "NYW6_mP6_vwf": "Hälso- och sjukvård", "wTEr_CBC_bqh": "Industriell tillverkning",
              "yhCP_AqT_tns": "Installation, drift, underhåll", "Uuf1_GMh_Uvw": "Kropps- och skönhetsvård", "9puE_nYg_crq": "Kultur, media, design",
              "bH5L_uXD_ZAX": "Militära yrken", "VuuL_7CH_adj": "Naturbruk", "MVqp_eS8_kDZ": "Pedagogik", "whao_Q6A_ScE": "Sanering och renhållning",
              "E7hm_BLq_fqZ": "Säkerhet och bevakning", "ASGV_zcE_bWf": "Transport, distribution, lager", "GazW_2TU_kJw": "Yrken med social inriktning",
              "6Hq3_tKo_V57": "Yrken med teknisk inriktning"}
    fields = sorted(fields.items(), key=lambda kv: kv[1])
    field_idx = {name: i for i, (_, name) in enumerate(fields)}

    # ads from other job sites, grouped by field
    extra, offset = defaultdict(list), 0
    while offset <= 2000:
        d = get(LINKS, {"region": REGION_ID, "exclude_source": "arbetsformedlingen.se", "limit": 100, "offset": offset})
        for h in d.get("hits", []):
            fi = field_idx.get(lab(h.get("occupation_field")))
            if fi is not None and h.get("source_links"):
                extra[fi].append(h)
        if len(d.get("hits", [])) < 100:
            break
        offset += 100
        time.sleep(0.15)

    meta = {"built": datetime.now(timezone.utc).isoformat(timespec="seconds"), "region": "Stockholms län",
            "source": "Arbetsförmedlingen Platsbanken + JobAd Links (JobTech open APIs)", "fields": [], "chunks": [],
            "total": 0, "withEmail": 0, "student": 0, "starter": 0, "otherSites": 0, "sources": {}}
    seen, seen_key = set(), set()
    pl_m, pl_s, pl_p = defaultdict(list), defaultdict(list), defaultdict(list)

    for fi, (cid, name) in enumerate(fields):
        hits, offset = [], 0
        while offset <= 2000:
            d = get(API, {"region": REGION, "occupation-field": cid, "limit": 100, "offset": offset, "sort": "pubdate-desc"})
            hits += d["hits"]
            if len(d["hits"]) < 100:
                break
            offset += 100
            time.sleep(0.15)
        hits = [h for h in hits if h["id"] not in seen and not h.get("removed")]
        for h in hits:
            seen.add(h["id"])
        hits.sort(key=lambda h: lab(h.get("occupation_group")))

        index, chunk, size = [], {}, 0

        def flush():
            nonlocal chunk, size
            if not chunk:
                return
            ci = len(meta["chunks"])
            fn = "d-%d-%d.json" % (fi, ci)
            with open(os.path.join(OUT, fn), "w", encoding="utf-8") as fh:
                json.dump(chunk, fh, ensure_ascii=False, separators=(",", ":"))
            meta["chunks"].append(fn)
            chunk, size = {}, 0

        def add(jid, det, row_fn):
            nonlocal size
            det = {k: v for k, v in det.items() if v not in ("", None, [], False)}
            blob = len(json.dumps(det, ensure_ascii=False))
            if size + blob > CHUNK_BYTES:
                flush()
            chunk[jid] = det
            size += blob
            index.append(row_fn(len(meta["chunks"])))

        for h in hits:
            ad = h.get("application_details") or {}
            emp = h.get("employer") or {}
            wa = h.get("workplace_address") or {}
            desc = clean((h.get("description") or {}).get("text"))
            head = clean(h.get("headline"))
            ename = clean(emp.get("name") or emp.get("workplace"))
            seen_key.add((head.lower(), ename.lower()))
            email = (ad.get("email") or "").strip()
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                email = ""
            must, nice = h.get("must_have") or {}, h.get("nice_to_have") or {}
            et, hr = short_emp(lab(h.get("employment_type"))), hours(lab(h.get("working_hours_type")))
            edu = bool((must.get("education") or []) or (must.get("education_level") or []))
            stu = youth_score(head, lab(h.get("occupation")) + " " + lab(h.get("occupation_group")), desc, hr, bool(h.get("experience_required")), edu)
            age = min_age(desc)
            lic = 1 if h.get("driving_license_required") or LICENSE.search(desc) else 0
            co = wa.get("coordinates") or []
            lat = round(co[1], 4) if len(co) == 2 and co[1] else None
            lon = round(co[0], 4) if len(co) == 2 and co[0] else None
            street = clean(wa.get("street_address"))
            if lat and lon:
                if wa.get("municipality"): pl_m[wa["municipality"].lower()].append((lat, lon))
                if wa.get("city"): pl_m[wa["city"].lower()].append((lat, lon))
                if wa.get("postcode"): pl_p[re.sub(r"\D", "", wa["postcode"])].append((lat, lon))
                sname = re.sub(r"\s*\d.*$", "", street).strip().lower()
                if len(sname) > 3: pl_s[sname].append((lat, lon))
            det = {
                "d": desc[:DESC_CAP],
                "email": email, "url": ad.get("url") or "", "ref": ad.get("reference") or "",
                "info": clean(ad.get("information"))[:600], "other": clean(ad.get("other"))[:600],
                "web": h.get("webpage_url") or "", "site": emp.get("url") or "",
                "pc": wa.get("postcode") or "", "city": (wa.get("city") or "").title(),
                "salary": clean(h.get("salary_description"))[:200], "salaryType": lab(h.get("salary_type")),
                "duration": lab(h.get("duration")), "scope": h.get("scope_of_work") or None,
                "vac": h.get("number_of_vacancies") or 1,
                "exp": bool(h.get("experience_required")), "lic": bool(h.get("driving_license_required")),
                "car": bool(h.get("access_to_own_car")), "model": lab(h.get("workplace_model")),
                "must": [x["label"] for k in ("skills", "languages", "work_experiences", "education") for x in must.get(k) or [] if x.get("label")][:12],
                "nice": [x["label"] for k in ("skills", "languages", "work_experiences", "education") for x in nice.get(k) or [] if x.get("label")][:12],
                "contacts": [{k: c.get(k) for k in ("name", "description", "email", "telephone") if c.get(k)} for c in (h.get("application_contacts") or [])][:3],
            }
            add(h["id"], det, lambda ci: [
                h["id"], head, ename, wa.get("municipality") or "", lab(h.get("occupation")), lab(h.get("occupation_group")),
                et, hr, (h.get("publication_date") or "")[:10], (h.get("application_deadline") or "")[:10],
                1 if email else 0, ci, re.sub(r"\s+", " ", desc)[:SNIPPET], lat, lon, street, stu, "", age, lic])
            meta["withEmail"] += 1 if email else 0
            meta["student"] += 1 if stu >= 2 else 0
            meta["starter"] += 1 if stu >= 1 else 0

        for h in extra.get(fi, []):
            head, ename = clean(h.get("headline")), clean((h.get("employer") or {}).get("name"))
            key = (head.lower(), ename.lower())
            if not head or key in seen_key:
                continue
            seen_key.add(key)
            src = h["source_links"][0]
            wa = (h.get("workplace_addresses") or [{}])[0]
            brief = clean(h.get("brief"))
            stu = youth_score(head, lab(h.get("occupation_group")), brief + (" student" if "student" in (src.get("label") or "") else ""), "", False)
            jid = "x" + h["id"][:15]
            add(jid, {"d": brief, "url": src.get("url") or "", "web": src.get("url") or ""}, lambda ci: [
                jid, head, ename, wa.get("municipality") or "", lab(h.get("occupation_group")), lab(h.get("occupation_group")),
                "", "", (h.get("publication_date") or "")[:10], "", 0, ci, re.sub(r"\s+", " ", brief)[:SNIPPET],
                None, None, "", stu, src.get("label") or "annan sajt", min_age(brief), 1 if LICENSE.search(brief) else 0])
            meta["otherSites"] += 1
            meta["student"] += 1 if stu >= 2 else 0
            meta["sources"][src.get("label") or "?"] = meta["sources"].get(src.get("label") or "?", 0) + 1

        flush()
        with open(os.path.join(OUT, "i-%d.json" % fi), "w", encoding="utf-8") as fh:
            json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))
        meta["fields"].append({"name": name, "count": len(index)})
        meta["total"] += len(index)
        print("%-45s %5d" % (name, len(index)), file=sys.stderr)

    # ads collected from JobTeaser's public Stockholm listing (title, employer, contract, place and link only)
    jt_path = os.path.join(ROOT, "jobteaser.json")  # optional, not kept in the repo
    if os.path.exists(jt_path):
        CT = [("part-time", "Extrajobb / studentjobb", "Part-time"), ("internship", "Praktik", ""), ("graduate", "Traineeprogram", ""),
              ("thesis", "Examensarbete", ""), ("apprentice", "Lärlingsplats", ""), ("vie", "Internationell traineeplats (VIE)", ""),
              ("fixed-term", "Visstidsanställning", ""), ("full time", "Heltidstjänst", "Full-time"), ("freelance", "Frilans", "")]
        fi, index, chunk = len(meta["fields"]), [], {}
        ci, today = len(meta["chunks"]), datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for a in json.load(open(jt_path, encoding="utf-8")):
            head, ename, url = clean(a.get("h")), clean(a.get("e")), a.get("u") or ""
            m = re.search(r"job-offers/([0-9a-f-]{36})", url)
            key = (head.lower(), ename.lower())
            if not head or not m or key in seen_key:
                continue
            seen_key.add(key)
            ct = clean(a.get("ct"))
            label, hr = next(((l, h) for k, l, h in CT if k in ct.lower()), (ct or "Jobb", ""))
            dur = re.search(r"(\d+(?: to \d+)?) months", ct)
            if dur: label += ", " + dur.group(1).replace(" to ", "–") + " mån"
            loc = clean(a.get("loc"))
            muni = "" if loc.lower().startswith("multiple") else re.sub(r"\s+Municipality$", "", loc.split(",")[0]).strip()
            stu = youth_score(head, label, "student" if label not in ("Heltidstjänst", "Visstidsanställning", "Frilans") else "", hr, False)
            jid = "jt" + m.group(1).replace("-", "")[:14]
            full = "https://www.jobteaser.com" + url if url.startswith("/") else url
            chunk[jid] = {"d": "Hela annonsen finns på JobTeaser. Öppna den för att läsa mer och ansöka.", "url": full, "web": full}
            index.append([jid, head, ename, muni, label, "", "", hr, today, "", 0, ci, label + (" · " + loc if loc else "") + ". Hela annonsen finns på JobTeaser.",
                          None, None, "", stu, "jobteaser.com", 0, 0])
            meta["student"] += 1 if stu >= 2 else 0
        if index:
            fn = "d-%d-%d.json" % (fi, ci)
            json.dump(chunk, open(os.path.join(OUT, fn), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            meta["chunks"].append(fn)
            json.dump(index, open(os.path.join(OUT, "i-%d.json" % fi), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            meta["fields"].append({"name": "Praktik, trainee och studentjobb", "count": len(index)})
            meta["total"] += len(index); meta["otherSites"] += len(index); meta["sources"]["jobteaser.com"] = len(index)
            print("%-45s %5d" % ("JobTeaser", len(index)), file=sys.stderr)

    avg = lambda pts: [round(sum(p[0] for p in pts) / len(pts), 4), round(sum(p[1] for p in pts) / len(pts), 4)]
    places = {"m": {k: avg(v) for k, v in pl_m.items()}, "s": {k: avg(v) for k, v in pl_s.items()}, "p": {k: avg(v) for k, v in pl_p.items()}}
    with open(os.path.join(OUT, "places.json"), "w", encoding="utf-8") as fh:
        json.dump(places, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, separators=(",", ":"))
    tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print("total %d, email %d, youth-friendly %d (no barriers %d), other sites %d %s, files %d, %.1f MB" % (
        meta["total"], meta["withEmail"], meta["student"], meta["starter"], meta["otherSites"], meta["sources"], len(os.listdir(OUT)), tot / 1e6), file=sys.stderr)


if __name__ == "__main__":
    main()
