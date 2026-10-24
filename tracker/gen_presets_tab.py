#!/usr/bin/env python3
"""Deterministically generate the Presets tab (tracker/presets_tab.csv) from data/presets.json.
verified + partial only; custom_only excluded; one 'Manual' row appended. --check diffs against the committed CSV."""
import csv, io, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tracker", "presets_tab.csv")
COLS = ["preset_key", "status", "dd_type", "start_balance", "dd_amount", "dd_pct", "lock_token", "breach_on_touch",
        "dll_token", "max_minis", "max_micros", "needs_user", "source_url", "checked_date", "source_page_date", "preset_id",
        "dll_enforcement", "dll_boundary"]

def rows():
    d = json.load(open(os.path.join(ROOT, "data", "presets.json")))
    out = []
    for p in d["presets"]:
        if p["status"] == "custom_only": continue
        need = []
        lk = p["lock"]
        if p["drawdown"]["type"] == "static" or lk["kind"] == "none": lock = "NONE"
        elif lk["kind"] == "offset": lock = lk["offset_usd"]
        else: lock = ""; need.append("lock_offset(" + lk["kind"] + ")")
        dl = p["daily_loss"]
        enf = dl.get("enforcement") or ""
        if enf not in ("hard", "soft"): enf = ""
        boundary = dl.get("boundary") or ""
        if boundary not in ("reach", "exceed"): boundary = ""
        if dl["kind"] == "none": dll = "NONE"
        elif dl["kind"] == "fixed_usd" and not dl["optional"]: dll = dl["amount_usd"]
        else: dll = ""; need.append("dll_usd(" + dl["kind"] + (",optional" if dl["optional"] else "") + ")")
        mc = p["max_contracts"]
        # Specific class wins. A generic count, and only a generic count, fills both classes.
        if mc["minis"] is None and mc["micros"] is None and mc["contracts"]:
            max_minis = max_micros = mc["contracts"]
        else:
            max_minis = mc["minis"] or ""
            max_micros = mc["micros"] or ""
        if not max_minis: need.append("max_minis")
        if not max_micros: need.append("max_micros")
        if p["account_size"] is None: need.append("start_balance")
        touch = "" if p["breach_on_touch"] is None else ("TRUE" if p["breach_on_touch"] else "FALSE")
        if not touch: need.append("breach_on_touch")
        if p["breach_on_touch_after_lock"] is not None: need.append("touch_after_lock_not_modeled")
        size = p["account_size"] or ""
        key = f'{p["firm"]} | {p["plan"]} | {size or "size?"} [{p["id"]}]'
        out.append([key, p["status"], p["drawdown"]["type"], size, p["drawdown"]["amount_usd"] or "",
                    p["drawdown"]["pct_of_start"] or "", lock, touch, dll, max_minis, max_micros,
                    ";".join(need), p["source_url"], p["checked_date"], p["source_page_date"] or "", p["id"], enf, boundary])
    out.append(["Manual", "manual", "", "", "", "", "", "", "", "", "", "all", "", "", "", "", "", ""])
    return out

def render():
    b = io.StringIO(); w = csv.writer(b, lineterminator="\n"); w.writerow(COLS); w.writerows(rows()); return b.getvalue()

if __name__ == "__main__":
    t = render()
    if "--check" in sys.argv:
        ok = open(OUT).read() == t; print("PRESETS_TAB", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
    open(OUT, "w").write(t); print("wrote", OUT, t.count("\n") - 1, "rows")
