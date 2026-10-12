# Jobbsvep

Swipe-to-apply job search for students in Stockholm. You describe what you want, add your CV and an example of how you write, then swipe through matching jobs. Swiping right drafts an application in your voice that you review and send.

This repository holds the working prototype and is the starting point for turning it into a real website, and later an app.

## What is here

| Path | What it is |
| --- | --- |
| `web/jobbsvep.html` | The whole app in one file (markup, styles, script). UI copy is Swedish. |
| `web/pois.json` | Shops, cafés, restaurants and similar walk-in workplaces in Stockholm county, from OpenStreetMap. |
| `scripts/build_data.py` | Fetches open job ads for Stockholm county, scores each for how suitable it is for a 16-21 year old beginner, and writes `web/data/`. |
| `scripts/build_places.py` | Rebuilds `web/pois.json` from OpenStreetMap. |
| `scripts/build_site.py` | Wraps the app into a normal web page and assembles `site/` for hosting. |
| `.github/workflows/update.yml` | Rebuilds the job data every Monday and Thursday and deploys the site to GitHub Pages. |
| `server/` | Small Node server that forwards AI requests to the Claude API, so the key never reaches the browser. |
| `extension/` | Chrome extension that fills in application forms with your details, CV and drafted letter. |
| `docs/design-handoff/` | The design spec ("2b Svep först") the UI follows. |

## The public website

The site is static and hosted on GitHub Pages. The workflow rebuilds it twice a week, so ads that have been removed disappear and new ones appear. Without the AI server the site still works: keyword matching, template letters and template walk-in pitches. With it, Claude ranks jobs, writes applications and personal pitches, and reads imported ads.

### Turn on the AI (your Claude API key)

The key is set as a secret on the server, never in the repository or the page.

```bash
cd server && fly launch --copy-config --no-deploy
```

```bash
fly secrets set ANTHROPIC_API_KEY=your-key-here
```

```bash
fly deploy
```

Then tell the site where the server is and redeploy it:

```bash
gh variable set JOBBSVEP_API --body "https://jobbsvep-api.fly.dev" && gh workflow run update.yml
```

Set `ALLOWED_ORIGINS` in `server/fly.toml` to the site's address so only your site can use the key. The server allows 40 requests per visitor per hour and 3000 per day in total (`PER_IP_HOUR`, `DAILY_CAP`). Also set a monthly spend limit in the Claude Console. Models: `claude-haiku-5-5` for matching and pitches, `claude-sonnet-5-5` for letters (`MODEL_QUICK`, `MODEL_DEFAULT`).

### Use your own domain

Buy the domain at any registrar, then:

```bash
gh variable set SITE_DOMAIN --body "jobbsvep.se" && gh workflow run update.yml
```

At the registrar, point the domain at GitHub Pages: four `A` records for `@` to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`, and a `CNAME` for `www` to `claudeabuser1.github.io`. In the repository's Settings → Pages, enter the domain and tick "Enforce HTTPS" once the certificate is ready.

## How the Claude artifact version works

The same file also runs as a Claude artifact. `web/jobbsvep.html` is a page fragment (no `<html>` or `<head>`) that the artifact host wraps, and it relies on that host for four things:

- **AI** (matching, ranking, drafting letters, reading imported ads, LinkedIn profile text) through `window.claude.use("sample")`.
- **Sending email** through the viewer's Gmail connector, `window.claude.use("mcp")`.
- **Saved state** (profile, applications, shared imported ads) through `window.claude.use("db")` and `use("user")`.
- **Job data** as static files in `web/data/`, published next to the page.

Opened outside that host, the page still loads and you can swipe with keyword matching, but there is no AI, no sending and no account sync.

## Run it locally

```bash
python3 scripts/build_data.py && python3 scripts/build_site.py && python3 -m http.server 8766 --directory site
```

Then open http://localhost:8766/.

## Job data

`build_data.py` uses two free, open APIs from JobTech (Arbetsförmedlingen), no key needed:

- `jobsearch.api.jobtechdev.se` – all Platsbanken ads for Stockholm county, with full text, application email or link, and coordinates.
- `links.api.jobtechdev.se` – ads collected from other Swedish job sites (studentjob.se, ledigajobb.se, thehub.io and others), title and link only.

The data is a snapshot from when the script ran. It is not committed; rebuild it. An earlier snapshot also included a one-off listing from JobTeaser, which is deliberately not in this repository because their site rules do not allow automated collection.

## Chrome extension

Load `extension/` via `chrome://extensions` → Developer mode → Load unpacked. See `extension/README.txt`. It never submits a form, never ticks checkboxes and skips identity-number and password fields.

## Not built yet

- Accounts and a database: everything a visitor enters is kept in their own browser only.
- Sending email from the site: applications open in the visitor's own mail app.
- A privacy policy. CVs and applications are personal data and are sent to Claude when a letter is drafted.

## Status

Tested locally: job loading, keyword matching, swiping, save, ad sheet, distance and map links, text import, the extension's form-filling logic. Not yet exercised end to end: AI ranking and drafting, Gmail sending, account sync, screenshot import, the extension's popup in Chrome.
