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

def signed_daily(a):
    """CENT_DOWN is floor (toward -inf), so a fraction of a cent below zero stays negative."""
    return CENT_DOWN(a["dll"] - max(0.0, -(a["equity"] - a["day_ref"])))

def dll_rule_of(enf):
    s = enf.strip().lower() if isinstance(enf, str) else ""
    return s if s in ("hard", "soft") else "unconfirmed"

def daily_word(capacity, enf):
    if capacity > 0: return "OK"
    if capacity == 0: return "DAILY LIMIT REACHED"
    rule = dll_rule_of(enf)
    if rule == "hard": return "BREACHED"
    if rule == "soft": return "DAILY LIMIT EXCEEDED"
    return "RULE CONFIRMATION REQUIRED"

def risk(a, dd_room):
    if a.get("dll", "NONE") == "NONE":
        return {"binding_room": dd_room, "daily_room": None, "drawdown_room": dd_room,
                "binding": "drawdown", "daily_status": None, "dll_rule": None}
    dr = signed_daily(a)
    sized = max(0.0, dr)
    rule = dll_rule_of(a.get("dll_enforcement"))
    return {"binding_room": min(dd_room, sized), "daily_room": dr, "drawdown_room": dd_room,
            "binding": "daily_loss" if dr < dd_room else "drawdown",
            "daily_status": daily_word(dr, rule), "dll_rule": rule}

def trade_status(acc, rr):
    """Floor hit outranks every daily status. Daily words block trading. OK is the only tradable word."""
    if acc.get("breached"): return "BREACHED"
    st = rr.get("daily_status")
    if st in ("DAILY LIMIT REACHED", "DAILY LIMIT EXCEEDED", "BREACHED", "RULE CONFIRMATION REQUIRED"): return st
    return "OK"

def breach_cell(acc, rr):
    """AE. TRUE is a confirmed breach. FALSE is not a breach. UNCONFIRMED is not a safe clearance and not soft."""
    if acc.get("breached") or rr.get("daily_status") == "BREACHED": return True
    if rr.get("daily_status") == "RULE CONFIRMATION REQUIRED": return "UNCONFIRMED"
    return False

# NEW instrument table. The workbook dropdown is the first four. The free calculator also
# knows the other symbols; the class rule is the same (mini cap vs micro cap).
TICK = {"ES": 12.5, "MES": 1.25, "NQ": 5.0, "MNQ": 0.5}
MINI_SYMS = {"ES", "NQ"}
MICRO_SYMS = {"MES", "MNQ"}

def norm_inst(s):
    return s.strip().upper() if isinstance(s, str) else ""

def active_cap_of(a):
    inst = norm_inst(a.get("instrument", ""))
    if inst == "": return ""
    if inst in MINI_SYMS: return a.get("max_minis", "")
    if inst in MICRO_SYMS: return a.get("max_micros", "")
    return "INVALID"

def size(a, binding):
    """Inner contract count. OLD: pass tv + maxc. NEW: pass instrument + max_minis + max_micros
    and this resolves the tick and the active cap, then uses the same formula."""
    if a.get("instrument"):
        inst = norm_inst(a["instrument"])
        if inst not in TICK: raise ValueError("invalid instrument " + inst)
        cap = a.get("max_minis") if inst in MINI_SYMS else a.get("max_micros")
        if cap == "" or cap is None: raise ValueError("missing cap")
        m = "NONE" if isinstance(cap, str) and cap.strip().upper() == "NONE" else cap
        a = {**a, "tv": TICK[inst], "maxc": m}
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
def dl_row(cid, equity, day_ref, dll, note, enf=None):
    si = ST(50000, 2000, equity, dll=dll, day_ref=day_ref)
    if enf is not None: si["dll_enforcement"] = enf
    M[cid] = (Y, note, si, RRF, "signed daily capacity; binding_room is max(0, capacity)")
