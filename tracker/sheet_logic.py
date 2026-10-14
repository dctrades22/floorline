#!/usr/bin/env python3
"""Float (IEEE double, like Excel/Sheets) re-implementation of the tracker cell formulas in tracker/FORMULAS.md.
Builds tracker/golden_map.json and, for every case marked reproducible yes/partial with sheet_inputs, evaluates the
formula logic and compares the listed fields to golden/cases.json.   python3 tracker/sheet_logic.py [--check]"""
import json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = {c["id"]: c for c in json.load(open(os.path.join(ROOT, "golden", "cases.json")))["cases"]}
OUT = os.path.join(ROOT, "tracker", "golden_map.json")

# --- formula primitives (exactly as specified in FORMULAS.md section 3) ---
def ROUND(x, n): return round_half_away(x, n)
def round_half_away(x, n):            # Excel/Sheets ROUND: half away from zero
    m = 10 ** n; return math.copysign(math.floor(abs(x) * m + 0.5), x) / m
def INT(x): return math.floor(x)
def CENT_UP(x): return -INT(ROUND(-x * 100, 6)) / 100      # floor display (ceiling to cents)
def CENT_DOWN(x): return INT(ROUND(x * 100, 6)) / 100      # rooms/risk (x >= 0)
def HIT(v, floor, touch): d = ROUND(v - floor, 6); return d <= 0 if touch else d < 0

def floor_raw(t, S, DD, lock, peak):
    if t == "static": return S - DD
    return peak - DD if lock == "NONE" else min(peak - DD, S + lock)

def account(a):
    t, S, DD, lock, touch, rows, K = a["type"], a["start"], a["dd"], a.get("lock", "NONE"), a.get("touch", True), a.get("log", []), a["equity"]
    breached = False
    for i, r in enumerate(rows):                 # Daily Log columns G..I
        prior = [x["eod"] for x in rows[:i]]
        if t == "static": pk = S
        elif t == "eod_trailing": pk = max([S] + prior)
        else: pk = max([S] + prior + [r["eod"]] + [x.get("high", 0) for x in rows[:i + 1]])
        f = floor_raw(t, S, DD, lock, pk)
        chk = [r["eod"]] + ([r["low"]] if "low" in r else [])
        if HIT(min(chk), f, touch): breached = True
    if t == "static": peak = S
    elif t == "eod_trailing": peak = max([S] + [x["eod"] for x in rows])
    else: peak = max([S, K] + [x["eod"] for x in rows] + [x.get("high", 0) for x in rows])
    f = floor_raw(t, S, DD, lock, peak)
    locked = t != "static" and lock != "NONE" and ROUND(peak - DD - (S + lock), 6) >= 0
    breached = breached or HIT(K, f, touch)
    room = 0.0 if breached else CENT_DOWN(max(0.0, K - f))
    return {"floor": CENT_UP(f), "peak": ROUND(peak, 2), "locked": locked, "breached": breached,
            "equity": CENT_DOWN(K), "drawdown_room": room}

def risk(a, dd_room):
    if a.get("dll", "NONE") == "NONE": return {"binding_room": dd_room, "daily_room": None, "drawdown_room": dd_room, "binding": "drawdown"}
    dr = CENT_DOWN(max(0.0, a["dll"] - max(0.0, -(a["equity"] - a["day_ref"]))))
    return {"binding_room": min(dd_room, dr), "daily_room": dr, "drawdown_room": dd_room,
            "binding": "daily_loss" if dr < dd_room else "drawdown"}

def size(a, binding):
    m = a.get("maxc", "NONE"); eff = min(a["risk"], binding)
    raw = INT(ROUND(eff / (a["ticks"] * a["tv"]), 9))
    n = raw if m == "NONE" else min(raw, m)
    return {"contracts": n, "capped": m != "NONE" and raw > m, "effective_risk": CENT_DOWN(eff),
            "risk_limited_by_room": a["risk"] > binding, "actual_risk": CENT_DOWN(n * a["ticks"] * a["tv"])}

