#!/usr/bin/env python3
"""Tests the REAL workbook formulas. Recalculates them headlessly in LibreOffice, reads the computed cells and
compares with golden/cases.json for every golden_map case marked yes/partial, plus INVALID / INCOMPLETE / BREACHED
scenarios.

  python3 tracker/test_tracker.py
      builds a fresh workbook per batch with build_tracker.build()

  python3 tracker/test_tracker.py --workbook PATH [--expect-sha HEX]
      copies PATH (the release xlsx) and writes only scenario inputs into the copy.
      PATH itself is not modified. The test prints PATH's SHA-256 before and after and exits
      non-zero if those hashes differ, or if --expect-sha does not match. Formulas are the
      ones stored in PATH, not a second build().

Case inputs come from QUANT's mapping in tracker/sheet_logic.py (M); the arithmetic under test is the spreadsheet's."""
import datetime, hashlib, json, os, shutil, subprocess, sys, tempfile
from openpyxl import load_workbook
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_tracker as bt, sheet_logic as sl

GOLD = {c["id"]: c for c in json.load(open(os.path.join(ROOT, "golden", "cases.json")))["cases"]}
GMAP = {c["id"]: c for c in json.load(open(os.path.join(HERE, "golden_map.json")))["cases"]}
COL = {"floor": "AC", "peak": "AB", "locked": "AD", "breached": "AE", "equity": "AT", "drawdown_room": "AF",
       "daily_room": "AG", "binding_room": "AH", "binding": "AI", "contracts": "AK", "capped": "AL",
       "effective_risk": "AJ", "risk_limited_by_room": "AM", "actual_risk": "AQ"}
TICK_INST = {1.25: "MES", 12.5: "ES", 5.0: "NQ", 0.5: "MNQ"}
MINI = {"ES", "NQ"}
MICRO = {"MES", "MNQ"}

def inst_for(si):
    if "instrument" in si: return si["instrument"]
    if "tv" not in si: return "MES"
    return TICK_INST.get(round(float(si["tv"]), 2))

def acc_row(cid, si):
    inst = inst_for(si)
    if inst is None: raise ValueError("unmapped tick for " + cid)
    if "max_minis" in si or "max_micros" in si:
        max_minis, max_micros = si.get("max_minis", "NONE"), si.get("max_micros", "NONE")
    elif "maxc" in si:
        u = str(inst).strip().upper()
        if u in MINI: max_minis, max_micros = si["maxc"], "NONE"
        elif u in MICRO: max_minis, max_micros = "NONE", si["maxc"]
        else: max_minis, max_micros = si["maxc"], si["maxc"]
    else:
        max_minis, max_micros = "NONE", "NONE"
    a = {"A": cid, "B": "Manual", "D": si["type"], "E": si["start"], "F": si["dd"], "G": si.get("lock", "NONE"),
         "H": si.get("touch", True), "I": si.get("dll", "NONE"), "J": max_minis, "K": max_micros,
         "L": inst, "M": si["equity"]}
    if "day_ref" in si: a["N"] = si["day_ref"]
    if "risk" in si: a.update(O=si["risk"], P=si["ticks"])
    if si.get("dll_enforcement"): a["AS"] = si["dll_enforcement"]
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
SKIPPED = []  # OLD single-cap rows whose tick is not ES/MES/NQ/MNQ; Python sheet_logic still checks them
for cid, g in GMAP.items():
    if g["reproducible"] in ("yes", "partial") and sl.M[cid][2] is not None:
        si = sl.M[cid][2]
        if inst_for(si) is None:
            SKIPPED.append(cid); continue
        GOLDEN.append((cid, acc_row(cid, si), log_rows(cid, si), g["checked_fields"]))

BASE = dict(type="static", start=50000, dd=2000, equity=49000, risk=300, ticks=16, instrument="MES", max_minis="NONE", max_micros=50)
def S(cid, **kw):
    si = dict(BASE); si.update(kw)
    if "maxc" in kw: si.pop("max_minis", None); si.pop("max_micros", None)
    return acc_row(cid, si)
