#!/usr/bin/env python3
"""Fetch shops, cafés, restaurants, hotels and similar workplaces in Stockholm county
from OpenStreetMap (Overpass API) and write web/pois.json for the "Gå dit" view.

Data © OpenStreetMap contributors, ODbL. Run now and then: python3 scripts/build_places.py
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
BBOX = (58.75, 17.25, 60.25, 19.35)  # south, west, north, east: Stockholm county, roughly
GRID = 4  # fetched as GRID x GRID tiles; small boxes answer in seconds where one big area query times out
# (label shown in the app, Overpass filters)
TYPES = [
    ("Mataffär", ['"shop"~"^(supermarket|convenience)$"']),
    ("Butik", ['"shop"~"^(clothes|shoes|sports|electronics|books|toys|department_store|cosmetics|gift|interior_decoration|furniture|pet|bicycle|outdoor|variety_store|second_hand|florist|chemist|stationery|mobile_phone|jewelry)$"']),
    ("Kafé och bageri", ['"amenity"="cafe"', '"shop"~"^(bakery|pastry)$"', '"amenity"="ice_cream"']),
    ("Snabbmat", ['"amenity"="fast_food"']),
    ("Restaurang", ['"amenity"~"^(restaurant|pub|bar)$"']),
    ("Hotell", ['"tourism"~"^(hotel|hostel)$"']),
    ("Fritid och nöje", ['"leisure"~"^(fitness_centre|sports_centre|bowling_alley|amusement_arcade|water_park|trampoline_park)$"', '"amenity"="cinema"', '"tourism"="theme_park"']),
    ("Bensinstation", ['"amenity"="fuel"']),
]


def overpass(query):
    """The public Overpass servers are often busy: fail fast and keep retrying for a while."""
    last = None
    for attempt in range(12):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": query}).encode(),
                                             headers={"user-agent": "jobbsvep-build/1.0 (github.com/Claudeabuser1/jobbsvep)"})
                with urllib.request.urlopen(req, timeout=75) as r:
                    return json.load(r)
            except Exception as e:
                last = e
        time.sleep(min(60, 6 + attempt * 6))
    raise last


def type_of(tags):
    """Index into TYPES for an element's tags, or None."""
    for ti, (_, filters) in enumerate(TYPES):
        for f in filters:
            key, _, val = f.partition("~") if "~" in f else f.partition("=")
            key, val = key.strip('"'), val.strip('"')
            v = tags.get(key)
            if v and (re.match(val, v) if "~" in f else v == val):
                return ti
    return None


def main():
    s, w, n, e = BBOX
    rows, seen, counts = [], set(), [0] * len(TYPES)
    for i in range(GRID):
        for k in range(GRID):
            box = "%.4f,%.4f,%.4f,%.4f" % (s + (n - s) * i / GRID, w + (e - w) * k / GRID, s + (n - s) * (i + 1) / GRID, w + (e - w) * (k + 1) / GRID)
            elements = []
            for _, fs in TYPES:  # one small query per type keeps each request light
                parts = "".join('nwr[%s]["name"];' % f for f in fs)
                elements += overpass("[out:json][timeout:60][bbox:%s];(%s);out center tags;" % (box, parts)).get("elements", [])
                time.sleep(1)
            for el in elements:
                t = el.get("tags", {})
                lat = el.get("lat") or (el.get("center") or {}).get("lat")
                lon = el.get("lon") or (el.get("center") or {}).get("lon")
                name, ti = (t.get("name") or "").strip(), type_of(t)
                if not name or not lat or not lon or ti is None or t.get("access") == "private":
                    continue
                key = (name.lower(), round(lat, 3), round(lon, 3))
                if key in seen:
                    continue
                seen.add(key)
                street = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
                rows.append([name[:60], ti, round(lat, 5), round(lon, 5), street[:50]])
                counts[ti] += 1
            print("tile %d/%d: %d places so far" % (i * GRID + k + 1, GRID * GRID, len(rows)), file=sys.stderr, flush=True)
            time.sleep(1.5)
    for (label, _), c in zip(TYPES, counts):
        print("%-18s %5d" % (label, c), file=sys.stderr)
    out = {"built": time.strftime("%Y-%m-%d"), "source": "© OpenStreetMap contributors (ODbL)", "types": [t[0] for t in TYPES], "places": rows}
    path = os.path.join(ROOT, "web", "pois.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("%d places, %.1f MB" % (len(rows), os.path.getsize(path) / 1e6), file=sys.stderr)


if __name__ == "__main__":
    main()