def run(si):
    acc = account(si); out = dict(acc)
    rr = risk(si, acc["drawdown_room"]); out.update(rr)
    if "risk" in si: out.update(size(si, rr["binding_room"]))
    return out

def norm(v):
    if isinstance(v, bool) or v is None or isinstance(v, int): return v
    if isinstance(v, float): return f"{v:.2f}"
    return v

# --- map definitions ---
def ST(S, DD, eq, **kw): return {"type": "static", "start": S, "dd": DD, "equity": eq, **kw}
DDF = ["floor", "peak", "locked", "breached", "equity", "drawdown_room"]
RRF = ["drawdown_room", "daily_room", "binding_room", "binding"]
FSF = ["contracts", "capped", "effective_risk", "risk_limited_by_room", "actual_risk"]
L = lambda eod, **k: {"eod": eod, **k}
Y, P, N = "yes", "partial", "no"
M = {
 "DD-01": (Y, "Accounts static S=50000 DD=2000; Daily Log 1 row EOD 49100 high 50800 low 49100; current equity 49100", ST(50000, 2000, 49100, log=[L(49100, high=50800, low=49100)]), DDF, None),
 "DD-02": (Y, "static; Daily Log EOD 49500 low 48000 -> touch breach; current equity 48000", ST(50000, 2000, 48000, log=[L(49500, high=49500, low=48000)]), DDF, "oracle equity is the breaching mark; user enters the breaching equity 48000 as current equity"),
 "DD-03": (Y, "eod_trailing no lock (NONE); day1 high 51500 EOD 50600; day2 EOD 50300; current equity 49000", {"type": "eod_trailing", "start": 50000, "dd": 2000, "equity": 49000, "log": [L(50600, high=51500), L(50300)]}, DDF, None),
 "DD-04": (Y, "eod_trailing lock 0; EOD 51000/52500/54000; equity 51000", {"type": "eod_trailing", "start": 50000, "dd": 2000, "lock": 0, "equity": 51000, "log": [L(51000), L(52500), L(54000)]}, DDF, None),
 "DD-05": (Y, "eod_trailing lock 100; EOD 51000/53000; equity 50150.25", {"type": "eod_trailing", "start": 50000, "dd": 2000, "lock": 100, "equity": 50150.25, "log": [L(51000), L(53000)]}, DDF, None),
 "DD-06": (Y, "eod_trailing lock 100; EOD 52100/51000; equity 51000 (lock exactly hit)", {"type": "eod_trailing", "start": 50000, "dd": 2000, "lock": 100, "equity": 51000, "log": [L(52100), L(51000)]}, DDF, None),
 "DD-07": (Y, "eod_trailing lock 0; day1 EOD 51000; day2 low 48999.99 EOD 50500; equity 48999.99", {"type": "eod_trailing", "start": 50000, "dd": 2000, "lock": 0, "equity": 48999.99, "log": [L(51000), L(50500, low=48999.99)]}, DDF, "oracle stops at the breaching mark; user enters breaching equity as current equity; day2 EOD 50500 does not raise peak above 51000"),
 "DD-08": (Y, "intraday_trailing; 1 row high 50750.50 low 49100 EOD 49100; equity 49100", {"type": "intraday_trailing", "start": 50000, "dd": 2000, "equity": 49100, "log": [L(49100, high=50750.50, low=49100)]}, DDF, "matches because oracle order is high-then-low, which is the sheet's conservative assumption"),
 "DD-09": (Y, "intraday_trailing lock 0; high 26400 low 25300; equity 25300", {"type": "intraday_trailing", "start": 25000, "dd": 1000, "lock": 0, "equity": 25300, "log": [L(25300, high=26400, low=25300)]}, DDF, None),
 "DD-10": (Y, "intraday_trailing lock 100; high 52600 low 50200; equity 50200", {"type": "intraday_trailing", "start": 50000, "dd": 2000, "lock": 100, "equity": 50200, "log": [L(50200, high=52600, low=50200)]}, DDF, None),
 "DD-11": (P, "intraday_trailing; high 51500 low 49000", {"type": "intraday_trailing", "start": 50000, "dd": 2000, "equity": 49000, "log": [L(51500, high=51500, low=49000)]}, ["breached", "drawdown_room", "locked"], "event-order dependence: oracle sees 51000 -> 49000 (breach) -> 51500 (ignored); one daily row cannot encode order, so sheet peak 51500/floor 49500 differ from oracle 51000/49000. Breach and room match (conservatively)."),
 "DD-12": (Y, "static touch FALSE; low 24000; equity 24000", ST(25000, 1000, 24000, touch=False, log=[L(24000, low=24000)]), DDF, None),
 "DD-13": (Y, "static touch FALSE; low 23999.99; equity 23999.99", ST(25000, 1000, 23999.99, touch=False, log=[L(23999.99, low=23999.99)]), DDF, None),
 "DD-14": (Y, "eod_trailing lock 100; EOD 52099.99; equity 52099.99", {"type": "eod_trailing", "start": 50000, "dd": 2000, "lock": 100, "equity": 52099.99, "log": [L(52099.99)]}, DDF, None),
 "DD-15": (Y, "eod_trailing lock -500; EOD 51000/52000; equity 52000", {"type": "eod_trailing", "start": 50000, "dd": 2000, "lock": -500, "equity": 52000, "log": [L(51000), L(52000)]}, DDF, None),
 "DD-16": (Y, "intraday_trailing; EOD 53000; equity 53000", {"type": "intraday_trailing", "start": 50000, "dd": 2000, "equity": 53000, "log": [L(53000)]}, DDF, None),
 "DD-17": (P, "intraday_trailing; high 50000.004 low 48000.009; equity 48000.009", {"type": "intraday_trailing", "start": 50000, "dd": 2000, "equity": 48000.009, "log": [L(48000.009, high=50000.004, low=48000.009)]}, DDF, "sub-cent inputs: matches here via ROUND(...,6) tolerance, but money inputs are validated to 2 dp (sub-cent entry -> INVALID), so the case is not enterable as-is; float cannot guarantee Decimal parity for arbitrary sub-cent values"),
 "RR-18": (Y, "equivalent inputs: static S=50000 DD=2000 equity 49800 (dd room 1800); DLL 1000; day reference 50450 (day_pnl -650)", ST(50000, 2000, 49800, dll=1000, day_ref=50450), RRF, "drawdown_room is not a direct input; constructed account yields the same room"),
 "RR-19": (Y, "equivalent: static S=50000 DD=2000 equity 48400 (room 400); DLL 1000; day reference 48150 (+250)", ST(50000, 2000, 48400, dll=1000, day_ref=48150), RRF, "constructed equivalent inputs"),
 "RR-20": (Y, "equivalent: static S=50000 DD=2000 equity 49234.56; DLL NONE", ST(50000, 2000, 49234.56), RRF, "constructed equivalent inputs"),
 "RR-21": (Y, "equivalent: static S=50000 DD=2000 equity 48500 (room 500); DLL 1000; day reference 49000 (-500)", ST(50000, 2000, 48500, dll=1000, day_ref=49000), RRF, "constructed equivalent inputs"),
}
def fs(cid, room, risk, ticks, tv, maxc="NONE", extra=None):
    eq = 48000 + room
    M[cid] = (Y, f"equivalent: static S=50000 DD=2000 equity {eq} (binding room {room}); risk {risk}, stop ticks {ticks}, tick value {tv}, max contracts {maxc}",
              ST(50000, 2000, eq, risk=risk, ticks=ticks, tv=tv, maxc=maxc), FSF, extra or "binding_room supplied via constructed account room")
