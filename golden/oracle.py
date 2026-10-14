#!/usr/bin/env python3
"""prop-dd-calc reference oracle (spec v0.2.0). stdlib only, Decimal only.

  python3 golden/oracle.py           # regenerate golden/cases.json
  python3 golden/oracle.py --check   # recompute + diff cases, and validate data/presets.json (exit 1 on any failure)
"""
import json, sys, os
from decimal import (Decimal as D, ROUND_FLOOR, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP,
                     getcontext, InvalidOperation)

getcontext().prec = 50
getcontext().traps[InvalidOperation] = True
CENT = D("0.01")
SPEC_VERSION = "0.2.0"
HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.json")


class SpecError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg); self.code = code


def bad(msg): raise SpecError("INVALID_INPUT", msg)
def badcfg(msg): raise SpecError("INVALID_RULE_CONFIGURATION", msg)

# Output rounding (M-7): conservative direction for every safety value.
def r_floor_level(x): return str(D(x).quantize(CENT, rounding=ROUND_CEILING))  # loss floor: round up
def r_down(x): return str(D(x).quantize(CENT, rounding=ROUND_DOWN))           # rooms / risk: toward zero
def r_near(x): return str(D(x).quantize(CENT, rounding=ROUND_HALF_UP))        # informational only
def fixed(x): return format(x, "f")


def need(inp, key):
    if not isinstance(inp, dict) or key not in inp: bad(f"missing {key}")
    return inp[key]


def dec(v, name, positive=False, nonneg=False, integer=False):
    if isinstance(v, bool) or not isinstance(v, (str, int)):
        bad(f"{name} must be a decimal string or int")
    try:
        d = D(str(v).strip())
    except InvalidOperation:
        bad(f"{name} not a decimal")
    if not d.is_finite(): bad(f"{name} not finite")
    if positive and d <= 0: bad(f"{name} must be > 0")
    if nonneg and d < 0: bad(f"{name} must be >= 0")
    if integer and d != d.to_integral_value(): bad(f"{name} must be an integer")
    return d


# ---------------- drawdown ----------------
def drawdown(inp):
    t = need(inp, "type")
    if t not in ("static", "eod_trailing", "intraday_trailing"): badcfg("unknown drawdown type")
    start = dec(need(inp, "start_balance"), "start_balance", positive=True)
    dd = dec(need(inp, "drawdown_amount"), "drawdown_amount", positive=True)
    touch = inp.get("breach_on_touch", True)
    if not isinstance(touch, bool): bad("breach_on_touch must be boolean")
    lo = inp.get("lock_offset")
    lock_level = None
    if lo is not None:
        if t == "static": badcfg("static drawdown has no lock")
        lock_level = start + dec(lo, "lock_offset")
        if lock_level <= start - dd: badcfg("lock level must be above initial floor")
    events = need(inp, "events")
    if not isinstance(events, list): bad("events must be a list")
    parsed = []                                   # L-3: validate every event up front
    for e in events:
        k = need(e, "kind")
        if k == "mark": parsed.append(("mark", dec(need(e, "equity"), "equity")))
        elif k == "eod": parsed.append(("eod", dec(need(e, "balance"), "balance")))
        else: bad("unknown event kind")
    hit = (lambda e, f: e <= f) if touch else (lambda e, f: e < f)
    floor, peak, locked, breached, equity = start - dd, start, False, False, start

    def trail(p):
        nonlocal floor, locked
        if t == "static" or locked: return
        c = p - dd
        if lock_level is not None and c >= lock_level:
            c = lock_level; locked = True
        if c > floor: floor = c

    for k, v in parsed:
        if breached: break                        # terminal
        equity = v
        if t == "intraday_trailing" and v > peak:  # H-1: marks AND eod are peak candidates
            peak = v; trail(peak)
        if hit(v, floor):
            breached = True; continue
        if t == "eod_trailing" and k == "eod" and v > peak:
            peak = v; trail(peak)
    room = D(0) if breached else max(D(0), equity - floor)
    return {"floor": r_floor_level(floor), "peak": r_near(peak), "locked": locked,
            "breached": breached, "equity": r_down(equity), "drawdown_room": r_down(room)}