dl_row("DL-01", 49000.01, 50000, 1000, "equity 49000.01, day ref 50000, DLL 1000 → $0.01 left, status OK")
dl_row("DL-02", 49000, 50000, 1000, "equity 49000, day ref 50000, DLL 1000 → capacity 0, DAILY LIMIT REACHED")
dl_row("DL-03", 48950, 50000, 1000, "equity 48950, day ref 50000, DLL 1000 → -50, enforcement unconfirmed, RULE CONFIRMATION REQUIRED")
dl_row("DL-04", 48950, 50000, 1000, "same -50 with hard enforcement → BREACHED", "hard")
dl_row("DL-05", 48999.99, 50000, 1000, "equity 48999.99 → capacity -0.01, RULE CONFIRMATION REQUIRED")
dl_row("DL-06", 48999.99, 50000, 1000, "capacity -0.01 with hard enforcement → BREACHED", "hard")
dl_row("DL-07", 48950, 50000, 1000, "explicit soft → DAILY LIMIT EXCEEDED", "soft")
dl_row("DL-08", 49800, 50450, 1000, "hard enforcement, day loss 650, capacity 350 still OK", "hard")
dl_row("DL-12", 48950, 50000, 1000, "enforcement HARD is hard → BREACHED", "HARD")
dl_row("DL-14", 49000.01, 50000, 1000, "capacity 0.01 with hard stays OK", "hard")
dl_row("DL-15", 49000.01, 50000, 1000, "capacity 0.01 with soft stays OK", "soft")
dl_row("DL-16", 49000, 50000, 1000, "capacity 0 with hard is DAILY LIMIT REACHED", "hard")
dl_row("DL-17", 49000, 50000, 1000, "capacity 0 with soft is DAILY LIMIT REACHED", "soft")
dl_row("DL-18", 48999.99, 50000, 1000, "capacity -0.01 with soft is DAILY LIMIT EXCEEDED", "soft")
M["DL-09"] = (Y, "touch false at the floor: room 0, no DLL, numeric contracts 0. Not a daily-limit status.",
              ST(50000, 2000, 48000, touch=False, risk=200, ticks=12, instrument="MES", max_minis="NONE", max_micros=50),
              FSF, "binding room 0")
M["DL-10"] = (P, "dll_enforcement other than hard or soft → INVALID on Accounts!AS and INVALID_INPUT in the oracle.",
              None, None, "categorical: bad token is invalid, not a silent soft exceed")
M["DL-11"] = (P, "day_pnl -1000.004 floors to daily room -0.01, so unconfirmed enforcement is RULE CONFIRMATION REQUIRED. Sheet money inputs are 2 dp, so this exact loss is not typed; scenarios check CENT_DOWN.",
              None, None, "oracle rounding case")
def fs(cid, room, risk, ticks, tv, maxc="NONE", extra=None):
    eq = 48000 + room
    note = ("OLD single-cap inner step: one max_contracts and a caller-supplied tick. "
            "NEW sheet derives the tick from ES/MES/NQ/MNQ and applies max_minis or max_micros, then this same formula. ")
    M[cid] = (Y, note + f"equivalent: static S=50000 DD=2000 equity {eq} (binding room {room}); risk {risk}, stop ticks {ticks}, tick value {tv}, max contracts {maxc}",
              ST(50000, 2000, eq, risk=risk, ticks=ticks, tv=tv, maxc=maxc), FSF, extra or "binding_room supplied via constructed account room")
fs("FS-22", 1000, 300, 16, 1.25, 50); fs("FS-23", 1000, 200, 20, 12.50, 5); fs("FS-24", 2000, 1000, 40, 0.50, 30)
fs("FS-25", 350, 999999, 1, 1, extra="OLD tick 1 is not an ES/MES/NQ/MNQ tick, so the workbook cannot enter this row. The room-clamp invariant is still checked here and, on a real instrument, by IA-08.")
fs("FS-26", 500, 500, 4, 1.25, 0); fs("FS-27", 500, 0, 4, 1.25)
fs("FS-28", 10, 0.996, 1, 0.995, extra="OLD sub-cent tick 0.995 is not an instrument tick. Money validation would reject the risk too. Inner invariant kept; the workbook does not accept this tick.")
M["FS-28"] = (P,) + M["FS-28"][1:]

