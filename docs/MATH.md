# prop-dd-calc — MATH spec v0.2.0 (fix loop for SPECTER-REVIEW @ 9a0a2de) (QUANT, 2026-10-14)

All arithmetic is defined by `golden/oracle.py` (stdlib, `decimal.Decimal`, prec 50). Golden vectors: `golden/cases.json`,
verify with `python3 golden/oracle.py --check`. Units: account currency (USD) unless noted. Intermediate values are unrounded; rounding happens **only at output**, always in the conservative direction (M-7):
`floor` → ROUND_CEILING to cents; `drawdown_room`, `binding_room`, `effective_risk`, `actual_risk`, `equity` → ROUND_DOWN to cents;
`daily_room` → ROUND_FLOOR to cents (identical to ROUND_DOWN for every value ≥ 0; a negative fraction of a cent stays negative);
`peak` → HALF_UP (informational only). Contract counts and crypto qty use ROUND_FLOOR. Numbers are decimal strings or ints; floats/bools rejected.

## 1. Common inputs
| name | unit | constraint |
|---|---|---|
| start_balance `S` | USD | > 0 |
| drawdown_amount `DD` | USD | > 0 |
| lock_offset `X` | USD or null | null = never locks; 0 = lock at start; X (may be negative) = lock at S+X. Require S+X > S-DD |
| breach_on_touch | JSON boolean (strings rejected, L-2) | default true (equity == floor is a breach). Firms where only "below" breaches (e.g. Vest) set false |
| events | ordered list | `mark{equity}` = intraday equity incl. unrealized P&L; `eod{balance}` = session-close balance |

All events are validated before processing (L-3); a malformed event anywhere fails the whole call.
State: `floor F`, `peak P`, `locked`, `breached`, last `equity E`. Initial: `F = S-DD`, `P = S`, unlocked, not breached.
Lock level `L = S + X`.

Trail step `trail(P)`: if static or locked, no-op. Else `c = P - DD`; if L set and `c >= L` then `c = L`, `locked = true`
(**lock exactly hit**, `c == L`, locks). `F = max(F, c)` (floor never decreases).

## 2. Static
`F = S - DD` forever. Peak irrelevant. Lock not allowed (config error `INVALID_RULE_CONFIGURATION`).
Breach on any `mark`/`eod` with `E <= F` (or `<` if not touch).
Example (DD-01): S=50,000, DD=2,000 → F=48,000; E=49,100 → room 1,100.00.

## 3. EOD trailing
Floor updates only on `eod` events from the highest close; it is **enforced on every mark** (intraday highs ignored for the trail).
On `eod{B}`: first breach check `B vs F`; if not breached and `B > P`: `P = B`, `trail(P)`.
On `mark{E}`: breach check only.
Example (DD-04, Topstep-like lock at start): S=50,000, DD=2,000, X=0; closes 51,000→F 49,000; 52,500→F 50,000 (= L, locked); 54,000→F stays 50,000.
Example (DD-06, lock exactly hit): X=100, close 52,100 → c=50,100 = L → locked; F=50,100.
Example (DD-07): F=49,000 after close 51,000; mark 48,999.99 → breached, later close ignored.

## 4. Intraday trailing (open-equity peak)
On `mark{E}`: **peak update first** — if `E > P`: `P = E`, `trail(P)` — then breach check `E vs F`.
(Ordering is safe: when E sets a new peak, E = P > P-DD >= F, so it can never breach on the same mark.)
`eod{B}` (H-1): B is also a peak candidate — if `B > P`: `P = B`, `trail(P)` — then breach check. (DD-16: eod 53,000 → F 51,000.)
Example (DD-08): S=50,000, DD=2,000, mark 50,750.50 → P=50,750.50, F=48,750.50; mark 49,100 → room 349.50.

## 5. Breach is terminal
Once breached, subsequent events are ignored; `drawdown_room = 0`. (DD-11.)

## 5a. Within-bar ordering (L-4)
The oracle consumes an ordered stream of marks only and never infers intrabar order. A caller expanding OHLC bars must emit the
conservative order: for trailing types, the adverse extreme is evaluated against the floor **before** the favorable extreme
raises the peak (long: O, L, H, C; i.e. assume the low came first). Ambiguity resolution is the caller's job and must be documented.