# ---------------- binding room ----------------
def risk_room(inp):
    dd_room = dec(need(inp, "drawdown_room"), "drawdown_room", nonneg=True)
    dl = inp.get("daily_loss_limit")
    if dl is None:
        return {"drawdown_room": r_down(dd_room), "daily_room": None,
                "binding_room": r_down(dd_room), "binding": "drawdown"}
    dl = dec(dl, "daily_loss_limit", positive=True)
    day_pnl = dec(need(inp, "day_pnl"), "day_pnl")
    d_room = max(D(0), dl - max(D(0), -day_pnl))
    return {"drawdown_room": r_down(dd_room), "daily_room": r_down(d_room),
            "binding_room": r_down(min(dd_room, d_room)),
            "binding": "daily_loss" if d_room < dd_room else "drawdown"}


def eff_risk(inp):
    """H-2: sizing is always bound by binding_room; risk is the request, never the authority."""
    risk = dec(need(inp, "risk"), "risk", nonneg=True)
    room = dec(need(inp, "binding_room"), "binding_room", nonneg=True)
    return min(risk, room), risk > room


# ---------------- sizing ----------------
def size_futures(inp):
    risk, limited = eff_risk(inp)
    ticks = dec(need(inp, "stop_ticks"), "stop_ticks", positive=True, integer=True)
    tv = dec(need(inp, "tick_value"), "tick_value", positive=True)
    mc = inp.get("max_contracts")
    if mc is not None: mc = int(dec(mc, "max_contracts", nonneg=True, integer=True))
    per = ticks * tv
    n = int((risk / per).to_integral_value(rounding=ROUND_FLOOR))
    capped = mc is not None and n > mc
    if capped: n = mc
    return {"effective_risk": r_down(risk), "risk_limited_by_room": limited,
            "risk_per_contract": fixed(per), "contracts": n, "capped": capped,
            "actual_risk": r_down(per * n)}


def size_crypto(inp):
    risk, limited = eff_risk(inp)
    e = dec(need(inp, "entry"), "entry", positive=True)
    s = dec(need(inp, "stop"), "stop", positive=True)
    step = dec(need(inp, "step_size"), "step_size", positive=True)   # M-2: required
    if e == s: bad("entry == stop")
    dist = abs(e - s)
    q = (risk / dist / step).to_integral_value(rounding=ROUND_FLOOR) * step
    q = q.quantize(step, rounding=ROUND_FLOOR)
    return {"effective_risk": r_down(risk), "risk_limited_by_room": limited,
            "side": "long" if s < e else "short", "qty": fixed(q), "actual_risk": r_down(q * dist)}


FUNCS = {"drawdown": drawdown, "risk_room": risk_room, "futures": size_futures, "crypto": size_crypto}


def evaluate(kind, inp):
    try:
        if kind not in FUNCS: bad("unknown kind")
        return {"ok": True, **FUNCS[kind](inp)}
    except SpecError as e:
        return {"ok": False, "error": e.code, "message": str(e)}
    except (KeyError, TypeError, ValueError, AttributeError, InvalidOperation, ArithmeticError) as e:
        return {"ok": False, "error": "INVALID_INPUT", "message": "malformed input: " + type(e).__name__}


def ev(m): return {"kind": "mark", "equity": m}
def eod(b): return {"kind": "eod", "balance": b}
def DDI(t, s, dd, events, **kw): return {"type": t, "start_balance": s, "drawdown_amount": dd, "events": events, **kw}

