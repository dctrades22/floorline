# Preset daily-loss enforcement and boundary sources

Checked 2026-10-24 by fetching each firm's current help or rules page. A preset `daily_loss.enforcement` value is confirmed only when this file quotes that page. A preset `daily_loss.boundary` value is confirmed only when this file quotes an equality sentence on that page. A blank value is unconfirmed. The calculator does not treat unconfirmed enforcement as soft or as hard, and it does not treat an unconfirmed boundary as reach or as exceed.

`hard` means going past the daily limit fails or permanently closes the account. `soft` means hitting the limit stops the session and is not a failed account. Enforcement was not changed on 2026-10-24. No firm flipped from hard to soft, or from soft to hard.

`reach` means the daily limit is inclusive: remaining room exactly 0 is already the firm's trigger. `exceed` means only going through the limit is the trigger: room exactly 0 is not a breach. Boundary is independent of enforcement.

## What the calculator does at exact zero

Both classifications have to be confirmed before exact zero gets a confirmed word.

- Confirmed hard and confirmed reach: `BREACHED`, breached flag TRUE, max contracts 0.
- Confirmed exceed, with hard or with soft: `DAILY LIMIT REACHED`, breached flag FALSE, max contracts 0.
- Confirmed soft and confirmed reach: `DAILY LIMIT REACHED`, breached flag FALSE, max contracts 0. Soft never breaches. Topstep is this pair.
- Enforcement unconfirmed, or boundary unconfirmed, or both: `RULE CONFIRMATION REQUIRED`, breached flag `UNCONFIRMED`, max contracts 0. That is not a safe clearance. A confirmed exceed does not clear an unconfirmed enforcement.

Room below zero ignores boundary and keeps the 2026-10-23 enforcement words: hard `BREACHED`, soft `DAILY LIMIT EXCEEDED`, unconfirmed `RULE CONFIRMATION REQUIRED`. Room above zero sizes normally and still flags whichever classification is blank.

## Topstep — enforcement soft, boundary reach

Presets: P001, P002, P003 (Trading Combine 50k, 100k, 150k). The DLL is optional. Express Funded Account stays `custom_only` with enforcement blank and boundary blank.

DLL page: https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account

Fetched 2026-10-24. The page shows June 30, 2026.

Enforcement:

> The Daily Loss Limit (DLL) is optional in the Trading Combine® and Express Funded Account® (XFA). It’s automatic in the Live Funded Account® (LFA). Triggering it is not a rule violation — it's a forced break for the rest of that session.

> Is hitting the DLL a rule violation? No. It's a temporary break — not a violation. Your account stays eligible for funding.

Boundary (reach). "Hits" includes the example at exactly the limit:

> Net P&L hits or exceeds the DLL during the trading day (5 PM CT – 3:10 PM CT)

> Example: $150K Trading Combine® with a $3,000 DLL. Net P&L hits -$3,000 → auto-liquidated.

Because enforcement is soft, exact zero on these presets is `DAILY LIMIT REACHED`, not `BREACHED`. Soft never breaches.

Maximum loss limit is a different rule (the trailing floor). It is not the DLL classification. Page https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit shows September 18, 2026, and still says hitting that floor liquidates the account. That supports the drawdown preset, not a hard DLL.

A personal daily loss limit can be set to Do Nothing, Liquidate, or Liquidate and Block. The preset classifies the checkout DLL, which the page says is not a rule violation. It does not model the Do Nothing action.

## Vest (Vest Capital) — enforcement hard, boundary exceed

Presets: P031, P032, P033 (Evaluation 5k, 10k, 25k). Instant accounts P027–P030 stay enforcement blank and boundary blank because the page says they never have a DLL. "No Daily Loss Limit" is a purchase option; those rows are the optional DLL, not a claim that every evaluation has one.

Page: https://docs.vestmarkets.com/vest-capital/loss-limits

Fetched 2026-10-24. No page date was visible in the fetch.

Enforcement:

> If your account equity drops through that day's threshold at any point before the next reset, the account closes immediately and permanently.

> Breaching either rule results in immediate, permanent account closure. There is no warning and no grace period. You would need to purchase a new Funded Account to trade again.

Boundary (exceed). The same page says equality is not a breach:

> Equity falling below either applicable loss floor closes the account; equality alone does not breach a limit.

Exact zero on these presets is `DAILY LIMIT REACHED`, not `BREACHED`. One cent through is `BREACHED`.

## Breakout — enforcement hard, boundary reach

Presets: P034–P050 (1-Step Classic, Pro, and Turbo sizes that carry a max daily loss).

Page: https://www.breakoutprop.com/program-rules/

Fetched 2026-10-24. The page says "Updated as of July 29, 2026".

Enforcement, and the equality sentence that sets reach:

