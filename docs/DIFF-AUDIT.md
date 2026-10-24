# Diff audit of 06e13720101882970ec2bb7f7e91276ac8d40324

Compared with `main` at `ca303e9bf9a5d3576a2020e1e6a8d6f56156c846`. Nineteen files, +1332 / −314. No file in that commit is an unrelated change. Nothing was reverted.

| File | Why it is in the commit |
|---|---|
| `.gitignore` | Stops tracking the paid xlsx, `tracker/dist/`, and Python bytecode. |
| `README.md` | Describes derived ticks, class caps, blank / 0 / NONE, and the workbook's four-symbol menu. |
| `docs/DEPLOY-CHECKLIST.md` | Owner checklist requested with the instrument-cap work. Later commits refresh the Gumroad quotes and the build command. |
| `docs/MATH.md` | Instrument path, legacy single-cap note, and the four required examples. |
| `golden/oracle.py` | Instrument dispatch, tick table, cap class, and the IA cases. |
| `golden/cases.json` | Regenerated. Old case inputs and expected values are unchanged. Fourteen IA cases were added. Descriptions only changed on FS-22..FS-28 and IV-36, IV-38, IV-46, IV-47. |
| `index.html` | Cap field label: required, 0, NONE. Input accepts `NONE`. |
| `js/oracle.js` | Same dispatch and table as the Python oracle. |
| `js/app.js` | Class cap, blank is incomplete, instrument passed instead of a typed tick. |
| `test/run.js` | Expects 63 cases and asserts IA-01..IA-04. |
| `tracker/FORMULAS.md` | Column letters and cap rules for v0.2.0. |
| `tracker/Floorline-Tracker.xlsx` | Removed from the index. The paid file must not be committed. History on `main` still has older copies. This audit does not put the file back and does not rewrite history. |
| `tracker/build_tracker.py` | Instrument column, tick lookup, class cap, validations. |
| `tracker/gen_presets_tab.py` | Header `max_minis`. A generic count fills both cap columns. |
| `tracker/presets_tab.csv` | Regenerated from that generator. |
| `tracker/sheet_logic.py` | Same cap rules as the sheet, plus the reclassified scenarios. |
| `tracker/golden_map.json` | Regenerated from `sheet_logic.py`. |
| `tracker/test_tracker.py` | Column map and the new status cases. |
| `tracker/verify_engine.py` | LibreOffice comparison harness for the ten account rows. |

## Questionable, and what was done

1. Disclaimer text inside `tracker/build_tracker.py` still said "Spec: tracker v0.1.0" after the rest of that file moved to v0.2.0. That is a leftover in a related file, not a second feature. The following commit sets it to v0.2.0. The file was not reverted.
2. Untracking `tracker/Floorline-Tracker.xlsx` deletes the blob from this branch's tree. It was required so the paid file is not in the commit. It is not reverted. No other public file is deleted.
3. `js/config.js`, Gumroad URLs, and site assets are not in the diff.

`git diff` of golden expected values: no old case changed its input or expected output.

## Daily-loss status (follow-up on 19304db)

An independent LibreOffice check found equity 49,000 (day reference 50,000, DLL 1,000) and equity 48,950 both left Accounts!AE false, daily room 0, and CONTRACTS 0. Every engine clamped daily capacity at 0. `daily_loss.enforcement` was stored on presets and described in MATH.md, and nothing read it.

This change does not add a feature beside that status. Preset numbers are unchanged. The new Presets column is `dll_enforcement` (column Q), appended so columns A–P stay put. Positive rooms in RR-18..RR-21 stay the same numbers; each risk_room result also carries `daily_status`. Old futures inputs and expected counts are unchanged. The four required caps stay 13 / 1 / 5 / 50.

| File | Why it is in this change |
|---|---|
| `golden/oracle.py`, `js/oracle.js` | Signed daily capacity, ROUND_FLOOR to the cent, and `daily_status`. |
| `js/app.js`, `css/app.css` | The page shows the status instead of a tradable count when capacity is ≤ 0 or the floor is hit. Preset enforcement is passed through. Custom leaves it unstated. |
| `tracker/build_tracker.py` | Workbook formulas. AS is the enforcement input. AU is the hidden trade-status word. AE is true for a floor hit or a hard daily exceed. |
| `tracker/sheet_logic.py`, `tracker/test_tracker.py` | Same rules, plus the boundary rows. |
| `tracker/gen_presets_tab.py`, `tracker/presets_tab.csv` | Export the existing enforcement field. |
| `golden/cases.json`, `tracker/golden_map.json` | Regenerated. |
| `docs/MATH.md`, `tracker/FORMULAS.md`, `README.md`, `docs/DEPLOY-CHECKLIST.md` | The status rules and the precedence order. |

Hard vs soft, as of the commit this section describes: `hard` means the firm fails the account for going past the daily limit, so the status is BREACHED and AE is true. `soft` (Topstep) and a blank enforcement mean the rule does not define that breach, so the status is DAILY LIMIT EXCEEDED and AE stays false. Both block trading. Exactly zero is DAILY LIMIT REACHED, also blocked, also not a breach. A floor hit is BREACHED and outranks the daily word. INVALID and INCOMPLETE are still decided first and stay different words.

That blank-as-soft sentence is superseded. A later commit on this branch stops treating a blank or unconfirmed rule as soft. Below zero with no confirmed hard or soft is `RULE CONFIRMATION REQUIRED`, the breached flag is `UNCONFIRMED`, and Flags shows `DLL RULE UNCONFIRMED` even while room is above zero. Confirmed soft stays `DAILY LIMIT EXCEEDED`. Confirmed hard stays `BREACHED`. Exactly zero stays `DAILY LIMIT REACHED` for all three. See `docs/PRESET-SOURCES.md` and `docs/MATH.md`.

The exact-zero sentence in that paragraph is superseded too. A later commit adds `dll_boundary`, separate from hard/soft. Exactly zero is `BREACHED` only for confirmed hard + `reach`. Confirmed `exceed` (hard or soft) and soft + `reach` are `DAILY LIMIT REACHED`. Soft never breaches. Exactly zero with either classification blank is `RULE CONFIRMATION REQUIRED` and the breached flag is `UNCONFIRMED`. Room below zero still ignores the boundary. Flags add `DLL BOUNDARY UNCONFIRMED` while a numeric DLL is on and reach/exceed is blank. The sheet input is Accounts column AV. Presets column R carries the preset value.