# TEST fixtures only (not firm rules).
DEFS = [
 ("DD-01", "static: equity above floor", "drawdown", DDI("static", "50000", "2000", [ev("50800"), ev("49100")])),
 ("DD-02", "static: touch floor exactly = breach (default)", "drawdown", DDI("static", "50000", "2000", [ev("49000"), ev("48000.00"), ev("49500")])),
 ("DD-03", "eod trailing no lock; intraday high ignored", "drawdown", DDI("eod_trailing", "50000", "2000", [ev("51500"), eod("50600"), eod("50300"), ev("49000")])),
 ("DD-04", "eod trailing, lock at start (X=0)", "drawdown", DDI("eod_trailing", "50000", "2000", [eod("51000"), eod("52500"), eod("54000"), ev("51000")], lock_offset="0")),
 ("DD-05", "eod trailing, lock at start+100", "drawdown", DDI("eod_trailing", "50000", "2000", [eod("51000"), eod("53000"), ev("50150.25")], lock_offset="100")),
 ("DD-06", "eod trailing, lock exactly hit", "drawdown", DDI("eod_trailing", "50000", "2000", [eod("52100"), eod("51000")], lock_offset="100")),
 ("DD-07", "eod trailing: intraday breach between closes, later close ignored", "drawdown", DDI("eod_trailing", "50000", "2000", [eod("51000"), ev("49200"), ev("48999.99"), eod("50500")], lock_offset="0")),
 ("DD-08", "intraday trailing from open-equity peak", "drawdown", DDI("intraday_trailing", "50000", "2000", [ev("50750.50"), ev("50200"), ev("49100")])),
 ("DD-09", "intraday trailing, lock at start", "drawdown", DDI("intraday_trailing", "25000", "1000", [ev("26400"), ev("25300")], lock_offset="0")),
 ("DD-10", "intraday trailing, lock exactly hit at start+100", "drawdown", DDI("intraday_trailing", "50000", "2000", [ev("52100"), ev("52600"), ev("50200")], lock_offset="100")),
 ("DD-11", "intraday trailing breach; later events ignored", "drawdown", DDI("intraday_trailing", "50000", "2000", [ev("51000"), ev("49000"), ev("51500")])),
 ("DD-12", "touch=false: equity == floor is not a breach, room 0", "drawdown", DDI("static", "25000", "1000", [ev("24000")], breach_on_touch=False)),
 ("DD-13", "touch=false: one cent below floor breaches", "drawdown", DDI("static", "25000", "1000", [ev("23999.99")], breach_on_touch=False)),
 ("DD-14", "lock one cent short stays unlocked", "drawdown", DDI("eod_trailing", "50000", "2000", [eod("52099.99")], lock_offset="100")),
 ("DD-15", "negative lock_offset (lock at start-500)", "drawdown", DDI("eod_trailing", "50000", "2000", [eod("51000"), eod("52000")], lock_offset="-500")),
 ("DD-16", "H-1: intraday trailing, eod above peak trails", "drawdown", DDI("intraday_trailing", "50000", "2000", [eod("53000")])),
 ("DD-17", "M-7: sub-cent room rounds toward zero; floor rounds up", "drawdown", DDI("intraday_trailing", "50000", "2000", [ev("50000.004"), ev("48000.009")])),
 ("RR-18", "daily-loss room binds", "risk_room", {"drawdown_room": "1800", "daily_loss_limit": "1000", "day_pnl": "-650"}),
 ("RR-19", "drawdown room binds; positive day pnl", "risk_room", {"drawdown_room": "400", "daily_loss_limit": "1000", "day_pnl": "250"}),
 ("RR-20", "no DLL: drawdown binds", "risk_room", {"drawdown_room": "1234.56"}),
 ("RR-21", "tie daily == drawdown -> binding drawdown", "risk_room", {"drawdown_room": "500", "daily_loss_limit": "1000", "day_pnl": "-500"}),
 ("FS-22", "futures MES basic", "futures", {"risk": "300", "binding_room": "1000", "stop_ticks": "16", "tick_value": "1.25", "max_contracts": "50"}),
 ("FS-23", "futures ES: below one contract -> 0", "futures", {"risk": "200", "binding_room": "1000", "stop_ticks": "20", "tick_value": "12.50", "max_contracts": "5"}),
 ("FS-24", "futures MNQ capped by max contracts", "futures", {"risk": "1000", "binding_room": "2000", "stop_ticks": "40", "tick_value": "0.50", "max_contracts": "30"}),
 ("FS-25", "H-2: risk above binding room is clamped", "futures", {"risk": "999999", "binding_room": "350", "stop_ticks": "1", "tick_value": "1"}),
 ("FS-26", "max_contracts 0 -> 0", "futures", {"risk": "500", "binding_room": "500", "stop_ticks": "4", "tick_value": "1.25", "max_contracts": "0"}),
 ("FS-27", "risk 0 -> 0", "futures", {"risk": "0", "binding_room": "500", "stop_ticks": "4", "tick_value": "1.25"}),
 ("FS-28", "M-7: actual_risk never above risk", "futures", {"risk": "0.996", "binding_room": "10", "stop_ticks": "1", "tick_value": "0.995"}),
 ("CS-29", "crypto long with step", "crypto", {"risk": "100", "binding_room": "1000", "entry": "65000", "stop": "64350", "step_size": "0.001"}),
 ("CS-30", "crypto short with step", "crypto", {"risk": "50", "binding_room": "1000", "entry": "3200", "stop": "3240", "step_size": "0.01"}),
 ("CS-31", "crypto sub-step result -> 0", "crypto", {"risk": "1", "binding_room": "1000", "entry": "65000", "stop": "60000", "step_size": "0.001"}),
 ("CS-32", "crypto tiny price, integer step", "crypto", {"risk": "30", "binding_room": "1000", "entry": "0.00001234", "stop": "0.00001200", "step_size": "1"}),
 ("CS-33", "crypto huge price", "crypto", {"risk": "250", "binding_room": "1000", "entry": "1250000", "stop": "1237500", "step_size": "0.0001"}),
 ("CS-34", "crypto risk clamped by room", "crypto", {"risk": "500", "binding_room": "120", "entry": "100", "stop": "98", "step_size": "0.1"}),
 ("IV-35", "invalid: crypto entry == stop", "crypto", {"risk": "100", "binding_room": "1000", "entry": "100", "stop": "100", "step_size": "0.01"}),
 ("IV-36", "invalid: futures stop_ticks = 0", "futures", {"risk": "100", "binding_room": "1000", "stop_ticks": "0", "tick_value": "1.25"}),
 ("IV-37", "invalid: crypto without step_size (M-2)", "crypto", {"risk": "100", "binding_room": "1000", "entry": "100", "stop": "97"}),
 ("IV-38", "invalid: sizing without binding_room (H-2)", "futures", {"risk": "100", "stop_ticks": "4", "tick_value": "1.25"}),
 ("IV-39", "config: lock level below initial floor", "drawdown", DDI("eod_trailing", "50000", "2000", [], lock_offset="-2500")),
 ("IV-40", "config: static with lock", "drawdown", DDI("static", "50000", "2000", [], lock_offset="0")),
 ("IV-41", "config: unknown drawdown type", "drawdown", DDI("hybrid", "50000", "2000", [])),
 ("IV-42", "M-1: event without kind", "drawdown", DDI("static", "50000", "2000", [{"equity": "49000"}])),
 ("IV-43", "M-1: DLL without day_pnl", "risk_room", {"drawdown_room": "500", "daily_loss_limit": "1000"}),
 ("IV-44", "M-1: missing type", "drawdown", {"start_balance": "50000", "drawdown_amount": "2000", "events": []}),
 ("IV-45", "M-1: crypto huge risk / tiny step overflows precision", "crypto", {"risk": "1E+40", "binding_room": "1E+40", "entry": "2", "stop": "1", "step_size": "1E-20"}),
 ("IV-46", "L-1: fractional max_contracts", "futures", {"risk": "100", "binding_room": "100", "stop_ticks": "4", "tick_value": "1.25", "max_contracts": "2.9"}),
 ("IV-47", "L-1: fractional stop_ticks", "futures", {"risk": "100", "binding_room": "100", "stop_ticks": "0.5", "tick_value": "1.25"}),
 ("IV-48", "L-2: breach_on_touch as string", "drawdown", DDI("static", "50000", "2000", [], breach_on_touch="false")),
 ("IV-49", "L-3: invalid event after breach still rejected", "drawdown", DDI("static", "50000", "2000", [ev("47000"), {"kind": "bogus"}])),
]


def build():
    return {"spec_version": SPEC_VERSION, "generated_by": "golden/oracle.py", "label": "TEST fixtures only",
            "cases": [{"id": i, "description": d, "kind": k, "input": inp, "expected": evaluate(k, inp)}
                      for i, d, k, inp in DEFS]}


def main():
    doc = build()
    if "--check" in sys.argv:
        sys.path.insert(0, HERE)
        import validate_presets
        with open(CASES) as f: disk = json.load(f)
        nbad = 0
        for c in disk["cases"]:
            got = evaluate(c["kind"], c["input"])
            if got != c["expected"]: nbad += 1; print("MISMATCH", c["id"], got, c["expected"])
        if disk != doc:
            if not nbad: print("MISMATCH: cases.json differs from oracle definitions")
            nbad += 1
        print("CASES", "FAIL" if nbad else "PASS", len(disk["cases"]))
        perr = validate_presets.main_check()
        sys.exit(1 if (nbad or perr) else 0)
    with open(CASES, "w") as f: f.write(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print("wrote", CASES, len(doc["cases"]), "cases")


if __name__ == "__main__":
    main()
