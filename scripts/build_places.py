#!/usr/bin/env python3
"""Fetch shops, cafés, restaurants, hotels and similar workplaces in Stockholm county
from OpenStreetMap (Overpass API) and write web/pois.json for the "Gå dit" view.

Data © OpenStreetMap contributors, ODbL. Run now and then: python3 scripts/build_places.py
"""
import json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]
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
    last = None
    for attempt in range(3):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": query}).encode(),
                                             headers={"user-agent": "jobbsvep-build/1.0 (github.com/Claudeabuser1/jobbsvep)"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r)
            except Exception as e:  # busy mirror: try the next one
                last = e
        time.sleep(10 + attempt * 20)
    raise last


def main():
    rows, seen = [], set()
    for ti, (label, filters) in enumerate(TYPES):
        parts = "".join('nwr[%s]["name"](area.a);' % f for f in filters)
        d = overpass('[out:json][timeout:150];area["ISO3166-2"="SE-AB"]->.a;(%s);out center tags;' % parts)
        n = 0
        for e in d.get("elements", []):
            t = e.get("tags", {})
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lon = e.get("lon") or (e.get("center") or {}).get("lon")
            name = (t.get("name") or "").strip()
            if not name or not lat or not lon or t.get("disused") or t.get("access") == "private":
                continue
            key = (name.lower(), round(lat, 3), round(lon, 3))
            if key in seen:
                continue
            seen.add(key)
            street = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
            rows.append([name[:60], ti, round(lat, 5), round(lon, 5), street[:50]])
            n += 1
        print("%-18s %5d" % (label, n), file=sys.stderr)
        time.sleep(3)
    out = {"built": time.strftime("%Y-%m-%d"), "source": "© OpenStreetMap contributors (ODbL)", "types": [t[0] for t in TYPES], "places": rows}
    path = os.path.join(ROOT, "web", "pois.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("%d places, %.1f MB" % (len(rows), os.path.getsize(path) / 1e6), file=sys.stderr)


if __name__ == "__main__":
    main()
