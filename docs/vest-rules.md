# Vest Capital rules checked 2026-10-25

Proposal notes for Floorline. Nothing here is a promise that a rule stays in force. Confirm the account in the Vest dashboard before trading.

## Which firm this is

Floorline's existing Vest rows already cite Vest Capital on Vest Markets. This pass used the same firm.

Official pages that loaded:

- https://docs.vestmarkets.com/vest-capital/overview
- https://docs.vestmarkets.com/vest-capital/account-tiers
- https://docs.vestmarkets.com/vest-capital/loss-limits
- https://docs.vestmarkets.com/vest-capital/claiming-profit
- https://docs.vestmarkets.com/llms.txt and https://docs.vestmarkets.com/sitemap.md
- https://next.vestmarkets.com/vest-capital/evaluation (the purchase app shell; the rules text is not in the first HTML response)
- https://api-gateway.hz.vestmarkets.com/v3/payments/catalog (the catalog that purchase app requests from `/v3/payments/catalog`)

The in-app FAQ quoted below is the English FAQ object shipped in `https://next.vestmarkets.com/assets/index-DE3UiZ01.js`, read 2026-10-25. That bundle is the purchase site's own copy, not a third-party review.

Vest Capital is the funded program on Vest Markets, a perpetual-futures exchange (equities, indices, commodities, FX, and crypto). It is not a CME mini/micro prop firm with a published contract ladder. A search the same day did not turn up a second prop program named Vest with its own rules site. If "Vest" was meant to be a different firm, these rows should not be used.

https://docs.vestmarkets.com/vest-capital/faq-and-refunds returned 404 on 2026-10-25. A web-search snippet still described an older daily-loss formula (4% plus half of unrealized profit, reset 8:00 PM EST). That page was not retrieved, and that formula is not used below.

Secondary write-ups were not used for any number.

## $50,000

The written docs do not list a $50,000 account.

Account Tiers, Overview, and Loss Limits, all fetched 2026-10-25, stop at Platinum $25,000 for evaluations and at $25,000 for Instant. Account Tiers says the live pricing pages are the source of record and that pricing may change.

The purchase catalog fetched the same day does list $50,000, under the tier name Emerald:

- 1-Step evaluation: 12 option combinations (10% or 20% profit target, 3%, 4%, or no daily loss limit, 80/20 or 90/10).
- 2-Step evaluation: one fixed plan.
- Instant: one plan, price $2,000, max drawdown 4%, no daily loss limit.

The purchase-app code builds the size list from that catalog and does not filter out 50000. This pass did not complete a logged-in purchase, and the marketing HTML served without JavaScript does not print the Emerald row.

## Full matrix

Access date for every cell is 2026-10-25.

Dollar drawdown for $5,000, $10,000, and $25,000 evaluations is printed on the docs floor table. The $50,000 evaluation dollar is 6% of the catalog starting capital (`maxDrawdownPct` `0.060000`). The docs table does not print that row. Instant $50,000 drawdown is the catalog price $2,000 and `maxDrawdownPct` `0.040000`. Docs say an Instant payment equals max drawdown.

Profit-target dollars for 2-Step stages are the catalog `profit_target` on that stage. They match "10% of capital, then a further 5%" on Account Tiers. Phase 2 `initial_capital` in the catalog is the original size, not the Phase 1 ending balance. No docs sentence was found that says the balance is reset in prose; the catalog field is the source for that figure.