fs("FS-22", 1000, 300, 16, 1.25, 50); fs("FS-23", 1000, 200, 20, 12.50, 5); fs("FS-24", 2000, 1000, 40, 0.50, 30)
fs("FS-25", 350, 999999, 1, 1); fs("FS-26", 500, 500, 4, 1.25, 0); fs("FS-27", 500, 0, 4, 1.25)
fs("FS-28", 10, 0.996, 1, 0.995, extra="risk 0.996 is sub-cent: money validation would reject it; logic matches when allowed. effective_risk shown 0.99")
M["FS-28"] = (P,) + M["FS-28"][1:]
for c in ["CS-29", "CS-30", "CS-31", "CS-32", "CS-33", "CS-34", "IV-35", "IV-37", "IV-45"]:
    M[c] = (N, "n/a", None, None, "crypto perp sizing (qty, step_size rounding, side) is out of tracker scope (futures-only product)")
TXT = {
 "IV-36": "Stop ticks = 0 -> Accounts AF/AG show 'INVALID' (validation: integer >= 1)",
 "IV-38": "binding room is always derived; a missing required input (equity/risk) -> 'INCOMPLETE'",
 "IV-39": "Lock offset -2500 with DD 2000 -> 'INVALID' (S+lock must be > S-DD)",
 "IV-40": "static + numeric lock -> 'INVALID' (static requires NONE)",
 "IV-41": "type restricted by dropdown; any other text -> 'INVALID'",
 "IV-43": "DLL set but Day Reference blank -> 'INCOMPLETE'",
 "IV-44": "type blank with Manual preset -> 'INCOMPLETE'",
 "IV-46": "max contracts 2.9 -> 'INVALID' (integer >= 0 or NONE)",
 "IV-47": "stop ticks 0.5 -> 'INVALID' (integer >= 1)",
 "IV-48": "breach_on_touch dropdown TRUE/FALSE; text 'false' -> 'INVALID'",
}
for c, how in TXT.items():
    M[c] = (P, how, None, None, "sheet shows text status (INVALID/INCOMPLETE), not the oracle's error code/message; equivalence is categorical only (INVALID_INPUT/INVALID_RULE_CONFIGURATION -> INVALID, missing -> INCOMPLETE)")