STATUS = [  # (case id, account dict, logs, {column: expected})
 ("IV-36", S("IV-36", ticks=0), [], {"AA": "OK", "AJ": "INVALID", "AK": "INVALID"}),
 ("IV-38", {**S("IV-38"), "O": None}, [], {"AA": "OK", "AJ": "INCOMPLETE", "AK": "INCOMPLETE"}),
 ("IV-39", S("IV-39", type="eod_trailing", lock=-2500), [], {"AA": "INVALID", "AC": "INVALID", "AK": "INVALID"}),
 ("IV-40", S("IV-40", lock=0), [], {"AA": "INVALID", "AC": "INVALID"}),
 ("IV-41", S("IV-41", type="hybrid"), [], {"AA": "INVALID", "AC": "INVALID"}),
 ("IV-43", S("IV-43", dll=1000), [], {"AA": "INCOMPLETE", "AH": "INCOMPLETE", "AK": "INCOMPLETE"}),
 ("IV-44", {k: v for k, v in S("IV-44").items() if k != "D"}, [], {"AA": "INCOMPLETE", "AC": "INCOMPLETE"}),
 ("IV-46", S("IV-46", maxc=2.9), [], {"AA": "INVALID", "AK": "INVALID"}),
 ("IV-47", S("IV-47", ticks=0.5), [], {"AA": "OK", "AK": "INVALID"}),
 ("IV-48", S("IV-48", touch="false"), [], {"AA": "INVALID", "AC": "INVALID"}),
 ("X-INCOMPLETE-equity", {**S("X1"), "M": None}, [], {"AA": "INCOMPLETE", "AC": "INCOMPLETE", "AH": "INCOMPLETE"}),
 ("X-INCOMPLETE-partial-preset", {"A": "X2", "B": "Apex Trader Funding | Intraday Trailing Evaluation | 50000 [P006]", "M": 50000}, [],
     {"C": "partial", "AA": "INCOMPLETE", "AC": "INCOMPLETE"}),
 ("X-INVALID-subcent-start", S("X3", start=50000.005), [], {"AA": "INVALID"}),
 ("X-INVALID-dup-id", None, [], {}),  # filled below
 ("X-INVALID-log-high<low", S("X5"), [{"A": "X5", "B": datetime.date(2026, 10, 1), "C": 49500, "D": 49000, "E": 49200}],
     {"AA": "INVALID", "AK": "INVALID", "log:I": "INVALID"}),
 ("X-INVALID-log-dup-date", S("X6"), [{"A": "X6", "B": datetime.date(2026, 10, 1), "C": 49500}, {"A": "X6", "B": datetime.date(2026, 10, 1), "C": 49600}],
     {"AA": "INVALID", "log:I": "INVALID"}),
 ("X-BREACHED-via-log", S("X7", equity=49800), [{"A": "X7", "B": datetime.date(2026, 10, 1), "C": 49800, "D": 50100, "E": 47990}],
     {"AA": "OK", "AE": True, "AF": "BREACHED", "AH": "BREACHED", "AK": "BREACHED", "AQ": "BREACHED", "log:I": "BREACHED", "AC": 48000}),
 ("X-BREACHED-touch-now", S("X8", equity=48000), [], {"AE": True, "AF": "BREACHED", "AK": "BREACHED"}),
 ("X-NOT-BREACHED-touch-false", S("X9", equity=48000, touch=False), [], {"AE": False, "AF": 0, "AK": 0}),
 ("X-OK-verified-preset", {"A": "X10", "B": "Topstep | Trading Combine | 50000 [P001]", "I": "NONE", "L": "MES", "M": 50500, "O": 300, "P": 16}, [],
     {"C": "verified", "AA": "OK", "Q": 1.25, "AC": 48000, "AH": 2500, "AK": 15, "AL": False, "Z": 50}),
]
D1 = datetime.date(2026, 10, 1)
STATUS += [
 # SPECTER repros
 ("P1 log INCOMPLETE -> account", S("P1", equity=49000), [{"A": "P1", "B": D1, "E": 47000}],
     {"log:I": "INCOMPLETE", "AA": "INCOMPLETE", "AH": "INCOMPLETE", "AK": "INCOMPLETE"}),
 ("P2 orphan log row", [S("P2", equity=49000), S("P2b", equity=49500)], [{"A": "P2x", "B": D1, "C": 49000, "E": 47000}],
     {"logid:P2x": "UNKNOWN_ACCOUNT", "AA": "INCOMPLETE", "AK": "INCOMPLETE", "acc2:AA": "INCOMPLETE", "acc2:AK": "INCOMPLETE",
      "B14": "contains:unknown account ID"}, {"solo": True}),
 ("P2 orphan blank-ID row", S("P2c"), [{"B": D1, "C": 49000}], {"logid:None": "UNKNOWN_ACCOUNT", "AA": "INCOMPLETE", "B14": "nonempty"}, {"solo": True}),
 ("P9 blank max contracts", {**S("P9", instrument="MES", max_minis=5, risk=200, ticks=12), "K": None}, [],
     {"AA": "INCOMPLETE", "AK": "INCOMPLETE", "AR": "contains:MAX CONTRACTS MISSING"}),
 # OLD single max-contracts / manual tick cases, reclassified onto the active cap and the instrument lookup.
 ("M-1 explicit NONE cap", S("M1", instrument="MNQ", max_minis="NONE", max_micros="NONE", risk=500, ticks=1, equity=49000), [],
     {"AA": "OK", "AK": 1000, "Q": 0.5, "AL": False}),
 ("L-1 OLD ZN tick not enterable", S("L1a", instrument="ZN", risk=500, ticks=8), [], {"AA": "INVALID", "AK": "INVALID"}),
 ("L-1 tick 7 dp replaced by bad instrument", S("L1b", instrument="MES "), [], {"AA": "INVALID", "AK": "INVALID"}),
 ("L-2 equity 1e15", S("L2a", equity=1e15), [], {"AA": "INVALID", "AK": "INVALID"}),
 ("L-2 equity 1e8 ok", S("L2b", start=100000000, dd=2000, equity=100000000), [], {"AA": "OK"}),
 ("L-2 log close 1e9", S("L2c"), [{"A": "L2c", "B": D1, "C": 1000000000}], {"log:I": "INVALID", "AA": "INVALID"}),
 ("L-3 none == NONE", S("L3a", type="eod_trailing", lock="none", maxc="None"), [], {"AA": "OK", "AD": False}),
 ("L-3 log id case", S("L3B"), [{"A": "l3b", "B": D1, "C": 49500}], {"logid:l3b": "OK", "AA": "OK"}),
 ("L-3 trailing space type", S("L3c", type="Static "), [], {"AA": "INVALID"}),
 ("M-4 as-of missing", {"A": "M4a", "B": "Topstep | Trading Combine | 50000 [P001]", "I": "NONE", "L": "ES", "M": 50500},
     [], {"AR": "contains:AS-OF DATE MISSING"}),
 ("M-4 stale preset", {"A": "M4b", "B": "Topstep | Trading Combine | 50000 [P001]", "I": "NONE", "L": "ES", "M": 50500},
     [], {"AR": "contains:STALE PRESET", "AA": "OK"}, {"asof": datetime.date(2026, 12, 1)}),
 ("M-4 fresh preset", {"A": "M4c", "B": "Topstep | Trading Combine | 50000 [P001]", "I": "NONE", "L": "ES", "M": 50500},
     [], {"AR": "lacks:STALE", "AA": "OK"}, {"asof": datetime.date(2026, 11, 13)}),
]
dup = S("DUP"); STATUS[[s[0] for s in STATUS].index("X-INVALID-dup-id")] = ("X-INVALID-dup-id", [dup, dict(dup)], [], {"AA": "INVALID"})
STATUS += [
 ("IA-05 missing micro cap", {**S("IA05", instrument="MES", max_minis=5, risk=200, ticks=12), "K": None}, [],
     {"AA": "INCOMPLETE", "AK": "INCOMPLETE", "AR": "contains:MAX CONTRACTS MISSING", "Q": 1.25}),
 ("IA-06 missing mini cap", {**S("IA06", instrument="ES", max_micros=50, risk=200, ticks=12), "J": None}, [],
     {"AA": "INCOMPLETE", "AK": "INCOMPLETE", "AR": "contains:mini cap", "Q": 12.5}),
 ("IA-07 zero micro cap", S("IA07", instrument="MES", max_minis="NONE", max_micros=0, risk=200, ticks=12), [],
     {"AA": "OK", "AK": 0, "AL": True, "Q": 1.25, "AQ": 0}),
 ("IA-08 NONE still daily-loss", S("IA08", instrument="MES", max_minis="NONE", max_micros="NONE", risk=10000, ticks=12, dll=1000, day_ref=49800, equity=49000), [],
     {"AA": "OK", "AI": "daily_loss", "AH": 200, "AK": 13, "AL": False, "AM": True}),
 ("IA-09 invalid instrument", S("IA09", instrument="ZZ"), [], {"AA": "INVALID", "AK": "INVALID", "Q": "INVALID"}),
 ("IA-09b sheet rejects GC", S("IA09b", instrument="GC"), [], {"AA": "INVALID", "Q": "INVALID"}),
 ("IA-10 blank instrument", {**S("IA10"), "L": None}, [],
     {"AA": "INCOMPLETE", "AK": "INCOMPLETE", "AR": "contains:INSTRUMENT MISSING"}),
 ("IA-BREACH size blocked", S("IAB", instrument="ES", max_minis=5, max_micros="NONE", equity=48000, risk=200, ticks=12), [],
     {"AA": "OK", "AE": True, "AF": "BREACHED", "AK": "BREACHED", "AH": "BREACHED", "Q": 12.5}),
 ("IA-TRAIL floor still moves", S("IAT", type="eod_trailing", lock=0, instrument="NQ", max_minis="NONE", max_micros="NONE", equity=51000),
     [{"A": "IAT", "B": datetime.date(2026, 10, 1), "C": 54000}],
     {"AA": "OK", "AC": 50000, "AD": True, "AK": 3, "Q": 5}),
 # Daily capacity. Static floor is 48000, so 48950 and 49000 are not floor breaches.
 # $0.01 left cannot buy one MES tick ($1.25), so the contract count is numeric 0 and the status stays OK.
 ("DL-01 $0.01 room left", S("DL01", equity=49000.01, dll=1000, day_ref=50000, risk=200, ticks=12), [],
     {"AA": "OK", "AE": False, "AG": 0.01, "AF": 1000.01, "AH": 0.01, "AI": "daily_loss", "AK": 0, "AJ": 0.01, "AU": None}),
 ("DL-02 exact zero", S("DL02", equity=49000, dll=1000, day_ref=50000, risk=200, ticks=12), [],
     {"AA": "OK", "AE": False, "AG": 0, "AF": 1000, "AH": 0, "AI": "daily_loss", "AK": "DAILY LIMIT REACHED",
      "AU": "DAILY LIMIT REACHED", "AJ": "DAILY LIMIT REACHED", "AQ": "DAILY LIMIT REACHED", "AP": 0}),
 ("DL-03 beyond unstated", S("DL03", equity=48950, dll=1000, day_ref=50000, risk=200, ticks=12), [],
     {"AA": "OK", "AE": False, "AG": -50, "AF": 950, "AH": 0, "AI": "daily_loss", "AK": "DAILY LIMIT EXCEEDED",
      "AU": "DAILY LIMIT EXCEEDED", "AJ": "DAILY LIMIT EXCEEDED"}),
 ("DL-04 beyond hard", S("DL04", equity=48950, dll=1000, day_ref=50000, risk=200, ticks=12, dll_enforcement="hard"), [],
     {"AA": "OK", "AE": True, "AG": -50, "AF": 950, "AH": 0, "AI": "daily_loss", "AK": "BREACHED", "AU": "BREACHED", "AP": 0}),
 ("DL-05 one cent beyond", S("DL05", equity=48999.99, dll=1000, day_ref=50000, risk=200, ticks=12), [],
     {"AA": "OK", "AE": False, "AG": -0.01, "AF": 999.99, "AK": "DAILY LIMIT EXCEEDED", "AU": "DAILY LIMIT EXCEEDED"}),
 ("DL-06 one cent beyond hard", S("DL06", equity=48999.99, dll=1000, day_ref=50000, risk=200, ticks=12, dll_enforcement="hard"), [],
     {"AA": "OK", "AE": True, "AG": -0.01, "AF": 999.99, "AK": "BREACHED", "AU": "BREACHED"}),
 ("DL-07 explicit soft", S("DL07", equity=48950, dll=1000, day_ref=50000, risk=200, ticks=12, dll_enforcement="soft"), [],
     {"AA": "OK", "AE": False, "AG": -50, "AK": "DAILY LIMIT EXCEEDED", "AU": "DAILY LIMIT EXCEEDED"}),
 ("DL-08 hard still open", S("DL08", equity=49000, dll=1000, day_ref=49800, risk=10000, ticks=12, max_minis="NONE", max_micros="NONE", dll_enforcement="hard"), [],
     {"AA": "OK", "AE": False, "AG": 200, "AI": "daily_loss", "AH": 200, "AK": 13, "AU": None}),
 ("DL-09 floor outranks daily", S("DL09", equity=48000, dll=1000, day_ref=50000, risk=200, ticks=12, dll_enforcement="soft"), [],
     {"AA": "OK", "AE": True, "AF": "BREACHED", "AG": "BREACHED", "AK": "BREACHED", "AU": "BREACHED", "AI": "BREACHED"}),
 ("DL-10 preset soft", {"A": "DL10", "B": "Topstep | Trading Combine | 50000 [P001]", "I": 1000, "L": "MES", "M": 48950, "N": 50000, "O": 200, "P": 12}, [],
     {"AA": "OK", "AE": False, "AG": -50, "AK": "DAILY LIMIT EXCEEDED", "AU": "DAILY LIMIT EXCEEDED"}),
 ("DL-11 hard overrides soft preset", {"A": "DL11", "B": "Topstep | Trading Combine | 50000 [P001]", "I": 1000, "AS": "hard", "L": "MES", "M": 48950, "N": 50000, "O": 200, "P": 12}, [],
     {"AA": "OK", "AE": True, "AG": -50, "AF": 950, "AK": "BREACHED", "AU": "BREACHED", "AR": "contains:OVERRIDES PRESET"}),
 ("DL-12 HARD token", S("DL12", equity=48950, dll=1000, day_ref=50000, risk=200, ticks=12, dll_enforcement="HARD"), [],
     {"AA": "OK", "AE": True, "AK": "BREACHED", "AG": -50}),
 ("DL-13 bad enforcement", S("DL13", dll_enforcement="nope", dll=1000, day_ref=50000), [],
     {"AA": "INVALID", "AK": "INVALID"}),
]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def fill_template(src, dest, accounts, logs, demo_asof):
    """Copy the release workbook and write scenario inputs only. Formulas stay the ones in src."""
    shutil.copyfile(src, dest)
    wb = load_workbook(dest)
    ws = wb["Accounts"]
    tick = ws["Q2"].value
    if not isinstance(tick, str) or "Contracts!$K$2:$K$5" not in tick:
        raise SystemExit("template Q2 is not the instrument tick lookup: " + repr(tick))
    for i, a in enumerate(accounts, 2):
        for col, val in a.items():
            ws[f"{col}{i}"] = val
    if demo_asof:
        ws["B13"] = demo_asof
    log = wb["Daily Log"]
    for i, row in enumerate(logs, 2):
        for col, val in row.items():
            log[f"{col}{i}"] = val
    for r in range(2, 12):
        ws[f"AT{r}"] = f'=IF(M{r}="","",INT(ROUND(M{r}*100,6))/100)'
    if "Contracts!$K$2:$K$5" not in str(ws["Q2"].value):
        raise SystemExit("filling the template rewrote the tick formula")
    wb.save(dest)