| Type | Phase | Size | Profit target | Max drawdown | Method | Daily loss limit |
| --- | --- | --- | --- | --- | --- | --- |
| 1-Step | Evaluation | $5,000 Silver | 10% or 20%, chosen at purchase | $300 | static 6%, no trail, no lock | 3%, 4%, or none, chosen at purchase |
| 1-Step | Evaluation | $10,000 Gold | 10% or 20%, chosen at purchase | $600 | static 6%, no trail, no lock | 3%, 4%, or none, chosen at purchase |
| 1-Step | Evaluation | $25,000 Platinum | 10% or 20%, chosen at purchase | $1,500 | static 6%, no trail, no lock | 3%, 4%, or none, chosen at purchase |
| 1-Step | Evaluation | $50,000 Emerald | 10% ($5,000) or 20% ($10,000), chosen at purchase | $3,000 (6% of $50,000; not in the docs table) | static 6%, no trail, no lock | 3%, 4%, or none, chosen at purchase |
| 1-Step | Funded | $5,000 Silver | none (catalog funded stage target empty) | $300 | same static 6% | same option bought with the evaluation |
| 1-Step | Funded | $10,000 Gold | none | $600 | same static 6% | same option bought with the evaluation |
| 1-Step | Funded | $25,000 Platinum | none | $1,500 | same static 6% | same option bought with the evaluation |
| 1-Step | Funded | $50,000 Emerald | none | $3,000 | same static 6% | same option bought with the evaluation |
| 2-Step | Phase 1 | $5,000 Silver | $500 (10%) | $300 | static 6% on that stage | 3% fixed |
| 2-Step | Phase 1 | $10,000 Gold | $1,000 (10%) | $600 | static 6% on that stage | 3% fixed |
| 2-Step | Phase 1 | $25,000 Platinum | $2,500 (10%) | $1,500 | static 6% on that stage | 3% fixed |
| 2-Step | Phase 1 | $50,000 Emerald | $5,000 (10%) | $3,000 | static 6% on that stage | 3% fixed |
| 2-Step | Phase 2 | $5,000 Silver | $250 (5%) | $300 | static 6%; stage initial capital is $5,000 | 3% fixed on that stage |
| 2-Step | Phase 2 | $10,000 Gold | $500 (5%) | $600 | static 6%; stage initial capital is $10,000 | 3% fixed on that stage |
| 2-Step | Phase 2 | $25,000 Platinum | $1,250 (5%) | $1,500 | static 6%; stage initial capital is $25,000 | 3% fixed on that stage |
| 2-Step | Phase 2 | $50,000 Emerald | $2,500 (5%) | $3,000 | static 6%; stage initial capital is $50,000 | 3% fixed on that stage |
| 2-Step | Funded | $5,000 Silver | none | $300 | static 6% | 3% fixed |
| 2-Step | Funded | $10,000 Gold | none | $600 | static 6% | 3% fixed |
| 2-Step | Funded | $25,000 Platinum | none | $1,500 | static 6% | 3% fixed |
| 2-Step | Funded | $50,000 Emerald | none | $3,000 | static 6% | 3% fixed |
| Instant | Funded | $500 | none | $10 (2%) | static, equals the $10 price | none |
| Instant | Funded | $5,000 | none | $200 (4%) | static, equals the $200 price | none |
| Instant | Funded | $10,000 | none | $400 (4%) | static, equals the $400 price | none |
| Instant | Funded | $25,000 | none | $1,000 (4%) | static, equals the $1,000 price | none |
| Instant | Funded | $50,000 | none | $2,000 (4%) | static, equals the $2,000 catalog price | none |

1-Step has one evaluation stage in the catalog, then a funded stage. It does not have a Phase 2. Profit split (80/20 or 90/10 on 1-Step, 80/20 on 2-Step, 95% on Instant) does not change the loss numbers. The catalog repeats the same drawdown and daily-loss percentages on every 1-Step option for a given size.

## Rules that apply across the matrix

Loss Limits, fetched 2026-10-25:

> Vest Capital's loss limits follow your account type, not its phase. Whatever applies during the Evaluation Phase carries through unchanged once you're Live.

> A fixed floor, set once when your account is created. It never moves.

> Profits don't raise it. Losses don't lower it further. Calculated as a percentage of your starting capital, not your current balance.

The in-app FAQ drawdown answer:

> Static. It is set when the account is created and never moves. It does not trail your profits and it is not recalculated at the end of the day.

> The rate is 6% of starting capital on every evaluation-path account. On Instant Accounts it varies by size.

So Phase 1, Phase 2, and the funded stage are not assumed to share a floor. The loss-limits page says the limits follow the account type rather than the phase, and the catalog prints `max_drawdown_pct` and `max_daily_loss_pct` on each stage. For every 2-Step product those stage percentages match (0.060000 and 0.030000). The profit targets do not match.

Daily loss limit, Loss Limits page:

> The daily loss allowance is 3% or 4% of your reset balance: account balance plus reserved collateral, excluding unrealized PnL.

> The daily reset boundary is 20:00 ET (America/New_York).

> Daily floor = reset balance × (1 − rate) + net non-trading transfers since reset.

> Current equity includes unrealized PnL and is checked against the adjusted floor.

> If your account equity drops through that day's threshold at any point before the next reset, the account closes immediately and permanently.

> Equity falling below either applicable loss floor closes the account; equality alone does not breach a limit.

In-app FAQ, daily loss:

> When present, it applies in both the Evaluation Phase and once Live, and is checked against your account equity at 20:00 ET each day, holding until the next 20:00 ET reset. Equity is your current account value, including unrealized PnL.

> If your account equity drops through that daily floor at any point during the day, the account closes immediately and permanently.

> For example, at the 3% rate, if your account equity is $10,000 at 20:00 ET, the day's floor is $9,700. At the 4% rate, the floor would be $9,600.

