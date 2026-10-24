# CME tick check, 2026-10-23

Outright minimum price increment only. Calendar-spread ticks are smaller and are not the tick value used by the calculator or the workbook.

The HTML contract-specs page for ES (`https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html`) was fetched the same day and did not contain the tick table. The numbers below are from the CME Rulebook PDFs.

`curl` to each PDF URL returned **HTTP 403**. The same URLs were then retrieved and the rule text below was read from those PDFs. Chapter `361/361.pdf` returned **404**. Chapter `361.pdf` was the URL that returned the MNQ text.

| Symbol | Tick | Rule | URL |
|---|---|---|---|
| ES | 0.25 index points = $12.50 | Chapter 358, 35801 and 35802.C | https://www.cmegroup.com/rulebook/CME/IV/350/358/358.pdf |
| MES | 0.25 index points = $1.25 | Chapter 353, 35301 and 35302.C | https://www.cmegroup.com/rulebook/CME/IV/350/353/353.pdf |
| NQ | 0.25 index points = $5.00 | Chapter 359, 35901 and 35902.C | https://www.cmegroup.com/rulebook/CME/IV/350/359/359.pdf |
| MNQ | 0.25 index points = $0.50 | Chapter 361, 36101 and 36102.C | https://www.cmegroup.com/rulebook/CME/IV/350/361.pdf |

## ES

Rule 35801: "Each futures contract shall be valued at $50.00 times the Standard and Poor's 500 Stock Price Index."

Rule 35802.C: "The minimum price increment shall be 0.25 Index points, equal to $12.50 per contract, except for intermonth spreads executed pursuant to Rule 542.A., for which the minimum price increment shall be 0.05 Index points, equal to $2.50 per intermonth spread."

$12.50 = 0.25 × $50. `data/contracts.json` status for ES is `verified` (no longer `flagged`).

## MES

Rule 35301: "Each futures contract shall be valued at $5.00 times the Standard and Poor's 500 Stock Price Index."

Rule 35302.C: "The minimum price increment shall be 0.25 Index points, equal to $1.25 per contract, except for intermonth spreads executed pursuant to Rule 542.A., for which the minimum price increment shall be 0.05 Index points, equal to $0.25 per intermonth spread."

$1.25 = 0.25 × $5.

## NQ

Rule 35901: "Each futures contract shall be valued at $20.00 times the Nasdaq-100 Index."

Rule 35902.C: "The minimum price increment shall be 0.25 Index points, equal to $5.00 per contract, except for intermonth spreads executed pursuant to Rule 542.A., for which the minimum price increment shall be 0.05 Index points, equal to $1.00 per intermonth spread."

$5.00 = 0.25 × $20.

## MNQ

Rule 36101: "Each futures contract shall be valued at $2.00 times the Nasdaq-100 Index."

Rule 36102.C: "The minimum price increment shall be 0.25 Index points, equal to $0.50 per contract, except for intermonth spreads executed pursuant to Rule 542.A., for which the minimum price increment shall be 0.05 Index points, equal to $0.10 per intermonth spread."

$0.50 = 0.25 × $2.

GC, MGC, CL, MCL, 6E and M6E were not re-checked. MCL stays `flagged`.
