#!/usr/bin/env python3
"""Tests the REAL workbook formulas: builds test workbooks with build_tracker.build(), recalculates them headlessly
in LibreOffice, reads the computed cells and compares with golden/cases.json for every golden_map case marked
yes/partial, plus INVALID / INCOMPLETE / BREACHED scenarios.   python3 tracker/test_tracker.py
Case inputs come from QUANT's mapping in tracker/sheet_logic.py (M); the arithmetic under test is the spreadsheet's."""
import datetime, json, os, shutil, subprocess, sys, tempfile
from openpyxl import load_workbook
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_tracker as bt, sheet_logic as sl

GOLD = {c["id"]: c for c in json.load(open(os.path.join(ROOT, "golden", "cases.json")))["cases"]}
GMAP = {c["id"]: c for c in json.load(open(os.path.join(HERE, "golden_map.json")))["cases"]}
COL = {"floor": "Y", "peak": "X", "locked": "Z", "breached": "AA", "equity": "AP", "drawdown_room": "AB",
       "daily_room": "AC", "binding_room": "AD", "binding": "AE", "contracts": "AG", "capped": "AH",
       "effective_risk": "AF", "risk_limited_by_room": "AI", "actual_risk": "AM"}

def acc_row(cid, si):
    a = {"A": cid, "B": "Manual", "D": si["type"], "E": si["start"], "F": si["dd"], "G": si.get("lock", "NONE"),
         "H": si.get("touch", True), "I": si.get("dll", "NONE"), "J": si.get("maxc", "NONE"), "K": si["equity"]}
    if "day_ref" in si: a["L"] = si["day_ref"]
    if "risk" in si: a.update(M=si["risk"], N=si["ticks"], O=si["tv"])
    return a

def log_rows(cid, si):
    out = []
    for i, r in enumerate(si.get("log", [])):
        row = {"A": cid, "B": datetime.date(2026, 10, 1) + datetime.timedelta(days=i), "C": r["eod"]}
        if "high" in r: row["D"] = r["high"]
        if "low" in r: row["E"] = r["low"]
        out.append(row)
    return out

# ---- scenarios ----
GOLDEN = []   # (cid, account, logs, fields)
for cid, g in GMAP.items():
    if g["reproducible"] in ("yes", "partial") and sl.M[cid][2] is not None:
        si = sl.M[cid][2]; GOLDEN.append((cid, acc_row(cid, si), log_rows(cid, si), g["checked_fields"]))

BASE = dict(type="static", start=50000, dd=2000, equity=49000, risk=300, ticks=16, tv=1.25)
def S(cid, **kw): si = dict(BASE); si.update(kw); return acc_row(cid, si)
STATUS = [  # (case id, account dict, logs, {column: expected})
 ("IV-36", S("IV-36", ticks=0), [], {"W": "OK", "AF": "INVALID", "AG": "INVALID"}),
 ("IV-38", {**S("IV-38"), "M": None}, [], {"W": "OK", "AF": "INCOMPLETE", "AG": "INCOMPLETE"}),
 ("IV-39", S("IV-39", type="eod_trailing", lock=-2500), [], {"W": "INVALID", "Y": "INVALID", "AG": "INVALID"}),
 ("IV-40", S("IV-40", lock=0), [], {"W": "INVALID", "Y": "INVALID"}),
 ("IV-41", S("IV-41", type="hybrid"), [], {"W": "INVALID", "Y": "INVALID"}),
 ("IV-43", S("IV-43", dll=1000), [], {"W": "INCOMPLETE", "AD": "INCOMPLETE", "AG": "INCOMPLETE"}),
 ("IV-44", {k: v for k, v in S("IV-44").items() if k != "D"}, [], {"W": "INCOMPLETE", "Y": "INCOMPLETE"}),
 ("IV-46", S("IV-46", maxc=2.9), [], {"W": "INVALID", "AG": "INVALID"}),
 ("IV-47", S("IV-47", ticks=0.5), [], {"W": "OK", "AG": "INVALID"}),
 ("IV-48", S("IV-48", touch="false"), [], {"W": "INVALID", "Y": "INVALID"}),
 ("X-INCOMPLETE-equity", {**S("X1"), "K": None}, [], {"W": "INCOMPLETE", "Y": "INCOMPLETE", "AD": "INCOMPLETE"}),
 ("X-INCOMPLETE-partial-preset", {"A": "X2", "B": "Apex Trader Funding | Intraday Trailing Evaluation | 50000 [P006]", "K": 50000}, [],
     {"C": "partial", "W": "INCOMPLETE", "Y": "INCOMPLETE"}),
 ("X-INVALID-subcent-start", S("X3", start=50000.005), [], {"W": "INVALID"}),
 ("X-INVALID-dup-id", None, [], {}),  # filled below
 ("X-INVALID-log-high<low", S("X5"), [{"A": "X5", "B": datetime.date(2026, 10, 1), "C": 49500, "D": 49000, "E": 49200}],
     {"W": "INVALID", "AG": "INVALID", "log:I": "INVALID"}),
 ("X-INVALID-log-dup-date", S("X6"), [{"A": "X6", "B": datetime.date(2026, 10, 1), "C": 49500}, {"A": "X6", "B": datetime.date(2026, 10, 1), "C": 49600}],
     {"W": "INVALID", "log:I": "INVALID"}),
 ("X-BREACHED-via-log", S("X7", equity=49800), [{"A": "X7", "B": datetime.date(2026, 10, 1), "C": 49800, "D": 50100, "E": 47990}],
     {"W": "OK", "AA": True, "AB": "BREACHED", "AD": "BREACHED", "AG": "BREACHED", "AM": "BREACHED", "log:I": "BREACHED", "Y": 48000}),
 ("X-BREACHED-touch-now", S("X8", equity=48000), [], {"AA": True, "AB": "BREACHED", "AG": "BREACHED"}),
 ("X-NOT-BREACHED-touch-false", S("X9", equity=48000, touch=False), [], {"AA": False, "AB": 0, "AG": 0}),
 ("X-OK-verified-preset", {"A": "X10", "B": "Topstep | Trading Combine | 50000 [P001]", "I": "NONE", "K": 50500, "M": 300, "N": 16, "O": 1.25}, [],
     {"C": "verified", "W": "OK", "Y": 48000, "AD": 2500, "AG": 5, "AH": True}),
]
dup = S("DUP"); STATUS[[s[0] for s in STATUS].index("X-INVALID-dup-id")] = ("X-INVALID-dup-id", [dup, dict(dup)], [], {"W": "INVALID"})

