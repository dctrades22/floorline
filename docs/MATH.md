# prop-dd-calc — MATH spec v0.1.0 (QUANT, 2026-10-14)

All arithmetic is defined by `golden/oracle.py` (stdlib, `decimal.Decimal`, prec 50). Golden vectors: `golden/cases.json`,
verify with `python3 golden/oracle.py --check`. Units: account currency (USD) unless noted. Money outputs are rounded
ROUND_HALF_UP to cents **only at output**; intermediate values are unrounded. Contract counts use ROUND_FLOOR.

## 1. Common inputs
| name | unit | constraint |
|---|---|---|
| start_balance `S` | USD | > 0 |
| drawdown_amount `DD` | USD | > 0 |
| lock_offset `X` | USD or null | null = never locks; 0 = lock at start; X = lock at S+X. Require S+X >= S-DD |
| breach_on_touch | bool | default true (equity == floor is a breach). Firms where only "below" breaches (e.g. Vest) set false |
| events | ordered list | `mark{equity}` = intraday equity incl. unrealized P&L; `eod{balance}` = session-close balance |

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
`eod` events: breach check only (no trail beyond what marks already did).
Example (DD-08): S=50,000, DD=2,000, mark 50,750.50 → P=50,750.50, F=48,750.50; mark 49,100 → room 349.50.

## 5. Breach is terminal
Once breached, subsequent events are ignored; `drawdown_room = 0`. (DD-11.)

## 6. Remaining room and binding constraint
- `drawdown_room = max(0, E - F)` (0 when breached).
- `day_loss = max(0, -day_pnl)`; `daily_room = max(0, DLL - day_loss)` when a $ DLL exists, else null.
- `binding_room = min(drawdown_room, daily_room)`; `binding = "daily_loss"` iff `daily_room < drawdown_room`, ties → "drawdown".
- Percentage DLLs (Breakout, Vest, MyFundedPerps) must be converted to $ at the firm's reset instant
  (DLL_$ = rate × reset basis) before calling; reset basis/time is firm-specific (see presets notes).
Examples: RR-12 → 350.00 daily binds; RR-13 → 400.00 drawdown binds.

## 7. Futures sizing
`risk_per_contract = stop_ticks × tick_value`; `contracts = floor(risk / risk_per_contract)`; result < 1 → 0;
`contracts = min(contracts, max_contracts)` if given (`capped=true`). Callers should pass `risk <= binding_room`.
Inputs: risk >= 0, stop_ticks > 0, tick_value > 0 (else `INVALID_INPUT`). Tick values: `data/contracts.json`.
Mini/micro equivalence is per-firm (no generic 10:1 assumed). Examples: FS-14 MES 300/(16×1.25)=15; FS-15 ES → 0; FS-16 MNQ 50→cap 30.

## 8. Crypto perp sizing
`qty = risk / |entry - stop|`; entry == stop → `INVALID_INPUT`; entry, stop > 0. If `step_size` given,
`qty = floor(qty/step) × step` (never round up risk). `actual_risk = qty × |entry-stop|` (cents).
Fees/slippage/leverage/margin not modeled in v0.1. Examples: CS-17 100/650=0.15384…→0.153 (risk 99.45); CS-18 → 1.25.

## 9. Failure conditions
| code | when |
|---|---|
| INVALID_INPUT | non-decimal / non-finite, S<=0, DD<=0, stop_ticks<=0, tick_value<=0, risk<0, entry==stop, unknown event |
| INVALID_RULE_CONFIGURATION | unknown drawdown type, lock on static, lock level below initial floor |
A config error must produce 0 contracts upstream (fail closed).

## 10. Not modeled (flag)
Payout-triggered floor resets (Topstep XFA, Lucid, MFP withdrawal lock), consistency rules, scaling plans,
session/DST boundaries (EOD event timing is the caller's responsibility), commissions.