M["IV-42"] = (N, "n/a", None, None, "no event stream in the sheet (daily rows have fixed columns); 'event without kind' has no analogue")
M["IV-49"] = (N, "n/a", None, None, "no event stream; an invalid Daily Log row after a breach shows INVALID on that row but the account BREACHED status is still derived from valid rows (not whole-call rejection)")

def build():
    errs, cases = [], []
    for cid in GOLD:
        r, how, si, fields, reason = M[cid]
        ent = {"id": cid, "reproducible": r, "how": how, "reason": reason}
        if si is not None:
            got, exp = run(si), GOLD[cid]["expected"]
            mism = {f: [norm(got[f]), exp[f]] for f in fields if norm(got[f]) != exp[f]}
            ent["checked_fields"] = fields; ent["sheet_logic_match"] = not mism
            if mism: errs.append((cid, mism)); ent["mismatch"] = mism
        cases.append(ent)
    assert len(cases) == 49 and set(M) == set(GOLD)
    return {"spec": "tracker v0.1.0 / oracle 0.2.0", "generated_by": "tracker/sheet_logic.py",
            "counts": {k: sum(c["reproducible"] == k for c in cases) for k in (Y, P, N)}, "cases": cases}, errs

# --- status model (FORMULAS.md v0.1.1 §3.1, §3.3) and scenario checks for SPECTER-TRACKER-REVIEW fixes ---
MAXM = 100000000
def num(x): return isinstance(x, (int, float)) and not isinstance(x, bool)
def cents_ok(x): return ROUND(x * 100, 6) == INT(ROUND(x * 100, 6))
def money_ok(x): return num(x) and 0 < x <= MAXM and cents_ok(x)
def eq_ci(a, b): return isinstance(a, str) and isinstance(b, str) and a.lower() == b.lower()   # Excel/Sheets "=" and MATCH