## 6. Remaining room and binding constraint
- `drawdown_room = max(0, E - F)` (0 when breached). Floor breach is `drawdown().breached`. It is not decided inside `risk_room`.
- `day_pnl` (M-6) = current equity incl. unrealized P&L − the firm's daily reference value at the last reset (preset `daily_loss.basis`/`reset`).
  Transfers/withdrawals that move the reference (Vest) must be folded into the reference by the caller.
- `day_loss = max(0, -day_pnl)`. Signed daily capacity is `DLL - day_loss` when a $ DLL exists, else there is no daily room.
  `daily_room` is that capacity, ROUND_FLOOR to the cent. It is not clamped at zero. A fraction of a cent below zero becomes `-0.01`, not `0.00`.
- `binding_room = min(drawdown_room, max(0, daily_room))`. Sizing never sees a negative room. `binding = "daily_loss"` iff `daily_room < drawdown_room`, ties → "drawdown". `binding` names the tighter room. It is not permission to trade.
- `daily_status` when a DLL exists:
  - capacity > 0 → `OK`. Size normally, subject to risk, the stop, the contract cap, and the drawdown room.
  - capacity = 0 → `DAILY LIMIT REACHED`. Max contracts 0. Not a breach.
  - capacity < 0 and `dll_enforcement` is `hard` → `BREACHED`. The configured rule treats exceeding the daily limit as a failed account.
  - capacity < 0 otherwise (`soft`, or the field omitted) → `DAILY LIMIT EXCEEDED`. Max contracts 0. The breached flag stays false. Unstated enforcement is not treated as hard: the rule does not define a breach, so the calculator must not invent one. Trading is still blocked.
- No status permits trading when daily capacity is ≤ 0. A numeric contract count of 0 with `daily_status = OK` means the stop does not fit in a still-positive room, or the cap is 0. That is not a daily-limit status.
- Percentage DLLs (Breakout, Vest, MyFundedPerps) must be converted to $ at the firm's reset instant
  (DLL_$ = rate × reset basis) before calling; reset basis/time is firm-specific (see presets notes).
- `daily_loss.enforcement` in presets: `hard` = breach/fail; `soft` = forced flat for the session, not a violation (Topstep). The token is case-insensitive. Any other token is `INVALID_INPUT`.
- Missing `day_pnl` when a DLL is given → INVALID_INPUT.
- Precedence, applied by the workbook and the page (the oracle functions stay separate): (1) empty row is blank; (2) `INCOMPLETE` (missing required input, including a blank instrument or cap, a DLL with no day reference, an incomplete log row, or any unknown-account log row); (3) `INVALID` (bad value, bad instrument, bad enforcement token, or an invalid log row); (4) drawdown floor hit → `BREACHED`, max contracts 0, and this outranks every daily status; (5) daily capacity < 0 and enforcement hard → `BREACHED`, max contracts 0; (6) daily capacity < 0 otherwise → `DAILY LIMIT EXCEEDED`, max contracts 0; (7) daily capacity = 0 → `DAILY LIMIT REACHED`, max contracts 0; (8) otherwise a numeric size. `INVALID` and `INCOMPLETE` stay different words. On the sheet, DD room and daily room show the word `BREACHED` only when the floor was hit. A hard daily exceed leaves the negative daily room visible so the two breach causes can be told apart. The breached flag is true for a floor hit and for a hard daily exceed.
Examples: RR-18 daily binds 350.00 and status OK; RR-19 drawdown binds; RR-20 no DLL (`daily_status` null); RR-21 tie → "drawdown". DL-01 is $0.01 left (OK). DL-02 is exactly 0 (`DAILY LIMIT REACHED`). DL-03 is −50 with enforcement unstated (`DAILY LIMIT EXCEEDED`). DL-04 is the same loss with `hard` (`BREACHED`). DL-05 / DL-06 are one cent past the limit. DL-11 floors −0.004 to −0.01.