def run_batches(items):
    tmp = tempfile.mkdtemp(); files = []
    for b in range(0, len(items), 10):
        chunk = items[b:b + 10]; accs, logs = [], []
        for it in chunk:
            a = it[1]
            if isinstance(a, list): accs.extend(a)
            else: accs.append(a)
            logs.extend(it[2])
        assert len(accs) <= 10
        p = os.path.join(tmp, f"b{b // 10:02d}.xlsx")
        bt.build(p, [{k: v for k, v in a.items() if v is not None} for a in accs], logs)
        wb = load_workbook(p); ws = wb["Accounts"]          # test-only probe: oracle 'equity' = CENT_DOWN(K)
        for r in range(2, 12): ws[f"AP{r}"] = f"=IF(K{r}=\"\",\"\",INT(ROUND(K{r}*100,6))/100)"
        wb.save(p); files.append((p, chunk))
    out = os.path.join(tmp, "calc")
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", out] + [f for f, _ in files],
                   check=True, capture_output=True, timeout=600)
    res = {}
    for p, chunk in files:
        wb = load_workbook(os.path.join(out, os.path.basename(p)), data_only=True)
        acc, log = wb["Accounts"], wb["Daily Log"]
        ids = {acc[f"A{r}"].value: r for r in range(11, 1, -1) if acc[f"A{r}"].value is not None}
        logstat = {}
        for r in range(2, 60):
            if log[f"A{r}"].value: logstat.setdefault(log[f"A{r}"].value, []).append(log[f"I{r}"].value)
        for it in chunk:
            aid = (it[1][0] if isinstance(it[1], list) else it[1])["A"]
            res[it[0]] = (lambda c, r=ids[aid], aid=aid, acc=acc, logstat=logstat: (logstat.get(aid, [None])[-1] if c == "log:I" else acc[f"{c}{r}"].value))
    shutil.rmtree(tmp) if os.environ.get("KEEP") is None else print("kept", tmp)
    return res

SUBCENT = {"DD-17"}

def fmt(v):
    if isinstance(v, bool) or v is None: return v
    if isinstance(v, (int, float)): return f"{v:.2f}"
    return v

def main():
    items = GOLDEN + STATUS
    res = run_batches(items)
    passed = failed = 0; notes = []
    print(f"{'case':30} {'map':8} result")
    for cid, _, _, fields in GOLDEN:
        get = res[cid]; exp = GOLD[cid]["expected"]; bad = {}
        if cid in SUBCENT:   # FORMULAS §1: sub-cent money inputs are rejected -> every output INVALID (golden_map: partial)
            bad = {f: get(COL[f]) for f in fields if f != "equity" and get(COL[f]) != "INVALID"}
            passed += not bad; failed += bool(bad)
            print(f"{cid:30} {'partial':8} {'PASS' if not bad else 'FAIL ' + str(bad)}  (sub-cent input -> INVALID as specified, not oracle values)")
            continue
        for f in fields:
            got = get(COL[f]); e = exp[f]
            if f == "contracts": ok = got == e
            elif f == "daily_room" and e is None: ok = got == "NONE"
            elif got == "BREACHED" and f in ("drawdown_room",) and exp.get("breached"): ok = e == "0.00"; notes.append(cid)
            else: ok = fmt(got) == e
            if not ok: bad[f] = (got, e)
        status = "PASS" if not bad else f"FAIL {bad}"
        passed += not bad; failed += bool(bad)
        print(f"{cid:30} {GMAP[cid]['reproducible']:8} {status}  ({len(fields)} fields)")
    for cid, _, _, want in STATUS:
        get = res[cid]; bad = {}
        for c, e in want.items():
            got = get(c)
            ok = (fmt(got) == fmt(e)) if not isinstance(e, str) else got == e
            if not ok: bad[c] = (got, e)
        passed += not bad; failed += bool(bad)
        print(f"{cid:30} {'status':8} {'PASS' if not bad else 'FAIL ' + str(bad)}  ({len(want)} cells)")
    print(f"\nGOLDEN yes/partial: {sum(1 for c in GOLDEN)} cases; STATUS scenarios: {len(STATUS)}")
    print(f"TOTAL PASS {passed} / {passed + failed}")
    if notes: print("note: drawdown_room shows 'BREACHED' (FORMULAS AB) where the oracle reports 0.00:", ", ".join(notes))
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