def log_row_status(r, ids):
    vals = [r.get(k, "") for k in ("acct", "date", "eod", "high", "low")]
    if all(v == "" for v in vals): return ""
    if r.get("acct", "") == "" or not any(eq_ci(r["acct"], i) for i in ids): return "UNKNOWN_ACCOUNT"
    if r.get("date", "") == "" or r.get("eod", "") == "": return "INCOMPLETE"
    for k in ("eod", "high", "low"):
        if r.get(k, "") != "" and not money_ok(r[k]): return "INVALID"
    return "OK"   # (breach evaluation is account()'s job; BREACHED is a sub-state of a valid row)

def tick_ok(tv): return num(tv) and 0 < tv <= 100000 and ROUND(tv * 1e6, 3) == INT(ROUND(tv * 1e6, 3))

def w_status(a, accts, log):
    """a: dict with effective fields P..V, K, L (strings for tokens)."""
    if a.get("id", "") == "" and a.get("preset", "") == "": return ""
    req = [a.get(k, "") for k in ("id", "preset", "type", "start", "dd", "lock", "touch", "dll", "maxc", "equity")]
    if any(v == "" for v in req) or (not eq_ci(a["dll"], "NONE") and a.get("day_ref", "") == ""): return "INCOMPLETE"
    lock_none = eq_ci(a["lock"], "NONE"); maxc_none = eq_ci(a["maxc"], "NONE"); dll_none = eq_ci(a["dll"], "NONE")
    inval = (sum(eq_ci(a["id"], b["id"]) for b in accts) > 1
             or not any(eq_ci(a["type"], t) for t in ("static", "eod_trailing", "intraday_trailing"))
             or not money_ok(a["start"]) or not money_ok(a["dd"])
             or (not lock_none and not num(a["lock"]))
             or (eq_ci(a["type"], "static") and not lock_none)
             or (num(a["lock"]) and ROUND(a["start"] + a["lock"] - (a["start"] - a["dd"]), 6) <= 0)     # guard 1
             or (num(a["lock"]) and abs(a["lock"]) > MAXM)
             or a["touch"] not in (True, False)
             or (not dll_none and not money_ok(a["dll"]))
             or (False if maxc_none else (a["maxc"] < 0 or a["maxc"] != INT(a["maxc"]) if num(a["maxc"]) else True))  # guard 2
             or not money_ok(a["equity"])
             or (not dll_none and not money_ok(a["day_ref"])))
    if inval: return "INVALID"
    ids = [b["id"] for b in accts]
    st = [log_row_status(r, ids) for r in log]
    mine = [x for r, x in zip(log, st) if r.get("acct", "") != "" and eq_ci(r["acct"], a["id"])]
    if "INVALID" in mine: return "INVALID"
    if "INCOMPLETE" in mine or "UNKNOWN_ACCOUNT" in st: return "INCOMPLETE"
    return "OK"

def locked_z(a, peak):   # guard 3: no arithmetic on NONE
    return num(a["lock"]) and not eq_ci(a["type"], "static") and ROUND(peak - a["dd"] - (a["start"] + (a["lock"] if num(a["lock"]) else 0)), 6) >= 0

