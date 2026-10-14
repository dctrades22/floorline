# SPECTER review: prop-dd-calc spec v0.1.0 @ cfe8ea6

Scope: docs/MATH.md, golden/oracle.py, golden/cases.json, data/presets.json, data/contracts.json. One loop.
Probes: /workspace/specter_attacks_propdd/ (oracle2.py = independent Fraction-based second oracle; probes.py = P1..P25).

## Verdict: PASS WITH CONDITIONS
Core math is sound and all 20 goldens reproduce independently. Fix H-1..H-3 and M-1..M-4 before BUILDER starts.

## What passed
- `oracle.py --check`: PASS 20 cases. oracle2.py (fractions, no Decimal) reproduces every field of all 20 cases.
- Lock: `c >= L` locks at exactly L (DD-06, DD-10). One cent short (P16: close 52,099.99, X=100) gives floor 50,099.99, unlocked. Correct.
- Strict vs inclusive lock trigger ("exceeds", Lucid/Tradeify wording) is not observable in the floor: at equality c == L either way. INFO, no change needed.
- Peak-before-breach proof in MATH 4 holds (new peak E gives F <= E - DD < E).
- Touch rule: default inclusive (DD-02); `breach_on_touch=false` at equality does not breach, room 0 (P24).
- Futures floor rounding and cap correct (FS-14..16, P22 cap 0). Crypto step floor never rounds risk up (CS-17, P4 gives 0).
- Presets: every numeric value fetched and matched on the cited page on 2026-10-14: Topstep MLL/DLL/max contracts (3 pages), Apex intraday 25/50/100/150K, Tradeify Select 4 sizes, MFF Rapid EOD 50K, Lucid Flex 4 sizes incl. trail/lock balances, TPT 5 sizes, Breakout 17 rows, Vest 7 rows (incl. non-uniform Instant 2%/4%), MFP 5 plans. No guessed number found. custom_only rows carry all-null fields.
- contracts.json: cmegroup.com returns 403 to curl too; values match standard CME specs and are honestly labeled verified_indirect/flagged. INFO.

## FIX list

### HIGH
**H-1 Intraday trailing ignores EOD balance above peak (overstates room).**
Why: an EOD balance is a realized equity level; ignoring it understates the floor. Repro P12: intraday_trailing S=50,000 DD=2,000, events [eod 53,000]. Expected floor >= 51,000, room <= 2,000. Actual floor 48,000, room 5,000. Fix: on eod in intraday mode, treat balance as a peak candidate (update P, trail) before the breach check, or reject eod-only streams.

**H-2 Sizing is not bound to the room it is meant to protect.**
Why: MATH 7 says "callers should pass risk <= binding_room"; nothing enforces it, so a caller bug yields full size. Repro P8: risk 999,999, 1 tick x $1 gives 999,999 contracts, ok=true. Fix: sizing takes binding_room (or the risk_room output) and uses min(risk, binding_room), or errors when risk > binding_room. Fail closed.

**H-3 MFF "Rapid EOD (sim funded)" marked verified but cannot be evaluated and is internally inconsistent.**
Why: account_size 50000 with lock_rule `start_balance: 0, lock_level_absolute: 100`; the oracle requires S > 0 (INVALID_INPUT for 0) and has no `lock_level_absolute` field. Source: initial balance $0, MLL $2,000, locks at $100, breach when balance goes "below $100" (strict). Fix: status custom_only or partial until the model supports start 0 / negative floor, and encode the strict breach.

### MEDIUM
**M-1 Not fail closed on malformed input.** Uncaught exceptions instead of INVALID_INPUT: P10 event without `kind` (KeyError), P17 DLL without `day_pnl` (KeyError), P23 missing `type` (KeyError), P3 crypto risk 1e40 step 1e-20 (decimal.InvalidOperation from quantize). MATH 9 requires codes. Fix: map all to INVALID_INPUT; add goldens.

**M-2 Crypto qty without step_size is unexecutable and badly formatted.** P2: qty `33.333336666667000000033333336666667000000033333337` (50 digits). P1: qty `1E+1` (scientific notation from normalize()). Fix: require step_size (or a documented default precision with ROUND_FLOOR) and plain fixed-point output.

**M-3 Breach touch semantics not machine-readable in presets.** Vest (equality does not breach), MFF sim funded (below $100), MFP (inclusive before lock, strict after lock, DLL always inclusive) are stated only in notes. A consumer gets the default true. Fix: add explicit `breach_on_touch` (and per-phase for MFP) to every preset; null where unstated.

**M-4 Tradeify Select rows are status "verified" while the note flags the eval lock as ambiguous.** Confirmed: the lock sentence sits under funded-stage "Important Considerations". Fix: status partial, or lock_rule null for evaluation.

**M-5 Preset schema is heterogeneous with no schema file.** drawdown_amount is a number or `{pct_of_start}` (MFP); lock_rule has lock_offset, lock_level_absolute, or text only; DLL has `amount`, `pct`, `pct_of_start`, `pct_of_reset_balance` list; max_contracts has minis/micros or contracts/micro_ratio. Fix: a JSON schema plus a rule that any unknown shape yields INVALID_RULE_CONFIGURATION, never a silent default.

**M-6 `day_pnl` basis undefined.** Firms differ: Breakout reset basis excludes open positions at 00:30 UTC, MFP uses start-of-day equity incl. open P&L, Vest adjusts the floor for transfers, Topstep DLL is a soft session stop, not a breach. Fix: define day_pnl (equity incl. unrealized minus firm reset reference) and a per-preset dll_kind (hard/soft).

**M-7 HALF_UP on safety outputs can overstate.** P25: drawdown_room 0.005 prints 0.01. P7: risk 0.996, 1 contract at 0.995 prints actual_risk 1.00 > risk. Fix: round rooms toward zero (ROUND_FLOOR) and never print actual_risk above risk.

### LOW
- **L-1** Fractional max_contracts silently truncated (P5: "2.9" gives 2); fractional stop_ticks accepted (P6: 0.5). Require integers.
- **L-2** `breach_on_touch: "false"` (string) coerces to true (P9). Require a real boolean.
- **L-3** Invalid event after a breach is silently ignored (P11) because the loop breaks first. Validate all events up front.
- **L-4** Within-bar ordering unspecified: input is marks only. Document that callers expanding OHLC must emit the conservative order and that the oracle does not infer it.

### Golden coverage gaps (add)
breach_on_touch=false at and below floor; lock one cent short (P16); negative lock_offset (P14) and lock below floor error (P15); static with lock error; unknown type; intraday eod above peak (H-1); risk_room with no DLL and tie case (P18); crypto no step, sub-step result 0, tiny/huge prices, long vs short; futures max_contracts 0, risk 0; each M-1 malformed input.

## Unsupported claims
- presets status "verified" is defined as "all non-null fields read on the firm's own page"; H-3 and M-4 violate the definition.
- MFF note "Start balance $0 => lock_offset = +100 relative to start" contradicts account_size 50000 in the same row.
No other unsupported claim found in MATH.md.
