#!/usr/bin/env python3
"""Assemble the public website into ./site from web/jobbsvep.html plus the data files.

Environment (all optional):
  JOBBSVEP_API   base URL of the AI server (server/), e.g. https://api.example.se
  SITE_DOMAIN    custom domain for GitHub Pages; writes site/CNAME

Run:  python3 scripts/build_site.py
"""
import html, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
ICON = "data:image/svg+xml," + "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%235b4fd6'/%3E%3Ctext x='50' y='70' font-family='sans-serif' font-size='62' font-weight='800' fill='%23fff' text-anchor='middle'%3Ej%3C/text%3E%3C/svg%3E"
DESC = "Extrajobb, sommarjobb och första jobbet nära dig i Stockholm. Svep höger så skrivs ansökan åt dig."


def main():
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(SITE)
    page = open(os.path.join(ROOT, "web", "jobbsvep.html"), encoding="utf-8").read()
    api = html.escape(os.environ.get("JOBBSVEP_API", "").strip(), quote=True)
    head = ('<!doctype html><html lang="sv"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="description" content="%s"><meta property="og:title" content="Jobbsvep">'
            '<meta property="og:description" content="%s"><meta name="theme-color" content="#5b4fd6">'
            '<meta name="jobbsvep-api" content="%s"><link rel="icon" href="%s">'
            '<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%%}'
            ':root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>'
            '</head><body>') % (DESC, DESC, api, ICON)
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(head + page + "</body></html>")
    data = os.path.join(ROOT, "web", "data")
    if os.path.isdir(data):
        shutil.copytree(data, os.path.join(SITE, "data"))
    pois = os.path.join(ROOT, "web", "pois.json")
    if os.path.exists(pois):
        shutil.copy(pois, SITE)
    domain = os.environ.get("SITE_DOMAIN", "").strip()
    if domain:
        open(os.path.join(SITE, "CNAME"), "w").write(domain + "\n")
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(SITE) for f in fs)
    print("site built: %.1f MB%s%s" % (size / 1e6, ", API " + api if api else ", no AI server configured", ", domain " + domain if domain else ""))


if __name__ == "__main__":
    main()
