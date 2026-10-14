# Taking Matchd outside Sweden

## Summary

Most of Matchd already works in any country: swiping, AI letters, walk-in pitches, the credit guard, the app shell. What is Swedish is the **job data**, the **rules for what counts as a youth job**, the **language**, and the **money and law** (kronor, Swedish VAT, Swedish consumer law). The plan is to move each of those into a per-country "market" setting, then add countries one at a time. **Norway first**, because it has a free official job feed and is closest to Sweden.

## 1. What is Sweden-specific today

| Area | Where | What is Swedish |
| --- | --- | --- |
| Job ads | `scripts/build_data.py` | JobTech APIs (Arbetsförmedlingen), region code `01` Stockholm, Swedish occupation fields |
| Youth filter | `scripts/build_data.py` (`YOUTH_OCC`, `BLOCK`, `REQS`, `AGE`, `LICENSE`) | Swedish keywords such as *undersköterska*, *sommarjobb*, *minst 18 år* |
| Places to walk into | `scripts/build_places.py` | Map box around Stockholm county |
| Address lookup | `web/data/places.json` built from Swedish ads, AI fallback says "in Sweden" | Swedish postcodes and street names |
| Language | `web/jobbsvep.html` (Swedish), `web/i18n/en.json` (English) | UI copy, AI instructions about "Swedish ads" |
| Questionnaire facts | `web/jobbsvep.html` (`statYouth`, plan screen) | SCB youth unemployment, IFAU research |
| Money | `server/server.js` `PLANS`, paywall cards | 49 kr / 129 kr / 299 kr, 25% Swedish VAT, `USD_SEK` |
| Law | Help page (privacy policy, terms) | IMY as regulator, Swedish 14-day withdrawal rules, rules for under-18s from Arbetsmiljöverket |
| Chrome extension | `extension/content.js` | Swedish field names (*förnamn*, *postnummer*, *personnummer* skipped) |

## 2. The framework: one "market" setting per country

Add a folder `markets/` with one file per country. Everything that differs lives there:

```json
{
  "code": "no",
  "country": "Norway",
  "languages": ["nb", "en"],
  "region": { "name": "Oslo og Akershus", "bbox": [59.6, 10.3, 60.4, 11.3] },
  "jobs": [{ "adapter": "nav_feed", "token_env": "NAV_FEED_TOKEN" }],
  "youth_rules": "markets/no-youth.json",
  "currency": "NOK",
  "prices": { "week": 2900, "month": 6900 },
  "vat": 0.25,
  "stats": [{ "value": "…", "text": "…", "source": "SSB, …" }],
  "legal": { "regulator": "Datatilsynet", "minors_info": "https://www.arbeidstilsynet.no/" }
}
```

Code changes, in order:

1. **Job adapters.** Split `build_data.py` into a common part (scoring, chunking, writing files) and one small adapter per source that returns ads in the shared format. The JobTech code becomes the `jobtech` adapter. Every adapter must drop expired ads, which some feeds require by contract.
2. **Youth rules as data.** Move the keyword lists into `markets/<code>-youth.json` (job types to include, to block, and phrases for age, licence and experience). Scoring stays shared.
3. **One site per market.** Run `build_site.py --market no` to build that country's site. Either use a folder per country (`/no/`, `/no/en/`) or a separate domain per country (`jobbsvep.no`). The translation tool already handles any language: add `web/i18n/nb.json`.
4. **Money per market.** Give the server one set of `PLANS` per currency, with a Stripe price per plan and market, and keep the same rule: each plan's AI budget stays under a third of its income after VAT and fees. Replace `USD_SEK` with a rate per currency.
5. **Questionnaire facts per market.** Every number on the statistics screens must come from that country's official statistics, with the source shown, like today.
6. **Legal pages per market.** Name the right data protection authority, consumer rules and rules for young workers.
7. **Extension.** Add field names for each new language.

Rough effort: steps 1–3 are about one week of work for the first new market. Each later market is mostly configuration, translation and research.

## 3. Which countries, and where the job data comes from

I checked what public job ad sources exist. **The status column says how sure this is.** Confirm each one with the provider before building.