def run_batches(items, template=None):
    """items: (name, account|[accounts], logs, expect[, opts]). opts: solo=True (own workbook, e.g. orphan rows poison
    every account), asof=date (Accounts!B13). Getter keys: column letter (first account), 'acc2:COL', 'log:I' (last log
    row of this account), 'logid:<ID>' (log status of rows with that ID), or an absolute cell like 'B14'.

    template: path of the release xlsx. Each batch is a copy of that file. None builds with build()."""
    tmp = tempfile.mkdtemp(); files = []
    plain = [it for it in items if not (it[4] if len(it) > 4 else {})]
    groups, cur, n = [], [], 0
    for it in plain:
        k = len(it[1]) if isinstance(it[1], list) else 1
        if n + k > 10: groups.append(cur); cur, n = [], 0
        cur.append(it); n += k
    if cur: groups.append(cur)
    groups += [[it] for it in items if (it[4] if len(it) > 4 else {})]
    for gi, chunk in enumerate(groups):
        accs, logs = [], []
        for it in chunk:
            accs.extend(it[1] if isinstance(it[1], list) else [it[1]]); logs.extend(it[2])
        assert len(accs) <= 10
        opts = chunk[0][4] if len(chunk) == 1 and len(chunk[0]) > 4 else {}
        p = os.path.join(tmp, f"b{gi:02d}.xlsx")
        clean = [{k: v for k, v in a.items() if v is not None} for a in accs]
        if template:
            fill_template(template, p, clean, logs, opts.get("asof"))
        else:
            bt.build(p, clean, logs, demo_asof=opts.get("asof"))
            wb = load_workbook(p); ws = wb["Accounts"]          # test-only probe: oracle 'equity' = CENT_DOWN(K)
            for r in range(2, 12): ws[f"AT{r}"] = f"=IF(M{r}=\"\",\"\",INT(ROUND(M{r}*100,6))/100)"
            wb.save(p)
        files.append((p, chunk))
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
            if log[f"A{r}"].value or log[f"C{r}"].value is not None or log[f"E{r}"].value is not None:
                logstat.setdefault(log[f"A{r}"].value, []).append(log[f"I{r}"].value)
        for it in chunk:
            accl = it[1] if isinstance(it[1], list) else [it[1]]
            def get(c, accl=accl, acc=acc, logstat=logstat, ids=ids):
                aid = accl[0]["A"]
                if c == "log:I": return logstat.get(aid, [None])[-1]
                if c.startswith("logid:"): return logstat.get(None if c[6:] == "None" else c[6:], [None])[-1]
                if c.startswith("acc2:"): return acc[f"{c[5:]}{ids[accl[1]['A']]}"].value
                if c[-1].isdigit(): return acc[c].value
                return acc[f"{c}{ids[aid]}"].value
            res[it[0]] = get
    shutil.rmtree(tmp) if os.environ.get("KEEP") is None else print("kept", tmp)
    return res