> If the account’s equity reaches or exceeds any of the equity limits – this includes both the maximum daily loss equity limit and the maximum drawdown equity limit – the account will be in breach (all positions closed, the account is permanently disabled, and you must purchase another Breakout Evaluation if you wish to restart).

> As a reminder: Maximum daily loss and maximum drawdown are in force at the same time. Reaching or exceeding EITHER of these thresholds will result in a breach.

> If your equity (including any open positions) reaches or exceeds your maximum daily loss equity limit at any point for any amount of time, the account will be breached.

> Reaching or exceeding the maximum daily loss equity limit.

A later sentence says only "Exceeding":

> Exceeding the maximum daily loss equity limit will breach the account.

That sentence does not cancel the repeated "reaches or exceeds" / "Reaching or exceeding" lines, which name the maximum daily loss equity limit and include equality. Boundary is reach.

Exact zero on these presets is `BREACHED`.

## MyFundedPerps — enforcement hard, boundary reach

Presets: P051 Select, P052 Prime, P053 Signature, P054 Elite 3% DLL. P055 Elite No DLL stays enforcement blank and boundary blank. The page says that option has no daily loss limit.

Page: https://docs.myfundedperpetuals.com/guides/challenges-and-rules

Fetched 2026-10-24. No page date was visible in the fetch.

Enforcement:

> A confirmed loss-limit breach changes the account to Failed and stops further trading.

Boundary (reach). The daily-loss floor is called out separately from the post-lock MLL equality exception:

> Before this lock, reaching a loss floor breaches the account. After the lock, equity exactly at the MLL floor is allowed; falling below it breaches. The daily-loss floor remains inclusive.

"The daily-loss floor remains inclusive" is the DLL sentence. The MLL equality allowance after the lock does not apply to the daily floor. Boundary is reach.

Exact zero on P051–P054 is `BREACHED`.

## Left blank on purpose

These presets have no stated daily-loss amount, or the cited page does not state a daily-loss equality rule. Enforcement stays null. Boundary stays null. Nothing in the 2026-10-24 check promoted one of them.

- Apex Trader Funding: daily loss none or unstated.
- Tradeify: daily loss none or unstated.
- MyFundedFutures: daily loss none or unstated.
- Lucid Trading: daily loss unstated.
- Take Profit Trader: daily loss unstated.
- Vest Instant (P027–P030 and P076) and the Vest no-DLL option: the loss-limits page says Instant accounts have no DLL. P076 is the $50,000 Instant row added on 2026-10-25. Its drawdown touch flag is null because the sources below disagree. Enforcement and boundary stay null.
- Topstep Express: `custom_only`, not on the preset tab. Enforcement and boundary blank.
- MyFundedPerps Elite No DLL (P055): the challenges page says there is no daily loss limit.
- Manual and Custom: no preset enforcement and no preset boundary. Those rows are the manual-confirmation path. Accounts columns AS and AV are that confirmation.

Drawdown touch language on those pages was not used as a daily-loss boundary.

## Vest rows added 2026-10-25 — DLL hard and exceed, drawdown touch not preset

Presets: P056–P059 (1-Step Evaluation 5k, 10k, 25k, 50k), P060–P063 (2-Step Phase 1), P064–P067 (2-Step Phase 2), P068–P071 (Funded after 1-Step), P072–P075 (Funded after 2-Step). P076 is Instant 50k and has no DLL, so its enforcement and boundary stay blank. P027–P033 were not edited. The full matrix, the $50,000 finding, and the conflict quotes are in `docs/vest-rules.md`.

Fetched 2026-10-25.

DLL enforcement (hard), from https://docs.vestmarkets.com/vest-capital/loss-limits :

> If your account equity drops through that day's threshold at any point before the next reset, the account closes immediately and permanently.

> Breaching either rule results in immediate, permanent account closure.

DLL boundary (exceed). The same page says equality is not a breach, and the in-app FAQ on next.vestmarkets.com uses "drops through" for the daily floor:

> Equity falling below either applicable loss floor closes the account; equality alone does not breach a limit.

> If your account equity drops through that daily floor at any point during the day, the account closes immediately and permanently.

That pair is why the new rows that have a DLL use `hard` and `exceed`. Exact zero on those rows is `DAILY LIMIT REACHED`. One cent through is `BREACHED`.

Drawdown touch is not given the same value. The loss-limits equality sentence covers both floors, but the in-app FAQ's drawdown answer says the opposite:

> If your total account value, including unrealized PnL, touches or drops below that fixed floor at any point, the account closes immediately and permanently.

> For example, an evaluation-path Platinum $25,000 account always has a Max. Drawdown of $1,500 (6%), closing if total account value ever reaches $23,500 or lower.

`breach_on_touch` on P056–P076 is null. The checkbox is not a confirmed Vest rule. P027–P033 keep the 2026-10-24 value, `false`, from the loss-limits equality sentence alone. This pass did not reopen those rows.