## 7. Futures sizing
`risk_per_contract = stop_ticks × tick_value`; `contracts = floor(risk / risk_per_contract)`; result < 1 → 0;
then `contracts = min(contracts, active_cap)` when a cap is in force (`capped=true`).
H-2: `binding_room` is a **required** input; `effective_risk = min(risk, binding_room)` is what is sized (`risk_limited_by_room` flags clamping). Fail closed. A contract cap of NONE does not turn this off. Drawdown room and daily-loss room still bind.

**Instrument path** (input contains `instrument`). Tick value is derived, never typed:

| instrument | class | tick value | cap used |
|---|---|---|---|
| ES | mini | 12.50 | `max_minis` |
| NQ | mini | 5.00 | `max_minis` |
| MES | micro | 1.25 | `max_micros` |
| MNQ | micro | 0.50 | `max_micros` |

The free calculator also prices GC/MGC, CL/MCL and 6E/M6E from `data/contracts.json` with the same class rule (symbol starts with M, or is in the micro set → micro cap). The paid workbook dropdown is only ES, MES, NQ, MNQ. A blank instrument or a missing cap for that class is an error (the sheet says INCOMPLETE). An unknown symbol is INVALID. An explicit 0 cap stays 0. `NONE` is the only way to remove the contract cap. If `tick_value` is also supplied it must equal the table or the call is `tick_value mismatch`.

**Legacy single-cap path** (no `instrument` key). The caller supplies `tick_value` and one optional `max_contracts`. FS-22..FS-28 and the old futures invalid cases stay on this path so the floor-division, zero-cap, room-clamp and sub-cent invariants remain tested. They are not the workbook's input shape anymore: the sheet cannot accept an arbitrary tick.

Examples on the new path: IA-01 MES $200 / 12 ticks / 50 micros → 13; IA-02 ES $200 / 12 / 5 minis → 1; IA-03 NQ $200 / 8 / 10 minis → 5; IA-04 MNQ $200 / 8 / 100 micros → 50. Legacy examples still hold: FS-22 15; FS-23 → 0; FS-24 cap 30; FS-25 clamp to room 350; FS-26 max 0; FS-27 risk 0; FS-28 actual_risk 0.99 ≤ 0.996.

## 8. Crypto perp sizing
`qty = effective_risk / |entry - stop|`; entry == stop → `INVALID_INPUT`; entry, stop > 0. `step_size` is **required** (M-2);
`qty = floor(qty/step) × step`, printed fixed-point with the step's decimals (never scientific). Side = long if stop < entry else short.
Results exceeding 50 significant digits → INVALID_INPUT (IV-45). `actual_risk = qty × |entry-stop|` (cents).
Fees/slippage/leverage/margin not modeled in v0.1. Examples: CS-29 0.153 (risk 99.45); CS-30 short 1.25; CS-31 sub-step → 0.000; CS-32/33 tiny/huge prices; CS-34 clamp.

## 9. Failure conditions
| code | when |
|---|---|
| INVALID_INPUT | any missing key or wrong shape (M-1: no exception escapes), non-decimal/non-finite, S<=0, DD<=0, non-integer or <=0 stop_ticks, tick_value<=0, risk<0, missing binding_room/step_size/day_pnl, entry==stop, unknown event, non-boolean breach_on_touch, precision overflow |
| INVALID_RULE_CONFIGURATION | unknown drawdown type, lock on static, lock level <= initial floor; any preset failing `data/presets.schema.json` / `golden/validate_presets.py` (never silently defaulted, M-5) |
A config error must produce 0 contracts upstream (fail closed).

## 10. Not modeled (flag)
Payout-triggered floor resets (Topstep XFA, Lucid, MFP withdrawal lock), consistency rules, scaling plans,
session/DST boundaries (EOD event timing is the caller's responsibility), commissions.

## 11. Presets contract (M-3, M-5)
`data/presets.json` follows `data/presets.schema.json` (no unknown keys; all numbers as decimal strings). Each row carries explicit
`breach_on_touch` (and `breach_on_touch_after_lock` for MFP), `lock.kind` ∈ none|offset|payout_lock_to_start|unstated,
`daily_loss.kind` ∈ none|fixed_usd|pct|pct_of_start|pct_choice|unstated with `enforcement` hard|soft. `custom_only` rows carry no numbers.
`verified` rows may not have any `unstated` kind or null `breach_on_touch`. `python3 golden/oracle.py --check` validates presets too.