SUBCENT = {"DD-17"}

def num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)

def golden_ok(f, got, e, breached):
    """M-3: exact. Breached rooms must be the literal 'BREACHED'; money must be exact cents (no tolerance)."""
    if f == "contracts": return num(got) and got == e
    if f == "daily_room" and e is None: return got == "NONE"
    if breached and f == "drawdown_room": return got == "BREACHED"
    if isinstance(e, bool): return got is e
    if isinstance(e, str) and e not in ("drawdown", "daily_loss"):
        return num(got) and round(got, 2) == got and f"{got:.2f}" == e
    return got == e

def status_ok(got, e):
    if isinstance(e, str) and e.startswith("contains:"): return isinstance(got, str) and e[9:] in got
    if isinstance(e, str) and e.startswith("lacks:"): return got is None or (isinstance(got, str) and e[6:] not in got)
    if e == "nonempty": return isinstance(got, str) and got != ""
    if isinstance(e, bool): return got is e
    if num(e): return num(got) and round(got, 2) == got and got == e
    return got == e

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    template = expect = None
    if "--workbook" in argv:
        template = os.path.abspath(argv[argv.index("--workbook") + 1])
        if not os.path.isfile(template):
            raise SystemExit("workbook not found: " + template)
    if "--expect-sha" in argv:
        expect = argv[argv.index("--expect-sha") + 1].lower()
    before = sha256_file(template) if template else None
    if template:
        print(f"WORKBOOK {template}")
        print(f"WORKBOOK_SHA256 {before}")
        if expect and before != expect:
            print(f"WORKBOOK_SHA256_EXPECT {expect}")
            print("HASH_MATCH no")
            sys.exit(1)
    items = GOLDEN + STATUS
    res = run_batches(items, template=template)
    if template:
        after = sha256_file(template)
        print(f"WORKBOOK_SHA256_AFTER {after}")
        print(f"HASH_MATCH {'yes' if after == before else 'no'}")
        if after != before:
            print("FAIL template bytes changed during the test")
            sys.exit(1)
    passed = failed = 0; notes = []; counts = {}
    print(f"{'case':30} {'map':8} result")
    for cid, _, _, fields in GOLDEN:
        get = res[cid]; exp = GOLD[cid]["expected"]; bad = {}
        if cid in SUBCENT:   # FORMULAS §1: sub-cent money inputs are rejected -> every output INVALID (golden_map: partial)
            bad = {f: get(COL[f]) for f in fields if f != "equity" and get(COL[f]) != "INVALID"}
            passed += not bad; failed += bool(bad)
            counts["golden"] = [counts.get("golden", [0, 0])[0] + (not bad), counts.get("golden", [0, 0])[1] + 1]
            print(f"{cid:30} {'partial':8} {'PASS' if not bad else 'FAIL ' + str(bad)}  (sub-cent input -> INVALID as specified, not oracle values)")
            continue
        for f in fields:
            got = get(COL[f]); e = exp[f]
            if f == "drawdown_room" and exp.get("breached"): notes.append(cid)
            if not golden_ok(f, got, e, exp.get("breached") is True): bad[f] = (got, e)
        status = "PASS" if not bad else f"FAIL {bad}"
        passed += not bad; failed += bool(bad)
        counts["golden"] = [counts.get("golden", [0, 0])[0] + (not bad), counts.get("golden", [0, 0])[1] + 1]
        print(f"{cid:30} {GMAP[cid]['reproducible']:8} {status}  ({len(fields)} fields)")
    for it in STATUS:
        cid, want = it[0], it[3]
        get = res[cid]; bad = {}
        for c, e in want.items():
            got = get(c)
            if not status_ok(got, e): bad[c] = (got, e)
        passed += not bad; failed += bool(bad)
        grp = "repro" if cid.startswith(("P1", "P2", "P9")) else "fix" if cid[:3] in ("L-1", "L-2", "L-3", "M-4", "H-1", "H-2", "M-1") else "status"
        counts[grp] = [counts.get(grp, [0, 0])[0] + (not bad), counts.get(grp, [0, 0])[1] + 1]
        print(f"{cid:30} {grp:8} {'PASS' if not bad else 'FAIL ' + str(bad)}  ({len(want)} cells)")
    print(f"\nGOLDEN yes/partial on sheet: {sum(1 for c in GOLDEN)} cases; STATUS scenarios: {len(STATUS)}")
    print("RECLASSIFIED legacy single-cap, not sheet-enterable (arbitrary tick; Python sheet_logic still checks the invariant):",
          ", ".join(SKIPPED) or "none")
    for g, (a, n) in counts.items(): print(f"GROUP {g:7} {a} / {n}")
    print(f"TOTAL PASS {passed} / {passed + failed}")
    if notes: print("note: breached cases require literal 'BREACHED' in drawdown_room (oracle 0.00):", ", ".join(notes))
    if template:
        print(f"TESTED_FILE_SHA256 {before}")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
