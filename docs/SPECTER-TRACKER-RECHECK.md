# SPECTER targeted re-check: Floorline Tracker @ ed58371 (spec 8f4ff01)

Not a new loop. LibreOffice headless. Probes: /workspace/specter_attacks_propdd/tracker/probe.py, recheck.py.

## Verdict: PASS

| item | repro | before (0ad7f63) | now (ed58371) |
|---|---|---|---|
| H-1 | P1: log low 47,000 below floor 48,000, EOD blank | account OK, AD 1,000, AG 15 | log I INCOMPLETE; account W..AM all INCOMPLETE, no room or contracts |
| H-2 | P2: log account id typo "P2x", low 47,000 | row ignored, account OK, AG 15 | log I = UNKNOWN_ACCOUNT; real account W..AM all INCOMPLETE |
| M-1 | P9: effective cap blank | AG 1,000 contracts, amber text only | all INCOMPLETE, flag "MAX CONTRACTS MISSING"; explicit NONE gives 15 (uncapped); a preset cap of 5 still applies with J blank |
| M-4 | Topstep P001, B13 blank / 2026-10-20 / 2026-11-20 | CF colour only, VALUE(date text) | text flags "AS-OF DATE MISSING" / none / "STALE PRESET: checked 2026-10-14..."; date parsed with DATE(LEFT,MID,MID), no VALUE(date text) |

Harness rerun: `python3 tracker/test_tracker.py` TOTAL PASS 64/64 (repro group 4/4, fix group 12/12). Breached cases now require the literal "BREACHED".

Residual (INFO, no action needed for this gate): STALE PRESET and AS-OF DATE MISSING are advisory flags; they do not block the numbers. The workbook is still verified in LibreOffice only, and the Sheets wording (M-2) was not re-checked here.
