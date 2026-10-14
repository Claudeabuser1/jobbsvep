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
| Vecka | 19 kr, once, 7 days | 5 kr | 15 letters | 13.11 kr | **+8.11 kr** |
| Månad | 49 kr / month | 12 kr | 40 letters | 36.67 kr | **+24.67 kr** |

How "income after VAT and card fee" is worked out:

- Swedish VAT is 25%, included in the price: 49 kr ÷ 1.25 = 39.20 kr.
- Stripe's fee for normal European cards is about 1.5% of the full price + 1.80 kr: 0.74 + 1.80 = 2.54 kr, so 39.20 − 2.54 = 36.67 kr. Check the current fee at stripe.com/se/pricing.

"Worst case" assumes the user spends the whole AI budget. Most users won't, so the real margin is higher. Fixed costs (Fly server about 30–50 kr/month, domain about 10 kr/month) are covered by a handful of paying users.

## How the guard works (server/server.js)

1. **Reserve.** Before calling Claude, the server works out the most the call could possibly cost: every 3 characters counted as a token, plus the full output limit. If the account's remaining budget is smaller than that, the call is refused with "out of credits", and the site shows the plans.
2. **Charge.** After the call, the real token count from Claude is converted to kronor and charged. The reservation is released.
3. **Free pool.** All free users together may cost at most 10 kr per day (`FREE_DAILY_ORE`). When the pool is empty, free users get template letters until the next day.
4. **Abuse limits.** At most 5 new accounts per IP address per day, 40 AI calls per IP per hour, and only your own website may call the server.
5. **Period.** Free budgets reset every 30 days. A week pass ends after 7 days. A monthly plan renews when Stripe reports the next payment, and drops to free if the subscription is cancelled.

I tested this with a fake AI and a 1.50 kr budget. It allowed 12 calls costing 1.06 kr, then refused the 13th because it could have cost more than the 0.44 kr that was left.

## Changing the numbers

Set these as Fly settings, no code change needed: `FREE_BUDGET_ORE`, `WEEK_BUDGET_ORE`, `MONTH_BUDGET_ORE`, `FREE_DAILY_ORE` (all in öre), `USD_SEK`. If you change a price, change it in three places: the product price in Stripe, `price_ore` in `server/server.js`, and the plan cards in `web/jobbsvep.html`. Keep each budget below a third of the income after VAT and fees, and you stay profitable even if Claude prices rise.

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
