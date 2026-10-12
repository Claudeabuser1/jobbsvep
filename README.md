# Jobbsvep

Swipe-to-apply job search for students in Stockholm. You describe what you want, add your CV and an example of how you write, then swipe through matching jobs. Swiping right drafts an application in your voice that you review and send.

This repository holds the working prototype and is the starting point for turning it into a real website, and later an app.

## What is here

| Path | What it is |
| --- | --- |
| `web/jobbsvep.html` | The whole prototype app in one file (markup, styles, script). UI copy is Swedish. |
| `scripts/build_data.py` | Fetches open job ads for Stockholm county and writes compact data files to `web/data/`. |
| `extension/` | Chrome extension that fills in application forms with your details, CV and drafted letter. |
| `docs/design-handoff/` | The design spec ("2b Svep först") the UI follows. |

## How the prototype works

The prototype runs as a Claude artifact, not as a normal website. `web/jobbsvep.html` is a page fragment (no `<html>` or `<head>`) that the artifact host wraps, and it relies on that host for four things:

- **AI** (matching, ranking, drafting letters, reading imported ads, LinkedIn profile text) through `window.claude.use("sample")`.
- **Sending email** through the viewer's Gmail connector, `window.claude.use("mcp")`.
- **Saved state** (profile, applications, shared imported ads) through `window.claude.use("db")` and `use("user")`.
- **Job data** as static files in `web/data/`, published next to the page.

Opened outside that host, the page still loads and you can swipe with keyword matching, but there is no AI, no sending and no account sync.

## Run it locally

```bash
python3 scripts/build_data.py
```

```bash
cd web && printf '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}[hidden]{display:none!important}</style>' | cat - jobbsvep.html > index.html && python3 -m http.server 8765
```

Then open http://localhost:8765/.

## Job data

`build_data.py` uses two free, open APIs from JobTech (Arbetsförmedlingen), no key needed:

- `jobsearch.api.jobtechdev.se` – all Platsbanken ads for Stockholm county, with full text, application email or link, and coordinates.
- `links.api.jobtechdev.se` – ads collected from other Swedish job sites (studentjob.se, ledigajobb.se, thehub.io and others), title and link only.

The data is a snapshot from when the script ran. It is not committed; rebuild it. An earlier snapshot also included a one-off listing from JobTeaser, which is deliberately not in this repository because their site rules do not allow automated collection.

## Chrome extension

Load `extension/` via `chrome://extensions` → Developer mode → Load unpacked. See `extension/README.txt`. It never submits a form, never ticks checkboxes and skips identity-number and password fields.

## What a real website needs

The prototype leans on the artifact host. A standalone site has to replace each piece:

1. **Backend and accounts** – sign-in, and a database for profiles, applications and imported ads.
2. **AI** – server-side calls to the Claude API with your own key (never from the browser).
3. **Email** – sending from the user's own address (Gmail/Outlook OAuth), or a transactional mail service with reply-to.
4. **Job data** – run `build_data.py` on a schedule and serve the ads from the database instead of static files.
5. **Frontend** – split `jobbsvep.html` into components (the design handoff suggests React + TypeScript).
6. **Privacy** – CVs and applications are personal data, so GDPR basics: consent, deletion, a privacy policy.
7. **LinkedIn** – no public API for reading or editing profiles; keep the upload-your-PDF flow.

## Status

Tested locally: job loading, keyword matching, swiping, save, ad sheet, distance and map links, text import, the extension's form-filling logic. Not yet exercised end to end: AI ranking and drafting, Gmail sending, account sync, screenshot import, the extension's popup in Chrome.
