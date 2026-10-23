# Excel spot check — daily room boundaries

Use the workbook built from this commit. Preset is Manual. The floor is 48,000, so none of the equities below is a floor hit. Day P&L is equity minus the day reference. DLL is 1,000, so daily room is `1000 - max(0, -(equity - 50000))`, floored to the cent.

Type only the white input cells. Leave AS empty for the blank rows. Do not type the word "blank". Do not type C, Q–R through AR, or AU. Those are calculated. Accounts!B13 (As of) can stay empty for these rows.

## Typed cells (same on every row except M and AS)

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

M is Equity now (incl. open P&L). AS is DLL enforcement (`hard`, `soft`, or left empty).

Calculated checks that should match on every row: C = `manual`, Q = `1.25`, R = `static`, S = `50000`, T = `2000`, U = `NONE`, V = `TRUE`, W = `1000`, X = `NONE`, Y = `50`, Z = `50`, AA = `OK`.

MES at 12 ticks is $15 per contract. Risk $200 would be 13 contracts in a large room. These rooms are not large, so a positive room of $0.01 still sizes to the number 0. That 0 is a size, not a status word.

Hidden AP (contracts raw) is 0 on every row below. Hidden AU is blank when the status is OK, and otherwise matches AK.

## Equity 49,000.01 — day P&L −999.99 — daily room 0.01

DD room 1,000.01. Binding room 0.01. Breached flag FALSE. CONTRACTS number 0. Trade status blank.

| AS | Flags (AR) |
|---|---|
| empty | `DLL RULE UNCONFIRMED; MANUAL: all params user-entered` |
| `soft` | `MANUAL: all params user-entered; OVERRIDES PRESET` |
| `hard` | `MANUAL: all params user-entered; OVERRIDES PRESET` |

The three rows size the same. Only the empty AS row is flagged unconfirmed.

## Equity 49,000 — day P&L −1,000 — daily room 0

DD room 1,000. Binding room 0. Breached flag FALSE. CONTRACTS and trade status `DAILY LIMIT REACHED`. Max contracts 0. This word does not depend on hard, soft, or blank.

| AS | Flags (AR) |
|---|---|
| empty | `DLL RULE UNCONFIRMED; MANUAL: all params user-entered` |
| `soft` | `MANUAL: all params user-entered; OVERRIDES PRESET` |
| `hard` | `MANUAL: all params user-entered; OVERRIDES PRESET` |

## Equity 48,950 — day P&L −1,050 — daily room −50

DD room 950. Binding room 0. Max contracts 0. The negative daily room stays visible.

| AS | Breached (AE) | CONTRACTS (AK) and trade status (AU) | Flags (AR) |
|---|---|---|---|
| empty | `UNCONFIRMED` | `RULE CONFIRMATION REQUIRED` | `DLL RULE UNCONFIRMED; MANUAL: all params user-entered` |
| `soft` | `FALSE` | `DAILY LIMIT EXCEEDED` | `MANUAL: all params user-entered; OVERRIDES PRESET` |
| `hard` | `TRUE` | `BREACHED` | `MANUAL: all params user-entered; OVERRIDES PRESET` |

`UNCONFIRMED` is not a safe clearance and it is not the soft exceed. `FALSE` on the soft row means the confirmed rule does not call it a breach. Trading is blocked on all three.

## Precedence these rows sit in

Empty, then INCOMPLETE, then INVALID, then a floor BREACHED, then hard BREACHED, then RULE CONFIRMATION REQUIRED, then DAILY LIMIT EXCEEDED, then DAILY LIMIT REACHED, then a number. Equity 48,000 on this same Manual row is a floor hit, so CONTRACTS is `BREACHED` and AE is TRUE even when AS is empty. The empty-AS floor row still shows `DLL RULE UNCONFIRMED` in Flags.
