# Deployment and rollback

This checklist is for the owner. It does not deploy anything. The free site and the paid workbook are different artifacts.

## What is public today

GitHub Pages for `dctrades22/floorline` is **Deploy from a branch**, branch `main`, folder `/` (root). The Pages API reports `build_type: legacy` and `source: {branch: main, path: /}`. The only Actions workflow is the automatic `pages-build-deployment` workflow GitHub adds for that setting. There is no project workflow under `.github/workflows`, and there is no `gh-pages` branch.

A push to `main` publishes the repository root, including `index.html`, `js/`, `data/`, and anything else that is not gitignored. The live site is https://dctrades22.github.io/floorline/.

## Paid workbook vs public site

Anyone who clones `main` can rebuild the paid workbook. These files are the product:

- `tracker/build_tracker.py` writes the xlsx
- `tracker/FORMULAS.md` is the formula spec
- `tracker/presets_tab.csv` and `data/presets.json` are the preset tables
- `tracker/Floorline-Tracker.xlsx` was committed on `main` before this branch (the raw GitHub URL is a free copy)

Practical split, without hiding the free calculator:

1. Keep the free site on this public repo: `index.html`, `css/`, `js/`, `data/`, `assets/`, `docs/MATH.md`.
2. Move `tracker/` (builder, formula spec, workbook tests, presets tab) to a private repository. Build the xlsx there.
3. Leave `tracker/Floorline-Tracker.xlsx` gitignored. This branch stops tracking it. History on `main` still contains older copies until the owner rewrites history, which this change does not do.
4. Upload only the private build to Gumroad.

The math is already public in the free calculator. A private builder stops one-click cloning of the exact file. It does not stop someone from recreating a spreadsheet from the site.

## Before replacing the Gumroad file

1. On this branch, `node test/run.js`, `python3 golden/oracle.py --check`, `python3 tracker/sheet_logic.py --check`, and `python3 tracker/test_tracker.py` are green.
2. Open the xlsx in Excel 2019 or Microsoft 365 (the file uses `MAXIFS` and `TEXTJOIN`). LibreOffice is the engine used in the tests. Excel itself has not been re-tested in this change.
3. Spot-check one row of each instrument: MES $200 / 12 ticks / 50 micros = 13; ES $200 / 12 / 5 minis = 1; NQ $200 / 8 / 10 minis = 5; MNQ $200 / 8 / 100 micros = 50.
4. Confirm a blank instrument says INCOMPLETE, a blank cap for that instrument says INCOMPLETE, cap 0 sizes 0, and NONE still respects the daily loss limit and the floor.
5. Do not commit the xlsx. Do not push this branch until the checks above are accepted.

## Replacing the file for existing buyers

Gumroad serves the product's current content from the buyer's Library and receipt link.

- Content tab: "Your customers will see the product just as you see it in the editor." https://gumroad.com/help/article/149-adding-a-product
- Library: "click on the product's card and you'll see the product's up-to-date files and posts." https://gumroad.com/help/article/211-im-not-receiving-updates.html
- If the product uses versions, files belong to a version. Reassign a purchase from the Sales dashboard (no charge, no refund) and resend the receipt. https://gumroad.com/help/article/126-setting-up-versions-on-a-digital-product and https://gumroad.com/blog/p/update-customers-variants-versions-tiers
- API `files` on `PUT /v2/products/:id` replaces the whole file list. Keep existing file ids if other files must stay. https://gumroad.com/api

Steps:

1. Duplicate the current Gumroad file to a local archive named with the date, before replacing it.
2. Edit the product (or the version buyers actually own). Replace the xlsx in the Content tab. Publish.
3. Buy a test copy, or open an existing receipt, and confirm the new file downloads.
4. Resend receipts only if buyers need the email again. The Library should already show the new file.
5. Tell buyers the sheet changed: add the Instrument column, tick value is calculated, and mini/micro caps are separate. Old workbooks do not pick up the new formulas by themselves. Buyers who already typed a manual tick value must pick ES, MES, NQ, or MNQ and enter both caps.

## Shipping the free site

1. Merge the approved branch to `main`. That is the Pages deploy.
2. Watch the `pages-build-deployment` run. The site should still show the firm chips, a floor, and a contract count.
3. On the calculator, MES with a stated micro cap must size from tick 1.25. Clearing the cap must show INCOMPLETE, not an unlimited size. NONE must still clamp to the binding room.

## Rollback

**Paid file.** Upload the archived previous xlsx to the same Gumroad content slot (or reassign the version). Resend a receipt if a buyer already downloaded the bad file. Their old download is not updated on disk; only the Library copy changes.

**Free site.** `git revert` the merge commit on `main` and push. Pages rebuilds from `main`. Do not force-push and do not delete `main`. If the bad commit is the tip and has not been announced, a revert is still the safer rollback.

**Do not** roll back by editing `gh-pages` (there is no such branch) and do not change the Gumroad product URL in `js/config.js` as part of a formula fix.
