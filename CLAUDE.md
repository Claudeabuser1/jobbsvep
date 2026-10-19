# Matchd: guide for Claude

Matchd (formerly Jobbsvep) is a swipe-to-apply job app for 16–21 year olds in Stockholm. The owner is not a developer; explain things simply, do one task at a time, and review your own work before moving on.

## Where things are

| What | Where |
| --- | --- |
| Live site (GitHub Pages) | https://claudeabuser1.github.io/jobbsvep/ (English at `/en/`) |
| AI, credits and payments server | Fly app `jobbsvep-api`, https://jobbsvep-api.fly.dev, region arn, volume `jobbsvep_data` |
| Launch checklist (owner's to-do list) | https://claude.ai/artifact/LGFh9d5PboYsvQcE473GZs, source copy in `docs/launch-checklist.html` |
| Claude-artifact version of the app | https://claude.ai/artifact/T8MKvZncutCWRi9EU2ScDn |

The whole app is one file, `web/jobbsvep.html` (markup, CSS, JS). The same file is published as the Claude artifact, where it uses `window.claude` capabilities, and as the public site, where `scripts/build_site.py` wraps it and it talks to the Fly server. `STANDALONE` in the script tells the two apart.

## Rules that are easy to break

- **Internal names stay "jobbsvep".** Only visible text says Matchd. Never rename `localStorage` keys (`jobbsvep:v1`, `jobbsvep:acct`), the IndexedDB name, `meta name="jobbsvep-*"` or `jobbsvep-bridge`: users would lose their saved data, and the Chrome extension would lose its connection.
- **English is generated.** `scripts/i18n.py` translates whole Swedish strings using `web/i18n/en.json`. Any new or changed Swedish UI text needs an entry there. Run `python3 scripts/i18n.py en`: it lists strings it couldn't find and Swedish left behind. The only expected leftovers are 9 intentional ones (place names, the IFAU report title, the stop-word list).
- **Prices must be safe.** Plans are Vecka 49 kr, Månad 129 kr/month and 3 månader 299 kr. Each plan's AI budget (`server/server.js` `PLANS`) must stay under a third of its income after VAT and Stripe fees, and the server reserves the worst-case cost before every Claude call. See `docs/PRICING.md`. If you change a price, change it in Stripe, `PLANS`, the paywall cards and the help and terms texts, plus their English entries.
- **Honest marketing.** No fake crossed-out prices, no invented statistics. The questionnaire's numbers are live job counts, SCB AKU August 2026 (23.8%) and IFAU 2013:20.
- **Secrets are the owner's.** Never ask for or handle the Anthropic API key or Stripe keys. The owner runs `fly secrets set …` themselves.
- **Things that cost money or publish need the owner's yes:** domain purchase, store accounts, new Fly resources.

## Build and deploy

```bash
python3 scripts/build_data.py && python3 scripts/build_site.py && python3 -m http.server 8766 --directory site
```

- **Website:** pushing to `main` deploys it. The workflow also rebuilds job data Mondays and Thursdays. If a deploy hangs, check for a stuck Pages deployment and cancel it with `gh api -X POST repos/Claudeabuser1/jobbsvep/pages/deployments/<id>/cancel`.
- **Server:** `cd server && fly deploy --remote-only --ha=false`.
- **Places:** `scripts/build_places.py` (OpenStreetMap; slow, run rarely, commits `web/pois.json`).
- **Repository variables:** `JOBBSVEP_API` and `CONTACT_EMAIL` (matchd.info@gmail.com) are set. `OWNER_NAME` and `SITE_DOMAIN` are not set yet.
- **Not in the repo on purpose:** the one-off JobTeaser listing (`jobteaser.json`). Their site rules don't allow automated collection.

## Status (15 October 2026)

Done and tested:
- Swiping and the youth filter.
- Distance from home and map links.
- "Gå dit" walk-in pitches.
- Importing ads and drafting letters.
- LinkedIn profile help.
- First-run questionnaire, guided tour, help page with privacy policy and terms.
- English version.
- Installable offline web app.
- Credit guard on the server.
- Chrome extension (`extension/`).
- Capacitor setup for the store apps (`app/`, app ID `se.matchd.app`).
- Docs: `docs/PRICING.md`, `docs/APP.md`, `docs/INTERNATIONAL.md`, `docs/MARKETING-VIDEOS.md`.

Waiting on the owner (all in the checklist):

- Anthropic API key on Fly.
- Buy matchd.se. Then set `SITE_DOMAIN`, add the domain to `ALLOWED_ORIGINS` and `SITE_URL` in `server/fly.toml`, and redeploy.
- Register an enskild firma.
- Stripe: three prices and the webhook, set as Fly secrets.
- `OWNER_NAME`.

Not verified end to end:
- Stripe checkout.
- AI on the public site (no key yet).
- The extension's automatic pick-up of profile and letters from the page.

Name risk: matchd.com belongs to an Australian recruiting-assessment company, and a Dutch staffing firm also uses "Matchd".
