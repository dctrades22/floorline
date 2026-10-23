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
