# Deployment and rollback

This checklist is for the owner. It does not deploy anything. The free site and the paid workbook are different artifacts.

## What is public today

GitHub Pages for `dctrades22/floorline` is **Deploy from a branch**, branch `main`, folder `/` (root). The Pages API reports `build_type: legacy` and `source: {branch: main, path: /}`. The only Actions workflow is the automatic `pages-build-deployment` workflow GitHub adds for that setting. There is no project workflow under `.github/workflows`, and there is no `gh-pages` branch.

A push to `main` publishes the repository root, including `index.html`, `js/`, `data/`, and anything else that is not gitignored. The live site is https://dctrades22.github.io/floorline/.

## Build the paid workbook

From a clean checkout of the commit you intend to ship (do not build from a dirty tree):

```sh
git archive HEAD | tar -x -C /tmp/floorline-release
cd /tmp/floorline-release
python3 tracker/build_tracker.py
sha256sum tracker/Floorline-Tracker.xlsx
python3 tracker/test_tracker.py --workbook tracker/Floorline-Tracker.xlsx --expect-sha "$(sha256sum tracker/Floorline-Tracker.xlsx | awk '{print $1}')"
```

`python3 tracker/build_tracker.py` writes `tracker/Floorline-Tracker.xlsx`. That path is gitignored. The default epoch is `2026-10-23T00:00:00Z` (`SOURCE_DATE_EPOCH=1792713600`). Set `SOURCE_DATE_EPOCH` to another integer UTC second only if you want a different stamp; the Gumroad file must be the same bytes the test hashed.

Two archives of the same commit, built with the same epoch, must have the same SHA-256. The test copies that file, fills inputs, and recalculates in LibreOffice. It exits non-zero if the file's hash changes or does not match `--expect-sha`.

Excel 2019 or Microsoft 365 is still required before Gumroad (the file uses `MAXIFS` and `TEXTJOIN`). LibreOffice is the engine in the tests. Excel itself has not been re-tested.

Spot-check: MES $200 / 12 ticks / 50 micros = 13; ES $200 / 12 / 5 minis = 1; NQ $200 / 8 / 10 minis = 5; MNQ $200 / 8 / 100 micros = 50. Blank instrument is INCOMPLETE. A blank cap for that class is INCOMPLETE. Cap 0 sizes 0. NONE still respects the daily loss limit and the floor.

Daily loss, static 50,000 / 2,000 so the floor is 48,000 (these equities are not a floor hit). DLL 1,000, day reference 50,000, MES, 12 ticks: equity 49,000.01 → daily room 0.01 and a numeric contract count (OK). Equity 49,000 → CONTRACTS `DAILY LIMIT REACHED`, breached flag false. Equity 48,950 with enforcement blank or soft → `DAILY LIMIT EXCEEDED`, breached flag false, daily room −50. The same 48,950 with enforcement `hard` → `BREACHED`, breached flag true, daily room still −50. Equity 48,000 → `BREACHED` from the floor, and the room columns say BREACHED. A numeric 0 is not a daily-limit status.

Tick values: `docs/CME-TICKS.md`. ES, MES, NQ and MNQ were read from the CME Rulebook on 2026-10-23. ES is no longer flagged.

## Paid workbook vs public site

Anyone who clones `main` can still rebuild the paid workbook. `docs/PRIVATE-TRACKER-MIGRATION.md` is the plan for a private tree. It does not delete public files. Run `python3 tools/export_private_tracker.py <tarball>` to pack a ready-to-init copy. Removing `tracker/` from this repo needs a separate approval.

## Replacing the Gumroad file

Full quotes and UNCONFIRMED items: `docs/GUMROAD-FILE-REPLACE.md` (pages read 2026-10-23).

Do not assume buyers are emailed when the file is replaced. The fetched help pages do not say that. Library shows up-to-date files. Emails and Workflows are a separate step. Workflow triggers listed that day do not include "file replaced."

1. Archive the current Gumroad file locally, named with the date.
2. Replace the xlsx on the Content tab of the product (or the version buyers own). Publish.
3. Download from a receipt or the Library and match the SHA-256.
4. Send an Email to Customers about the Instrument column, the calculated tick, and the separate caps. Resend a receipt only if a buyer needs the mail again.
5. Old filled workbooks do not pick up the new formulas.

API `files` on `PUT /v2/products/:id` replaces the whole file list (https://gumroad.com/api). Keep existing file ids if other files must stay.

## Shipping the free site

1. Merge the approved branch to `main`. That is the Pages deploy.
2. Watch the `pages-build-deployment` run. The site should still show the firm chips, a floor, and a contract count.
3. On the calculator, MES with a stated micro cap must size from tick 1.25. Clearing the cap must show INCOMPLETE. NONE must still clamp to the binding room. ES, MES, NQ and MNQ should show as verified on the CME rulebook.

## Rollback

**Paid file.** Upload the archived previous xlsx to the same Gumroad content slot (or reassign the version). Resend a receipt if a buyer already downloaded the bad file and needs the mail. Their old download is not updated on disk; the Library card is what shows the current file (`docs/GUMROAD-FILE-REPLACE.md`).

**Free site.** `git revert` the merge commit on `main` and push. Pages rebuilds from `main`. Do not force-push and do not delete `main`. If the bad commit is the tip and has not been announced, a revert is still the safer rollback.

**Do not** roll back by editing `gh-pages` (there is no such branch) and do not change the Gumroad product URL in `js/config.js` as part of a formula fix. Do not rewrite history to remove the builder or the old xlsx.
