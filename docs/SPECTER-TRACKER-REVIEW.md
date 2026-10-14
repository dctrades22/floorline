# SPECTER review: Floorline Tracker @ 0ad7f63 (spec tracker/FORMULAS.md @ dc0127c)

One loop. Probes: /workspace/specter_attacks_propdd/tracker/ (probe.py P1..P20, cmp.py). Recalc engine: LibreOffice headless.

## Verdict: PASS WITH CONDITIONS
Formulas match the spec and the oracle, but two fail-open paths show a normal room and contract count after a logged breach.
Not releasable until H-1 and H-2 are fixed and re-checked (targeted, no new loop).

## What passed
- Committed `tracker/Floorline-Tracker.xlsx` is cell-for-cell identical to a fresh `build_tracker.build()` (0 diffs, all 7 tabs), so the harness tests the real workbook formulas.
- `python3 tracker/test_tracker.py`: 48/48 PASS on rerun (28 golden yes/partial, 20 status scenarios).
- Functions used: AND, COUNTIFS, IF, IFERROR, INDEX, INT, ISNUMBER, MATCH, MAX, MIN, NOT, OR, ROUND, VALUE, `_xlfn.MAXIFS`, `_xlfn.TEXTJOIN`. No LET, LAMBDA, dynamic arrays, INDIRECT, OFFSET, TODAY, NOW, macros or VBA part. `_xlfn` prefixes are the correct xlsx storage form.
- BUILDER's 3 AND() guard changes (W lock-below-floor, W max-contracts, Z Locked) are correct: AND does not short-circuit, so the spec form errors on `NONE`. The rewrite keeps the same truth table. QUANT should adopt them in the spec.
- Text in number cells fails closed: equity "49000" (P4), tick value "1.25" (P10), type "Static " (P14), log date as text (P3), sub-cent log close (P20) give INVALID.
- Breach is terminal and shown as BREACHED, never 0.00, on AB/AC/AD/AE/AF/AG/AM (P5, P15, P16). Exhausted DLL shows 0 room and 0 contracts, not BREACHED (P8), which matches the oracle.
- Intraday close above peak raises the floor (P19, H-1 of v0.1 fixed). Touch FALSE at equality is not a breach (P12).

## FIX list

### HIGH
**H-1 Daily Log INCOMPLETE does not propagate to the account (fail open).** Owner: QUANT (spec 3.1 counts only INVALID) and BUILDER.
Repro P1: Manual static 50,000 / 2,000, equity 49,000; log row with date and intraday low 47,000, EOD balance blank.
Expected: account INCOMPLETE or BREACHED. Actual: log I = INCOMPLETE; account W = OK, AD 1,000, AG 15 contracts.
Fix: W returns INCOMPLETE when `COUNTIFS(log A, A2, log I, "INCOMPLETE") > 0`. Better: also evaluate the low against the floor when C is blank.

**H-2 Orphan log rows are ignored (fail open).** Owner: BUILDER (and a spec line from QUANT).
Repro P2: the log row's account id is a typo ("P2x"), low 47,000 is below the floor. Expected: a visible error. Actual: row INCOMPLETE, F blank, account P2 OK with 15 contracts. The dropdown can be bypassed by pasting.
Fix: if any log row has A filled and F blank, every account shows INCOMPLETE (or there is a global banner), plus a test for it.

### MEDIUM
**M-1 A blank max contracts means no cap.** Owner: QUANT. Repro P9: J blank, risk 100,000, 1 tick at $1 gives AG 1,000 contracts, flagged only as amber text. Presets with a null cap (Lucid) size uncapped by default. Fix: blank V gives INCOMPLETE; only an explicit NONE removes the cap.
**M-2 Google Sheets support and the How-to claims are unverified.** Owner: BUILDER. Only LibreOffice was exercised. "Sheet protection carries over as warnings" and "every formula re-checks its inputs" are not demonstrated, and the second is false per H-1 and H-2. Fix: a recorded Sheets import check (functions, DV, CF, protection) or reword the claims as untested.
**M-3 The harness cannot tell BREACHED from 0.00 and has a ±0.005 tolerance.** Owner: BUILDER. `fmt()` maps numeric 0 to "0.00", so a breached account showing the number 0.00 passes the same as BREACHED. `{:.2f}` hides sub-cent drift. There are no cases for H-1, H-2 or M-1. Fix: when breached, require the literal "BREACHED"; compare exact cents (round(v,2)==v); add P1, P2 and P9 as tests.
**M-4 The stale check is silent.** Owner: BUILDER. It shows only as a CF colour; with B13 blank there is no check and no flag. It relies on `VALUE("2026-10-14")`, which is locale-sensitive in Sheets. If VALUE fails, the CF rule just doesn't fire. Fix: an AN flag "AS-OF DATE MISSING" / "STALE PRESET"; parse the date with DATE(LEFT,MID,RIGHT).

### LOW
- **L-1** Tick value DV requires at most 2 dp, which rejects real ticks such as 15.625 (ZN) and 3.125. Formula AK accepts them, so DV and formula disagree. Owner: QUANT/BUILDER.
- **L-2** No sanity bound on equity (P17: 1e15 gives room 999,999,999,952,000). Optional. Owner: QUANT.
- **L-3** Matching is case-insensitive: "none" counts as NONE (P13) and account id "p16" matches log "P16" (P16). This is the same in Excel and Sheets. Document it. Owner: QUANT.

### INFO
- Sheet protection has no password; it guards against accidents only. Pasting values over the locked calc cells is blocked in Excel and LibreOffice. In Sheets it is not verified (see M-2).
- Intraday "high first" is the conservative assumption and is disclosed on the How-to tab.

## Fix list by owner
- QUANT (spec): H-1 (log INCOMPLETE propagation rule), H-2 (orphan-row rule), M-1 (blank cap = INCOMPLETE), adopt BUILDER's 3 AND guards, L-1, L-2, L-3.
- BUILDER (workbook/harness): H-1, H-2, M-2, M-3, M-4, L-1, plus tests for P1, P2 and P9.
