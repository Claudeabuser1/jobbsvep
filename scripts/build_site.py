#!/usr/bin/env python3
"""Assemble the public website into ./site from web/jobbsvep.html plus the data files.

Environment (all optional):
  JOBBSVEP_API   base URL of the AI server (server/), e.g. https://api.example.se
  SITE_DOMAIN    custom domain for GitHub Pages; writes site/CNAME
  CONTACT_EMAIL  shown on the help page
  OWNER_NAME     name of the person or company running Jobbsvep (privacy policy)

Run:  python3 scripts/build_site.py
"""
import html, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
ICON = "data:image/svg+xml," + "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%235b4fd6'/%3E%3Ctext x='50' y='70' font-family='sans-serif' font-size='62' font-weight='800' fill='%23fff' text-anchor='middle'%3Ej%3C/text%3E%3C/svg%3E"
DESC = "Extrajobb, sommarjobb och första jobbet nära dig i Stockholm. Svep höger så skrivs ansökan åt dig."
DESC_EN = "Extra work, summer jobs and your first job near you in Stockholm. Swipe right and your application is written for you."


def main():
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(SITE)
    page = open(os.path.join(ROOT, "web", "jobbsvep.html"), encoding="utf-8").read()
    api = html.escape(os.environ.get("JOBBSVEP_API", "").strip(), quote=True)
    contact = html.escape(os.environ.get("CONTACT_EMAIL", "").strip(), quote=True)
    owner = html.escape(os.environ.get("OWNER_NAME", "").strip(), quote=True)

    def wrap(body, lang, base, desc):
        head = ('<!doctype html><html lang="%s"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                '<meta name="description" content="%s"><meta property="og:title" content="Jobbsvep">'
                '<meta property="og:description" content="%s"><meta name="theme-color" content="#5b4fd6">'
                '<meta name="jobbsvep-api" content="%s"><meta name="jobbsvep-contact" content="%s"><meta name="jobbsvep-owner" content="%s">'
                '<meta name="jobbsvep-lang" content="%s"><meta name="jobbsvep-base" content="%s">'
                '<link rel="alternate" hreflang="sv" href="%s"><link rel="alternate" hreflang="en" href="%sen/"><link rel="icon" href="%s">'
                '<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%%}'
                ':root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>'
                '</head><body>') % (lang, desc, desc, api, contact, owner, lang, base, base or "./", base or "./", ICON)
        return head + body + "</body></html>"

    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(wrap(page, "sv", "", DESC))
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import i18n
    en, _ = i18n.translate(page, i18n.load("en")["strings"])
    os.makedirs(os.path.join(SITE, "en"))
    open(os.path.join(SITE, "en", "index.html"), "w", encoding="utf-8").write(wrap(en, "en", "../", DESC_EN))
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
