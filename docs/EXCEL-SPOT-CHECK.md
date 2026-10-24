# Excel spot check — daily room, enforcement, and boundary

Use the workbook built from this commit. Preset is Manual, so Presets columns Q and R are blank. The floor is 48,000, so none of the equities below is a floor hit. Day P&L is equity minus the day reference. DLL is 1,000, so daily room (AG) is `1000 - max(0, -(equity - 50000))`, floored to the cent.

Type only the white input cells. Leave AS empty to leave enforcement unconfirmed. Leave AV empty to leave boundary unconfirmed. Do not type the word "blank". Do not type C, Q through AR, or AU. Those are calculated. AV is an input. Accounts!B13 (As of) can stay empty for these rows.

## Typed cells (same on every row except M, AS, and AV)

| Cell | Header | Value |
|---|---|---|
| A | Account ID | any unique id, for example `SPOT` |
| B | Preset | `Manual` |
| D | Type override | `static` |
| E | Start override | `50000` |
| F | DD $ override | `2000` |
| G | Lock offset override | `NONE` |
| H | Touch = breach override | `TRUE` |
| I | DLL $ override | `1000` |
| J | Max minis override | `NONE` |
| K | Max micros override | `50` |
| L | Instrument | `MES` |
| N | Day reference balance | `50000` |
| O | Risk $ / trade | `200` |
| P | Stop ticks | `12` |

M is Equity now (incl. open P&L). AS is DLL enforcement (`hard`, `soft`, or left empty). AV is DLL boundary (`reach`, `exceed`, or left empty).

Calculated checks that should match on every row: C = `manual`, Q = `1.25`, R = `static`, S = `50000`, T = `2000`, U = `NONE`, V = `TRUE`, W = `1000`, X = `NONE`, Y = `50`, Z = `50`, AA = `OK`.

MES at 12 ticks is $15 per contract. Risk $200 would be 13 contracts in a large room. These rooms are not large, so a positive room of $0.01 still sizes to the number 0. That 0 is a size, not a status word.

Hidden AP (contracts raw) is 0 on every row below. Hidden AU is blank when the status is OK, and otherwise matches AK.

Flags (AR) depend on AS and AV, not on the equity:

| AS | AV | Flags (AR) |
|---|---|---|
| empty | empty | `DLL RULE UNCONFIRMED; DLL BOUNDARY UNCONFIRMED; MANUAL: all params user-entered` |
| empty | `reach` or `exceed` | `DLL RULE UNCONFIRMED; MANUAL: all params user-entered; OVERRIDES PRESET` |
| `hard` or `soft` | empty | `DLL BOUNDARY UNCONFIRMED; MANUAL: all params user-entered; OVERRIDES PRESET` |
| `hard` or `soft` | `reach` or `exceed` | `MANUAL: all params user-entered; OVERRIDES PRESET` |

A row with either flag is not fully verified. Sizing at room 0.01 does not change because of the flag.

## Equity 49,000.01 — day P&L −999.99 — daily room 0.01

DD room (AF) 1,000.01. Binding room (AH) 0.01. Breached (AE) FALSE on all nine rows. CONTRACTS (AK) number 0. Trade status (AU) blank. The nine rows size the same.

| AS | AV | AE | AG | AK |
|---|---|---|---|---|
| empty | empty | FALSE | 0.01 | 0 |
| empty | `reach` | FALSE | 0.01 | 0 |
| empty | `exceed` | FALSE | 0.01 | 0 |
| `hard` | empty | FALSE | 0.01 | 0 |
| `hard` | `reach` | FALSE | 0.01 | 0 |
| `hard` | `exceed` | FALSE | 0.01 | 0 |
| `soft` | empty | FALSE | 0.01 | 0 |
| `soft` | `reach` | FALSE | 0.01 | 0 |
| `soft` | `exceed` | FALSE | 0.01 | 0 |

## Equity 49,000 — day P&L −1,000 — daily room 0

DD room 1,000. Binding room 0. Max contracts 0. Soft never breaches, so soft + reach is `DAILY LIMIT REACHED` and AE is FALSE. Either classification left empty is `RULE CONFIRMATION REQUIRED` and AE is `UNCONFIRMED`, including empty enforcement with a typed `exceed`.

| AS | AV | AE | AG | AK and AU |
|---|---|---|---|---|
| empty | empty | `UNCONFIRMED` | 0 | `RULE CONFIRMATION REQUIRED` |
| empty | `reach` | `UNCONFIRMED` | 0 | `RULE CONFIRMATION REQUIRED` |
| empty | `exceed` | `UNCONFIRMED` | 0 | `RULE CONFIRMATION REQUIRED` |
| `hard` | empty | `UNCONFIRMED` | 0 | `RULE CONFIRMATION REQUIRED` |
| `hard` | `reach` | TRUE | 0 | `BREACHED` |
| `hard` | `exceed` | FALSE | 0 | `DAILY LIMIT REACHED` |
| `soft` | empty | `UNCONFIRMED` | 0 | `RULE CONFIRMATION REQUIRED` |
| `soft` | `reach` | FALSE | 0 | `DAILY LIMIT REACHED` |
| `soft` | `exceed` | FALSE | 0 | `DAILY LIMIT REACHED` |

`UNCONFIRMED` is not a safe clearance. FALSE on the reached rows means the confirmed pair does not call exact zero a breach. Trading is blocked on every row in this table.

## Equity 48,999.99 — day P&L −1,000.01 — daily room −0.01

DD room 999.99. Binding room 0. Max contracts 0. The negative daily room stays visible. Boundary does not change AE or AK on a negative room. The flag column still follows the table above.

| AS | AV | AE | AG | AK and AU |
|---|---|---|---|---|
| empty | empty, `reach`, or `exceed` | `UNCONFIRMED` | −0.01 | `RULE CONFIRMATION REQUIRED` |
| `soft` | empty, `reach`, or `exceed` | FALSE | −0.01 | `DAILY LIMIT EXCEEDED` |
| `hard` | empty, `reach`, or `exceed` | TRUE | −0.01 | `BREACHED` |

## Precedence these rows sit in

Empty, then INCOMPLETE, then INVALID, then a floor BREACHED, then a confirmed hard daily BREACHED (room below zero, or room exactly 0 with reach), then RULE CONFIRMATION REQUIRED, then DAILY LIMIT EXCEEDED, then DAILY LIMIT REACHED, then a number.

Equity 48,000 on this same Manual row is a floor hit, so CONTRACTS is `BREACHED`, AF and AG say `BREACHED`, and AE is TRUE. That outranks every daily word, including hard + reach and including both classifications blank. The blank floor row still shows `DLL RULE UNCONFIRMED; DLL BOUNDARY UNCONFIRMED; MANUAL: all params user-entered` in Flags.

Preset-driven exact zero, with AS and AV left empty so Presets Q and R supply the pair, and column I set to 1000 with day reference 50000: Topstep Combine 50k (soft + reach) is `DAILY LIMIT REACHED`. Vest Evaluation 5k (hard + exceed) is `DAILY LIMIT REACHED`. Breakout 1-Step Classic 5k (hard + reach) is `BREACHED` with AE TRUE. MyFundedPerps 1-Step Select (hard + reach) is `BREACHED` with AE TRUE. Those four do not show an UNCONFIRMED flag.
