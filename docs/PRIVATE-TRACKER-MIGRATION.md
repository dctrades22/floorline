# Private tracker migration

This plan does not create a GitHub repository, does not push, and does not delete anything from the public Floorline repo. Removing `tracker/` from the public repo needs a separate owner approval after the private copy is proven.

## What is public today

Anyone who clones `main` can rebuild the paid workbook. The builder, the formula spec, the preset tab, and the tests live in `tracker/`. `data/presets.json`, `data/contracts.json`, `golden/oracle.py`, and `golden/cases.json` are also public, and the free calculator already publishes the math. An older xlsx is still in `main` history.

## Ready-to-init bundle

From a checkout of this branch:

```sh
python3 tools/export_private_tracker.py /tmp/floorline-private-tracker.tar.gz
```

The tarball is a standalone tree with the same relative paths the builder expects (`tracker/`, `data/`, `golden/`). It contains its own README and this migration note. Unpack it somewhere that is not the public repo, then:

```sh
tar -xzf floorline-private-tracker.tar.gz
cd floorline-private-tracker
git init
git add .
git commit -m "Import Floorline tracker"
python3 -m pip install --user openpyxl
python3 tracker/build_tracker.py
python3 tracker/test_tracker.py --workbook tracker/Floorline-Tracker.xlsx
```

Do not add a public remote. Do not commit `tracker/Floorline-Tracker.xlsx` (the private `.gitignore` ignores it).

## Later removal from the public repo (owner approval required)

Do this only after the private tree builds the same SHA-256 as the tested Gumroad file.

1. Keep the free site on the public repo: `index.html`, `css/`, `js/`, `data/`, `assets/`, `docs/MATH.md`, `docs/CME-TICKS.md`.
2. In a new commit on a branch, stop publishing `tracker/` (builder, formula spec, workbook tests, presets tab) and `tools/export_private_tracker.py`.
3. Leave `golden/` if the public site tests still need it. `node test/run.js` uses `golden/cases.json` and does not need `tracker/`.
4. Do not rewrite history to purge the old xlsx or the old builder. Say in the commit that past clones can still rebuild old files.
5. Do not change `js/config.js` or the Gumroad URL as part of the split.
6. Pages deploys from `main`. Merging the removal is a site deploy. Watch `pages-build-deployment` and confirm the calculator still loads.

Until that approval, both copies exist: the public `tracker/` stays, and the tarball is only an artifact.
