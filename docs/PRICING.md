# Pricing: how Jobbsvep can never cost more than it earns

## The short version

Every visitor gets an account automatically (no sign-up). Each account has an **AI budget in kronor of real Claude cost** for its period. The server checks the budget **before** every AI call and charges the **actual** cost after it. A paid plan's budget is set far below its price, so even a user who uses every last öre leaves you with a profit. Free users are capped both per person and all together per day.

Everything that does not use AI (swiping, keyword matching, template letters, Gå dit, the job list) is free and costs you nothing extra.

## What things cost you

Claude prices (per million tokens, from Anthropic's price list, October 2026):

| Model | Used for | Input | Output |
| --- | --- | --- | --- |
| Claude Haiku 5.5 | Ranking jobs, walk-in pitches, finding places | $0.10 | $0.50 |
| Claude Sonnet 5.5 | Application letters, LinkedIn profile, reading imported ads | $2.00 | $10.00 |

The server converts with 11 kr per dollar, a little above the real rate, so costs are slightly overestimated rather than underestimated.

Estimated cost per action (actual cost is measured on every call):

| Action | Model | Roughly | Cost |
| --- | --- | --- | --- |
| One application letter | Sonnet | 7,000 tokens in, 1,500 out | about 0.30 kr |
| Ranking 40 jobs | Haiku | 7,000 in, 2,000 out | about 0.02 kr |
| One walk-in pitch | Haiku | 2,500 in, 600 out | under 0.01 kr |
| LinkedIn profile rewrite | Sonnet | 10,000 in, 3,000 out | about 0.55 kr |
| Reading an imported ad with a screenshot | Sonnet | 3,000 in, 1,000 out | about 0.18 kr |

## The plans

| Plan | Price | AI budget | About | Your income after VAT and card fee | Your worst case |
| --- | --- | --- | --- | --- | --- |
| Gratis | 0 kr | 1.50 kr / 30 days | 5 letters | 0 kr | −1.50 kr per active free user, capped by the daily pool |
| Vecka | 49 kr, once, 7 days | 6 kr | 20 letters | 36.67 kr | **+30.67 kr** |
| Månad | 129 kr / month | 18 kr | 60 letters | 99.47 kr | **+81.47 kr** |
| 3 månader | 299 kr, once, 90 days | 54 kr | 180 letters | 232.91 kr | **+178.91 kr** |

How "income after VAT and card fee" is worked out, using Månad:

- Swedish VAT is 25%, included in the price: 129 kr ÷ 1.25 = 103.20 kr.
- Stripe's fee for normal European cards is about 1.5% of the full price + 1.80 kr: 1.94 + 1.80 = 3.74 kr, so 103.20 − 3.74 = 99.47 kr. Check the current fee at stripe.com/se/pricing.

Each AI budget is 16–23% of the plan's income, well under the one-third rule below. "Worst case" assumes the user spends the whole budget; most won't. Fixed costs (Fly server about 30–50 kr a month, domain about 10 kr a month) are covered by a single paying user.

### How the prices are presented (anchoring)

Every comparison uses real prices only:

- **3 månader is shown first.** The biggest number sets the reference point, so 129 kr feels moderate.
- **Månad is highlighted as "Populärast".** It's in the middle, with a per-week price ("Bara 30 kr i veckan").
- **Vecka shows 49 kr i veckan.** Next to Månad's 30 kr a week, that makes the month look like the obvious deal. Buying four weeks would cost 196 kr.
- **3 månader shows "spara 88 kr".** This is true: 3 × 129 kr = 387 kr, against 299 kr.
- **The value anchor:** "Ett enda arbetspass på ditt nya jobb betalar en hel månad."

Never show a crossed-out "ordinary price" that was never actually charged. Under Swedish price-marking rules, a price reduction must be measured against the lowest price of the previous 30 days, and Konsumentverket acts against fake discounts. If you run a real campaign later, for example Månad at 99 kr for two weeks, you may show "129 kr" crossed out because that was the real price before.

## How the guard works (server/server.js)

1. **Reserve.** Before calling Claude, the server works out the most the call could possibly cost: every 3 characters counted as a token, plus the full output limit. If the account's remaining budget is smaller than that, the call is refused with "out of credits", and the site shows the plans.
2. **Charge.** After the call, the real token count from Claude is converted to kronor and charged. The reservation is released.
3. **Free pool.** All free users together may cost at most 10 kr per day (`FREE_DAILY_ORE`). When the pool is empty, free users get template letters until the next day.
4. **Abuse limits.** At most 5 new accounts per IP address per day, 40 AI calls per IP per hour, and only your own website may call the server.
5. **Period.** Free budgets reset every 30 days. A week pass ends after 7 days. A monthly plan renews when Stripe reports the next payment, and drops to free if the subscription is cancelled.

I tested this with a fake AI and a 1.50 kr budget. It allowed 12 calls costing 1.06 kr, then refused the 13th because it could have cost more than the 0.44 kr that was left.

## Changing the numbers

Set these as Fly settings, no code change needed: `FREE_BUDGET_ORE`, `WEEK_BUDGET_ORE`, `MONTH_BUDGET_ORE`, `QUARTER_BUDGET_ORE`, `FREE_DAILY_ORE` (all in öre), `USD_SEK`. If you change a price, change it in three places: the product price in Stripe, `price_ore` in `server/server.js`, and the plan cards in `web/jobbsvep.html`. Keep each budget below a third of the income after VAT and fees, and you stay profitable even if Claude prices rise.

Example:

```bash
fly secrets set FREE_DAILY_ORE=500 -a jobbsvep-api
```

## Before you take real money

- **Company:** you need a business to sell in Sweden. An enskild firma is registered free at verksamt.se. Under 18, a guardian must agree and the överförmyndare must approve.
- **Stripe:** create the account, the two products, and the webhook. Exact clicks are in the setup checklist.
- **Consumer law:** digital services have a 14-day right of withdrawal unless the buyer agrees that delivery starts immediately and that they lose that right. Stripe Checkout can show that consent text. The terms page should say it.
- **Young users:** many users will be 16–17. Card payments need a card in their name or a parent's. Keep the free tier genuinely useful, and never pressure anyone into paying.
- **Spend limit:** set a monthly spend limit on your Claude API key in the Claude Console as a last safety net.