def IA(cid, inst, risk, ticks, minis, micros, room=10000, rep=Y, fields=FSF, reason=None):
    eq = 48000 + room
    M[cid] = (rep, f"NEW instrument-aware: {inst} risk {risk} ticks {ticks} max_minis {minis} max_micros {micros} room {room}",
              {"type": "static", "start": 50000, "dd": 2000, "equity": eq, "instrument": inst,
               "max_minis": minis, "max_micros": micros, "risk": risk, "ticks": ticks},
              fields, reason or "tick and active cap are derived; inner INT formula is the legacy one")
IA("IA-01", "MES", 200, 12, 1, 50)
IA("IA-02", "ES", 200, 12, 5, 1)
IA("IA-03", "NQ", 200, 8, 10, "NONE")
IA("IA-04", "MNQ", 200, 8, "NONE", 100)
IA("IA-07", "MES", 200, 12, "NONE", 0)
IA("IA-08", "MES", 200, 12, "NONE", "NONE", room=15)
IA("IA-13", "MES", 200, 12, 1, 50)
IA("IA-14", "ES", 200, 12, 5, 1)
for cid, how in {
    "IA-05": "MES missing max_micros -> INCOMPLETE. A mini cap does not satisfy a micro instrument.",
    "IA-06": "ES missing max_minis -> INCOMPLETE. A micro cap does not satisfy a mini instrument.",
    "IA-09": "Instrument other than ES, MES, NQ, MNQ -> INVALID on the sheet.",
    "IA-10": "Blank instrument -> INCOMPLETE.",
    "IA-11": "Oracle rejects a tick_value that disagrees with the instrument. The sheet has no tick input, so a mismatch cannot be typed.",
    "IA-12": "Oracle accepts a tick_value equal to the instrument table. The sheet derives that value.",
}.items():
    M[cid] = (P, how, None, None, "NEW instrument-aware status. Sheet text is INCOMPLETE or INVALID; the oracle's error code is not copied onto the sheet.")
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
 "IV-46": "OLD fractional max_contracts 2.9 -> INVALID. NEW: a fractional active cap (the mini cap on ES/NQ, the micro cap on MES/MNQ) is INVALID the same way",
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
            check = list(fields)
            # daily_status is oracle/UI/sheet-status. The xlsx column map checks the blocking word separately.
            if "daily_status" in exp and "daily_status" in got and "daily_status" not in check:
                check.append("daily_status")
            if "dll_rule" in exp and "dll_rule" in got and "dll_rule" not in check:
                check.append("dll_rule")
            mism = {f: [norm(got[f]), exp[f]] for f in check if norm(got[f]) != exp[f]}
            ent["checked_fields"] = fields; ent["sheet_logic_match"] = not mism
            if mism: errs.append((cid, mism)); ent["mismatch"] = mism
        cases.append(ent)
    assert len(cases) == len(GOLD) and set(M) == set(GOLD)
    return {"spec": "tracker v0.2.0 instrument caps / oracle 0.2.0", "generated_by": "tracker/sheet_logic.py",
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

def cap_bad(v):
    if v == "" or v is None: return False
    if isinstance(v, str) and eq_ci(v, "NONE"): return False
    if num(v): return v < 0 or v != INT(v)
    return True

def w_status(a, accts, log):
    """Account param check. Blank instrument or blank active cap -> INCOMPLETE.
    ES/NQ require max_minis; MES/MNQ require max_micros. The other cap may be blank.
    Explicit 0 is present. NONE is the only unrestricted contract cap."""
    if a.get("id", "") == "" and a.get("preset", "") == "": return ""
    cap = active_cap_of(a)
    inst = a.get("instrument", "")
    req = [a.get(k, "") for k in ("id", "preset", "type", "start", "dd", "lock", "touch", "dll", "equity")]
    if any(v == "" for v in req) or inst == "" or cap == "" or (not eq_ci(str(a.get("dll", "")), "NONE") and a.get("day_ref", "") == ""):
        return "INCOMPLETE"
    lock_none = eq_ci(a["lock"], "NONE"); dll_none = eq_ci(a["dll"], "NONE")
    known = any(eq_ci(inst, s) for s in ("ES", "MES", "NQ", "MNQ"))
    enf = a.get("dll_enforcement", "")
    bad_enf = not (enf == "" or (isinstance(enf, str) and enf.strip().lower() in ("hard", "soft")))
    inval = (sum(eq_ci(a["id"], b["id"]) for b in accts) > 1
             or not any(eq_ci(a["type"], t) for t in ("static", "eod_trailing", "intraday_trailing"))
             or not money_ok(a["start"]) or not money_ok(a["dd"])
             or (not lock_none and not num(a["lock"]))
             or (eq_ci(a["type"], "static") and not lock_none)
             or (num(a["lock"]) and ROUND(a["start"] + a["lock"] - (a["start"] - a["dd"]), 6) <= 0)     # guard 1
             or (num(a["lock"]) and abs(a["lock"]) > MAXM)
             or a["touch"] not in (True, False)
             or (not dll_none and not money_ok(a["dll"]))
             or cap_bad(a.get("max_minis", "")) or cap_bad(a.get("max_micros", ""))                     # guard 2
             or not known
             or not money_ok(a["equity"])
             or (not dll_none and not money_ok(a["day_ref"]))
             or bad_enf)
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
    base = dict(id="P1", preset="Manual", type="static", start=50000, dd=2000, lock="NONE", touch=True, dll="NONE",
                instrument="MES", max_minis="NONE", max_micros="NONE", equity=49000, day_ref="")
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
    # M-1 reclassified: the old single maxc field is now the active cap (micro on MES, mini on ES/NQ).
    # Blank required cap -> INCOMPLETE. Explicit NONE -> OK. Explicit 0 stays present. Fractional -> INVALID.
    t("M-1 blank active cap", w_status(A(max_micros=""), [A()], []), "INCOMPLETE")
    t("M-1 NONE cap", w_status(A(max_micros="NONE"), [A()], []), "OK")
    t("M-1 numeric cap", w_status(A(max_micros=5), [A()], []), "OK")
    t("M-1 explicit zero", w_status(A(max_micros=0), [A()], []), "OK")
    t("M-1 fractional cap", w_status(A(max_micros=2.5), [A()], []), "INVALID")
    t("M-1 blank instrument", w_status(A(instrument=""), [A()], []), "INCOMPLETE")
    t("M-1 invalid instrument", w_status(A(instrument="ZZ"), [A()], []), "INVALID")
    t("M-1 ES missing mini", w_status(A(instrument="ES", max_minis="", max_micros=50), [A()], []), "INCOMPLETE")
    t("M-1 ES blank micro ok", w_status(A(instrument="ES", max_minis=5, max_micros=""), [A()], []), "OK")
    # BUILDER guards: NONE lock does not error; lock below floor INVALID; Locked FALSE on NONE
    t("guard1 NONE lock eod ok", w_status(A(type="eod_trailing"), [A()], []), "OK")
    t("guard1 lock below floor", w_status(A(type="eod_trailing", lock=-2500), [A()], []), "INVALID")
    t("guard2 text cap", w_status(A(max_micros="five"), [A()], []), "INVALID")
    t("guard3 Locked on NONE", locked_z(A(type="eod_trailing"), 60000), False)
    t("guard3 Locked numeric", locked_z(A(type="eod_trailing", lock=0), 52000), True)
    # L-1: fractional tick values
    t("L-1 tick 15.625", tick_ok(15.625), True)
    t("L-1 tick 3.125", tick_ok(3.125), True)
    t("L-1 tick 0.995", tick_ok(0.995), True)
    t("L-1 tick 7 dp", tick_ok(0.0000001), False)
    t("L-1 OLD inner ZN 15.625", size({"risk": 500, "ticks": 8, "tv": 15.625, "maxc": "NONE"}, 1000)["contracts"], 4)
    t("IA-01 MES 13", size({"instrument": "MES", "risk": 200, "ticks": 12, "max_minis": 1, "max_micros": 50}, 10000)["contracts"], 13)
    t("IA-02 ES 1", size({"instrument": "ES", "risk": 200, "ticks": 12, "max_minis": 5, "max_micros": 1}, 10000)["contracts"], 1)
    t("IA-03 NQ 5", size({"instrument": "NQ", "risk": 200, "ticks": 8, "max_minis": 10, "max_micros": "NONE"}, 10000)["contracts"], 5)
    t("IA-04 MNQ 50", size({"instrument": "MNQ", "risk": 200, "ticks": 8, "max_minis": "NONE", "max_micros": 100}, 10000)["contracts"], 50)
    t("IA-07 zero", size({"instrument": "MES", "risk": 200, "ticks": 12, "max_minis": "NONE", "max_micros": 0}, 10000)["contracts"], 0)
    t("IA-08 room still binds", size({"instrument": "MES", "risk": 200, "ticks": 12, "max_minis": "NONE", "max_micros": "NONE"}, 15)["contracts"], 1)
    # L-2: equity bound
    t("L-2 equity 1e15", w_status(A(equity=1e15), [A()], []), "INVALID")
    t("L-2 equity 0", w_status(A(equity=0), [A()], []), "INVALID")
    t("L-2 equity 1e8", w_status(A(equity=100000000), [A()], []), "OK")
    t("L-2 log close 1e9", w_status(A(), [A()], [{"acct": "P1", "date": "d", "eod": 1e9}]), "INVALID")
    # L-3: case-insensitive
    t("L-3 dup IDs ignoring case", w_status(A(id="p16"), [A(id="p16"), A(id="P16")], []), "INVALID")
    t("L-3 log p16 matches P16", log_row_status({"acct": "p16", "date": "d", "eod": 49000}, ["P16"]), "OK")
    t("L-3 none == NONE", w_status(A(lock="none", max_minis="none", max_micros="None"), [A()], []), "OK")
    t("L-3 trailing space invalid", w_status(A(type="Static "), [A()], []), "INVALID")
    t("DLL blank enforcement ok", w_status(A(), [A()], []), "OK")
    t("DLL hard token ok", w_status(A(dll_enforcement="hard"), [A()], []), "OK")
    t("DLL bad enforcement", w_status(A(dll_enforcement="nope"), [A()], []), "INVALID")
    t("DL subcent floors negative", CENT_DOWN(-0.004), -0.01)
    c01 = run({"type": "static", "start": 50000, "dd": 2000, "equity": 49000.01, "dll": 1000, "day_ref": 50000, "lock": "NONE", "touch": True, "risk": 200, "ticks": 12, "instrument": "MES", "max_minis": "NONE", "max_micros": 50})
    t("DL-01 status", c01["daily_status"], "OK")
    t("DL-01 room", c01["daily_room"], 0.01)
    t("DL-01 contracts numeric", c01["contracts"], 0)
    t("DL-01 tradable word", trade_status(c01, c01), "OK")
    c02 = run({"type": "static", "start": 50000, "dd": 2000, "equity": 49000, "dll": 1000, "day_ref": 50000, "lock": "NONE", "touch": True})
    t("DL-02 status", trade_status(c02, c02), "DAILY LIMIT REACHED")
    t("DL-02 room", c02["daily_room"], 0.0)
    c03 = run({"type": "static", "start": 50000, "dd": 2000, "equity": 48950, "dll": 1000, "day_ref": 50000, "lock": "NONE", "touch": True})
    t("DL-03 status", trade_status(c03, c03), "RULE CONFIRMATION REQUIRED")
    t("DL-03 room", c03["daily_room"], -50.0)
    t("DL-03 flag", breach_cell(c03, c03), "UNCONFIRMED")
    t("DL-03 rule", c03["dll_rule"], "unconfirmed")
    c04 = run({"type": "static", "start": 50000, "dd": 2000, "equity": 48950, "dll": 1000, "day_ref": 50000, "lock": "NONE", "touch": True, "dll_enforcement": "hard"})
    t("DL-04 status", trade_status(c04, c04), "BREACHED")
    t("DL-04 floor not hit", c04["breached"], False)
    t("DL-04 flag", breach_cell(c04, c04), True)
    # Blank / hard / soft at the four daily boundaries. Words are the spec, not a copy of another engine's output.
    spec = {
        (None, 49000.01): ("OK", False, "unconfirmed", 0.01),
        ("hard", 49000.01): ("OK", False, "hard", 0.01),
        ("soft", 49000.01): ("OK", False, "soft", 0.01),
        (None, 49000): ("DAILY LIMIT REACHED", False, "unconfirmed", 0.0),
        ("hard", 49000): ("DAILY LIMIT REACHED", False, "hard", 0.0),
        ("soft", 49000): ("DAILY LIMIT REACHED", False, "soft", 0.0),
        (None, 48999.99): ("RULE CONFIRMATION REQUIRED", "UNCONFIRMED", "unconfirmed", -0.01),
        ("hard", 48999.99): ("BREACHED", True, "hard", -0.01),
        ("soft", 48999.99): ("DAILY LIMIT EXCEEDED", False, "soft", -0.01),
        (None, 48950): ("RULE CONFIRMATION REQUIRED", "UNCONFIRMED", "unconfirmed", -50.0),
        ("hard", 48950): ("BREACHED", True, "hard", -50.0),
        ("soft", 48950): ("DAILY LIMIT EXCEEDED", False, "soft", -50.0),
    }
    for (enf, eq), (word, flag, rule, room) in spec.items():
        si = {"type": "static", "start": 50000, "dd": 2000, "equity": eq, "dll": 1000, "day_ref": 50000, "lock": "NONE", "touch": True, "risk": 200, "ticks": 12, "instrument": "MES", "max_minis": "NONE", "max_micros": 50}
        if enf: si["dll_enforcement"] = enf
        got = run(si)
        label = f"MX {enf or 'blank'} {eq}"
        t(label + " status", trade_status(got, got), word)
        t(label + " flag", breach_cell(got, got), flag)
        t(label + " rule", got["dll_rule"], rule)
        t(label + " room", got["daily_room"], room)
        if word == "OK":
            t(label + " contracts", got["contracts"], 0)
        else:
            t(label + " binding", got["binding_room"], 0.0)
    for enf in (None, "hard", "soft"):
        si = {"type": "static", "start": 50000, "dd": 2000, "equity": 49800, "dll": 1000, "day_ref": 50450, "lock": "NONE", "touch": True, "risk": 200, "ticks": 12, "instrument": "MES", "max_minis": "NONE", "max_micros": 50}
        if enf: si["dll_enforcement"] = enf
        got = run(si)
        t(f"MX open {enf or 'blank'} contracts", got["contracts"], 13)
        t(f"MX open {enf or 'blank'} status", trade_status(got, got), "OK")
    for enf in (None, "hard", "soft"):
        si = {"type": "static", "start": 50000, "dd": 2000, "equity": 48000, "dll": 1000, "day_ref": 50000, "lock": "NONE", "touch": True, "dll_enforcement": enf or ""}
        if enf: si["dll_enforcement"] = enf
        else: si.pop("dll_enforcement", None)
        got = run(si)
        t(f"MX floor {enf or 'blank'} status", trade_status(got, got), "BREACHED")
        t(f"MX floor {enf or 'blank'} flag", breach_cell(got, got), True)
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
