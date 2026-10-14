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
- Contract specs (`data/contracts.json`) are labelled *verified indirectly* (CME pages are bot-blocked).
- Micro/mini caps are per firm. When a firm only states a generic contract count, that count is applied to every
  instrument (conservative); no 10:1 equivalence is assumed.

## Math
`js/oracle.js` is a line-by-line port of `golden/oracle.py` on top of `js/decimal.js`, a small BigInt decimal with the
same 50-digit context and rounding modes. Safety values round conservatively. The UI only formats oracle output.

How UI inputs become oracle events: static → `[mark(balance)]`; EOD trailing → `[eod(highest close), mark(balance)]`;
intraday trailing → `[mark(peak equity), mark(balance)]`. Percent daily limits are converted to $ exactly
(rate × balance at last reset, or × start for `pct_of_start`).

## Tests
```sh
node test/run.js        # 49 golden cases, presets schema + semantic rules, contracts, data bundle freshness
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

Before publishing, re-verify presets older than a few weeks and the flagged contract specs (ES, MCL).