| Country | Source | Access | Status |
| --- | --- | --- | --- |
| **Norway** | NAV Arbeidsplassen job feed (`pam-stilling-feed`) | Free token requested from NAV; you must accept NAV's API terms and not show expired ads. The older `pam-public-feed` was shut down in 2024. | Described in data.norge.no and third-party tools; read NAV's own docs before building |
| **Finland** | Työmarkkinatori search API (hakurajapinta) | Apply to KEHA-keskus and accept their terms; access is tied to a **Finnish business ID (Y-tunnus)**; test environment first. New interface since April 2026, old one closes May 2027. | Official documentation on tyomarkkinatori.fi |
| **Denmark** | Jobnet (run by STAR) | No documented public API found. Tools use an undocumented search endpoint. STAR has historically shared ads with other job sites for free; ask jobnet@star.dk. | Unconfirmed; needs contact with STAR |
| **Germany** | Bundesagentur für Arbeit, Jobsuche | Publicly reachable endpoint with a fixed client ID, documented by the bundesAPI volunteer project, which says the agency offers **no official API**. Can change without notice. | Works but unofficial; legal and stability risk |
| **United Kingdom** | No government job feed found. Commercial option: Adzuna API (free key at developer.adzuna.com) | Free-tier limits are reported differently by different sources (250 calls a day, or 1,000 a month); production use likely needs a paid feed. | Commercial; check Adzuna's terms |

### Recommended order

1. **Norway.** Free official feed. Norwegian is close to Swedish, so the youth rules are easy to adapt. Strong youth job market in retail and hospitality. Prices in NOK.
2. **Denmark,** once STAR confirms data access. Similar to Norway.
3. **Finland.** Needs a Finnish business ID, so a Finnish company or partner. Wait until you have revenue.
4. **Germany or the UK.** Bigger markets, but no free official feed. Only worth it with funding for a commercial data feed or a partner.

## 4. Checklist for each new country

- [ ] Data access agreement signed, or terms accepted, with the job source
- [ ] Adapter built; expired ads disappear on every refresh
- [ ] Youth rules written and checked against 50 random ads by someone who speaks the language
- [ ] Rules for young workers in that country read (minimum age, hours, night work) and summarised on the help page
- [ ] Places to walk into built for the first city
- [ ] UI translated and the AI prompts adjusted (language of ads, letters and pitches)
- [ ] Statistics for the questionnaire found from official sources, with links
- [ ] Prices set in local currency and checked against the PRICING.md rule
- [ ] VAT: as a Swedish business selling digital services to EU consumers, register for the EU's One Stop Shop (OSS). Norway is outside the EU and has its own simplified scheme for foreign sellers (VOEC). Check with Skatteverket or an accountant.
- [ ] Payment methods people actually use there (for example MobilePay or Vipps); check which ones Stripe supports in that country
- [ ] Privacy policy and terms adapted, with the right regulator named
- [ ] Domain or folder set up, and a local contact address

## Sources

- data.norge.no, NAV job ad API entry: https://data.norge.no/en/datasets/42dc3fe7-46b6-3674-8301-60b6aab84ef5
- Työmarkkinatori, job ad APIs: https://tyomarkkinatori.fi/ohjeet-ja-tuki/yhteistyokumppanit/tyopaikkailmoitusten-rajapinnat
- Työmarkkinatori, search API description: https://tyomarkkinatori.fi/ohjeet-ja-tuki/rajapinnat/tyopaikkailmoitusten-rajapinnat/hakurajapinnan-kuvaus-ja-ohjeistus
- bundesAPI, Jobsuche API documentation: https://github.com/bundesAPI/jobsuche-api
- STAR, rules for job ads on Jobnet (2025): https://star.dk/media/uovn5mx3/2025_04_22_regler-for-kvalitetssikring-af-annoncer-paa-jobnet-og-virksomhedernes-brug-af-cv-banken.pdf
- Adzuna SDK readme (API keys, limits): https://cdn.jsdelivr.net/npm/adzuna-sdk@0.1.2/README.md