The FAQ example treats 20:00 ET equity, including unrealized PnL, as the reset input. The Loss Limits page excludes unrealized PnL and includes reserved collateral, then moves the floor for non-trading transfers. Both are official. Floorline's new rows keep the Loss Limits basis text and tell the user to type the dashboard reset balance. They do not pick the FAQ example silently. See "Unverified" below.

2-Step is not the 3% / 4% / none menu. Account Tiers says every 2-Step account has a 3% daily loss limit. The catalog has one 2-Step product per size, `maxDailyLossPct` 0.030000 on Phase 1, Phase 2, and funded.

Going live, in-app FAQ:

> Your Evaluation Phase closes and a Live Funded Account of the same size is created instantly.

> There is no profit goal and no time limit, and you can claim profit at any time.

> The risk rules carry across unchanged: Max. Drawdown continues to apply at the same fixed floor, and the Daily Loss Limit continues to reset each day at 20:00 ET if your account type includes one.

Other published points, same date:

- No minimum trading days and no time limit, in the Evaluation Phase or on a live funded account (in-app FAQ). Overview also says no time limits.
- No consistency rule: no cap on one day's share of profit (in-app FAQ). The evaluation marketing page also says "No consistency rule."
- No news restriction: positions may be opened and held before, during, and after a release (in-app FAQ).
- No per-trade position-size limit beyond the loss rules (in-app FAQ). That is not a mini/micro contract count.
- Breach of either loss rule closes the account immediately and permanently, evaluation or funded (Loss Limits, and the in-app FAQ).
- Evaluation profits are not a payout. Claiming Profit is the live-account flow (Claiming Profit page). The old FAQ URL that used to say evaluation profits are not kept returned 404; the in-app FAQ says the evaluation closes and a new live account is created, with no profit goal.
- API trading is not available on evaluation or live funded accounts, including Instant (Overview and in-app FAQ).
- XRP and HYPE are unavailable on funded accounts (Overview and in-app FAQ).
- Non-crypto markets follow the weekend schedule. The in-app FAQ says ES, NQ, and commodities close Friday 5:00 PM ET and resume Sunday 6:00 PM ET, and single equities close Friday 8:00 PM ET and resume Sunday 8:00 PM ET. Crypto trades through the weekend. No separate prop ban on overnight holds was found.
- Refund within 3 days if no trade has been placed (Overview). Failing the evaluation is not a refund (in-app FAQ).
- Maximum 10 live funded accounts and 100 evaluation accounts (Overview). `GET /v3/capital/limits` the same day returned `max_funded` 10, `max_eval` 100, `max_per_purchase` 20.

## Drawdown touch conflict

Loss Limits says falling below a floor closes the account and equality alone does not breach either floor.

The in-app FAQ drawdown answer says touching the floor closes it, and that a $25,000 evaluation closes if account value reaches $23,500 or lower.

Floorline's new Vest rows leave `breach_on_touch` null. The existing Instant and Evaluation rows (P027–P033) were not changed. They still follow the 2026-10-24 reading of the Loss Limits equality sentence (`false`). `docs/PRESET-SOURCES.md` records both.

On the calculator, a null touch flag uses the existing "not stated by firm" control. The page's existing default checks that box until the user confirms it. That default is not a Vest rule.

## What was not published, or not used

- A single drawdown-touch rule. The two official texts disagree. Not filled on P056–P076.
- Which daily-loss reset basis wins. Loss Limits excludes unrealized PnL. The in-app FAQ example uses equity, including unrealized PnL. The user has to enter the reset balance.
- The $50,000 evaluation floor as a printed docs-table cell. $3,000 is 6% of the catalog capital. The $50,000 Instant $2,000 allowance is the catalog price and the 4% field, not a docs-table cell.
- A prose statement that Phase 2 wipes the Phase 1 balance. The catalog stage's `initial_capital` is the original size. What the dashboard shows at the moment Phase 2 opens was not described in prose.
- Whether changing phase forces a daily-loss reset outside 20:00 ET. Not stated.
- The funded account's opening equity, as distinct from its size. The FAQ says a live account of the same size is created and the floor carries across. It does not say whether evaluation profit is inside that new balance.
- Leverage. Overview says up to 75x, market-dependent. The in-app FAQ says up to 50x on a funded account and up to 100x on a primary account. Every catalog plan, including funded and Instant stages, has `maxLeverage` `5.0000`. Those were not converted into a contract cap, and 5.0000 was not assumed to mean 5x or 50x.
- Mini, micro, or generic contract caps. Not published. The FAQ's "no per-trade position-size limit" is not a Floorline contract count. The new rows leave the cap blank. Type NONE or a number from the dashboard.
- A scaling plan. Not published.
- A prop-account overnight ban, apart from the market hours above. Not published.
- The retracted FAQ page's 4%-plus-half-unrealized formula. The page 404'd. Not used.
- Any number from a review site.