def scenarios():
    base = dict(id="P1", preset="Manual", type="static", start=50000, dd=2000, lock="NONE", touch=True, dll="NONE", maxc="NONE", equity=49000, day_ref="")
    A = lambda **k: {**base, **k}
    other = A(id="P2")
    T = []
    def t(name, got, exp): T.append((name, got, exp))
    # H-1: incomplete log row (low entered, close blank) -> account INCOMPLETE
    t("H-1 log INCOMPLETE propagates", w_status(A(), [A()], [{"acct": "P1", "date": "2026-10-13", "low": 47000}]), "INCOMPLETE")
    # H-2: orphan row -> UNKNOWN_ACCOUNT on row, every account INCOMPLETE; blank-ID row with data also orphan
    log2 = [{"acct": "P2x", "date": "2026-10-13", "eod": 49000, "low": 47000}]
    t("H-2 orphan row status", log_row_status(log2[0], ["P1", "P2"]), "UNKNOWN_ACCOUNT")
    t("H-2 orphan -> P1 INCOMPLETE", w_status(A(), [A(), other], log2), "INCOMPLETE")
    t("H-2 orphan -> P2 INCOMPLETE", w_status(other, [A(), other], log2), "INCOMPLETE")
    t("H-2 blank ID with data", log_row_status({"acct": "", "eod": 49000}, ["P1"]), "UNKNOWN_ACCOUNT")
    t("H-2 empty row ignored", log_row_status({}, ["P1"]), "")
    # M-1: blank cap -> INCOMPLETE; explicit NONE -> OK; numeric cap OK
    t("M-1 blank cap", w_status(A(maxc=""), [A()], []), "INCOMPLETE")
    t("M-1 NONE cap", w_status(A(maxc="NONE"), [A()], []), "OK")
    t("M-1 numeric cap", w_status(A(maxc=5), [A()], []), "OK")
    t("M-1 fractional cap", w_status(A(maxc=2.5), [A()], []), "INVALID")
    # BUILDER guards: NONE lock does not error; lock below floor INVALID; Locked FALSE on NONE
    t("guard1 NONE lock eod ok", w_status(A(type="eod_trailing"), [A()], []), "OK")
    t("guard1 lock below floor", w_status(A(type="eod_trailing", lock=-2500), [A()], []), "INVALID")
    t("guard2 text cap", w_status(A(maxc="five"), [A()], []), "INVALID")
    t("guard3 Locked on NONE", locked_z(A(type="eod_trailing"), 60000), False)
    t("guard3 Locked numeric", locked_z(A(type="eod_trailing", lock=0), 52000), True)
    # L-1: fractional tick values
    t("L-1 tick 15.625", tick_ok(15.625), True)
    t("L-1 tick 3.125", tick_ok(3.125), True)
    t("L-1 tick 0.995", tick_ok(0.995), True)
    t("L-1 tick 7 dp", tick_ok(0.0000001), False)
    t("L-1 sizing ZN", size({"risk": 500, "ticks": 8, "tv": 15.625, "maxc": "NONE"}, 1000)["contracts"], 4)
    # L-2: equity bound
    t("L-2 equity 1e15", w_status(A(equity=1e15), [A()], []), "INVALID")
    t("L-2 equity 0", w_status(A(equity=0), [A()], []), "INVALID")
    t("L-2 equity 1e8", w_status(A(equity=100000000), [A()], []), "OK")
    t("L-2 log close 1e9", w_status(A(), [A()], [{"acct": "P1", "date": "d", "eod": 1e9}]), "INVALID")
    # L-3: case-insensitive
    t("L-3 dup IDs ignoring case", w_status(A(id="p16"), [A(id="p16"), A(id="P16")], []), "INVALID")
    t("L-3 log p16 matches P16", log_row_status({"acct": "p16", "date": "d", "eod": 49000}, ["P16"]), "OK")
    t("L-3 none == NONE", w_status(A(lock="none", maxc="None"), [A()], []), "OK")
    t("L-3 trailing space invalid", w_status(A(type="Static "), [A()], []), "INVALID")
    return T

def run_scenarios():
    bad = [(n, g, e) for n, g, e in scenarios() if g != e]
    for b in bad: print("SCENARIO FAIL", b)
    print("SCENARIOS", "FAIL" if bad else "PASS", len(scenarios()))
    return not bad

if __name__ == "__main__":
    doc, errs = build()
    t = json.dumps(doc, indent=2) + "\n"
    for e in errs: print("MISMATCH", e)
    if "--check" in sys.argv:
        ok = open(OUT).read() == t and not errs and run_scenarios(); print("GOLDEN_MAP", "PASS" if ok else "FAIL", doc["counts"]); sys.exit(0 if ok else 1)
    open(OUT, "w").write(t); print("wrote", OUT, doc["counts"]); sys.exit(1 if errs or not run_scenarios() else 0)
