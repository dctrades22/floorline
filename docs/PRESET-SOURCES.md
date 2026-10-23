# Preset daily-loss enforcement sources

Checked 2026-10-23 by fetching each firm's current help or rules page. A preset `daily_loss.enforcement` value is confirmed only when this file quotes that page. A blank value is unconfirmed. The calculator does not treat unconfirmed as soft or as hard.

`hard` means going past the daily limit fails or permanently closes the account. `soft` means hitting the limit stops the session and is not a failed account.

No preset's hard or soft value was removed. The live pages still support the value stored on 2026-10-14. No firm flipped from hard to soft, or from soft to hard, in the text fetched on 2026-10-23. This check compared that text with the notes already in `data/presets.json`. It is not a byte diff against a saved copy of the 2026-10-14 HTML.

## Product rule at exact zero

Daily room exactly 0 is `DAILY LIMIT REACHED`, max contracts 0, and not a breach, for hard, soft, and unconfirmed. That is the product rule.

It matches Vest, which says equality alone does not breach. It does not match Breakout or MyFundedPerps, which say reaching the daily-loss floor breaches. Those presets stay `hard` because going through the limit fails the account. At exact zero the sheet still says `DAILY LIMIT REACHED`, not `BREACHED`. A trader at Breakout or MyFundedPerps has to treat exact zero as the firm's breach even though this calculator does not.

## Topstep — soft — kept

Presets: P001, P002, P003 (Trading Combine 50k, 100k, 150k). The DLL is optional. Express Funded Account stays `custom_only` with enforcement blank.

DLL page: https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account

The page shows June 30, 2026.

> The Daily Loss Limit (DLL) is optional in the Trading Combine® and Express Funded Account® (XFA). It’s automatic in the Live Funded Account® (LFA). Triggering it is not a rule violation — it's a forced break for the rest of that session.

> Is hitting the DLL a rule violation? No. It's a temporary break — not a violation. Your account stays eligible for funding.

Maximum loss limit is a different rule (the trailing floor). It is not the DLL classification. Page https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit shows September 18, 2026, and still says hitting that floor liquidates the account. That supports the drawdown preset, not a hard DLL.

A personal daily loss limit can be set to Do Nothing, Liquidate, or Liquidate and Block. The preset classifies the checkout DLL, which the page says is not a rule violation. It does not model the Do Nothing action.

## Vest (Vest Capital) — hard — kept

Presets: P031, P032, P033 (Evaluation 5k, 10k, 25k). Instant accounts P027–P030 stay enforcement blank because the page says they never have a DLL. "No Daily Loss Limit" is a purchase option; those rows are the optional DLL, not a claim that every evaluation has one.

Page: https://docs.vestmarkets.com/vest-capital/loss-limits

No page date was visible in the fetch.

> If your account equity drops through that day's threshold at any point before the next reset, the account closes immediately and permanently.

> Breaching either rule results in immediate, permanent account closure. There is no warning and no grace period. You would need to purchase a new Funded Account to trade again.

> Equity falling below either applicable loss floor closes the account; equality alone does not breach a limit.

## Breakout — hard — kept

Presets: P034–P050 (1-Step Classic, Pro, and Turbo sizes that carry a max daily loss).

Page: https://www.breakoutprop.com/program-rules/

The page says "Updated as of July 29, 2026".

> If the account’s equity reaches or exceeds any of the equity limits – this includes both the maximum daily loss equity limit and the maximum drawdown equity limit – the account will be in breach (all positions closed, the account is permanently disabled, and you must purchase another Breakout Evaluation if you wish to restart).

> As a reminder: Maximum daily loss and maximum drawdown are in force at the same time. Reaching or exceeding EITHER of these thresholds will result in a breach.

> Exceeding the maximum daily loss equity limit will breach the account.

See the exact-zero note above. The page treats reaching the limit as a breach. This calculator shows `DAILY LIMIT REACHED` at exact zero.

## MyFundedPerps — hard — kept

Presets: P051 Select, P052 Prime, P053 Signature, P054 Elite 3% DLL. P055 Elite No DLL stays enforcement blank. The page says that option has no daily loss limit.

Page: https://docs.myfundedperpetuals.com/guides/challenges-and-rules

No page date was visible in the fetch.

> Before this lock, reaching a loss floor breaches the account. After the lock, equity exactly at the MLL floor is allowed; falling below it breaches. The daily-loss floor remains inclusive.

> A confirmed loss-limit breach changes the account to Failed and stops further trading.

See the exact-zero note above. "The daily-loss floor remains inclusive" means touching it fails the account. This calculator shows `DAILY LIMIT REACHED` at exact zero.

## Left blank on purpose

Every other preset already has `daily_loss.enforcement` null: Apex, Tradeify, MyFundedFutures, Lucid, Take Profit Trader, Vest Instant, MyFundedPerps Elite No DLL, and Topstep Express (`custom_only`, not on the preset tab). Manual and Custom have no preset enforcement. Those rows are the manual-confirmation path. Nothing in this check promoted one of them to hard or soft.
