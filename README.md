# Floorline

Prop-firm drawdown floor, remaining room and position-size calculator. A static site: no backend, no tracking,
no CDN, no web fonts, no dependencies. Open `index.html` directly from disk and it works.

**Educational only.** Not affiliated with any firm. Rules change; always confirm in your firm dashboard. Not financial advice.

## What it does
- Firm → plan → size presets fill the rule (`data/presets.json`, QUANT spec v0.2.0 @ be940d1). Every preset shows its
  source link, checked date and a verified / partial / custom-only badge.
  - **partial**: fields the firm's page does not state are left blank, editable and flagged "not stated by firm".
  - **custom_only**: opens in Custom with the reason; no numbers are carried over.
  - **Edit as custom** copies the current rule into fully editable fields.
- Outputs floor, drawdown room, daily room, binding room (and which constraint binds), lock status, max contracts for the
  chosen instrument with a quick by-stop table, plus CLAMPED / CAPPED / BREACHED flags.
- ES, MES, NQ and MNQ tick values were read from the CME Rulebook on 2026-10-23 (`docs/CME-TICKS.md`). Other symbols in `data/contracts.json` are still labelled *verified indirectly*. MCL remains flagged.
- Tick value comes from the instrument. ES 12.50, MES 1.25, NQ 5.00, MNQ 0.50. It is not a separate input.
- ES/NQ use the firm's mini cap. MES/MNQ (and the other micros) use the micro cap. A generic contract count, and only
  a generic count, applies to every instrument. No 10:1 equivalence is assumed. Blank cap = incomplete. Explicit 0
  stays 0. Type NONE to remove only the contract cap. Risk, trailing drawdown and the daily loss limit stay active.
  Daily capacity above zero sizes normally. Exactly zero is BREACHED only when the confirmed rule is hard and the
  boundary is reach. Confirmed exceed, and confirmed soft even with reach, shows DAILY LIMIT REACHED. Soft never
  breaches. Exactly zero with hard/soft or reach/exceed unconfirmed shows RULE CONFIRMATION REQUIRED and does not
  read as safe. Below zero ignores the boundary: BREACHED when hard, DAILY LIMIT EXCEEDED when soft, and
  RULE CONFIRMATION REQUIRED when hard/soft is not confirmed. A blank rule is not soft. The page flags
  DLL RULE UNCONFIRMED and DLL BOUNDARY UNCONFIRMED independently while that limit is on, including while room is
  still above zero. A preset with either flag is not fully verified. A drawdown floor hit is BREACHED and outranks
  the daily status. None of those statuses can be traded.
- The paid 10-account workbook is built from `tracker/` and is not part of the GitHub Pages site. Its instrument
  list is ES, MES, NQ, MNQ. See `docs/DEPLOY-CHECKLIST.md`.

## Math
`js/oracle.js` is a line-by-line port of `golden/oracle.py` on top of `js/decimal.js`, a small BigInt decimal with the
same 50-digit context and rounding modes. Safety values round conservatively. The UI only formats oracle output.

How UI inputs become oracle events: static → `[mark(balance)]`; EOD trailing → `[eod(highest close), mark(balance)]`;
intraday trailing → `[mark(peak equity), mark(balance)]`. Percent daily limits are converted to $ exactly
(rate × balance at last reset, or × start for `pct_of_start`).

## Tests
```sh
node test/run.js        # golden cases (legacy single-cap plus instrument-aware), presets, contracts, data bundle
python3 golden/oracle.py --check   # QUANT's reference check
```
Data is embedded into `js/data.js` (browsers block `fetch` on `file://`). After editing `data/*.json` run
`node tools/build-data.js`; the test fails if the bundle is stale.

Screenshots: `sh tools/shots.sh` (needs a local Chrome/Chromium) writes `shots/`.

## Deploy to GitHub Pages
1. Create a GitHub account and an empty repository (e.g. `floorline`).
2. From this folder:
   ```sh
   git remote add origin https://github.com/<you>/floorline.git
   git push -u origin master      # or main
   ```
3. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**, branch `master` (or `main`),
   folder `/ (root)`. Save.
4. After a minute the site is at `https://<you>.github.io/floorline/`. All paths are relative, so no config is needed.
5. Optional: add a `CNAME` file for a custom domain.

Before publishing, re-verify presets older than a few weeks and the flagged contract spec (MCL). ES, MES, NQ and MNQ were checked on 2026-10-23.
