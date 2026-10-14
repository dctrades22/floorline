#!/usr/bin/env python3
"""prop-dd-calc reference oracle (spec v0.1.0). stdlib only, Decimal only.

Usage:
  python3 golden/oracle.py           # (re)generate golden/cases.json
  python3 golden/oracle.py --check   # recompute and diff against golden/cases.json (exit 1 on mismatch)
"""
import json, sys, os
from decimal import Decimal as D, ROUND_HALF_UP, ROUND_FLOOR, getcontext

getcontext().prec = 50
CENT = D("0.01")
SPEC_VERSION = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.json")


class SpecError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg); self.code = code


def money(x):
    return D(x).quantize(CENT, rounding=ROUND_HALF_UP)


def dec(v, name, positive=False, nonneg=False):
    try:
        d = D(str(v))
    except Exception:
        raise SpecError("INVALID_INPUT", f"{name} not a decimal")
    if not d.is_finite():
        raise SpecError("INVALID_INPUT", f"{name} not finite")
    if positive and d <= 0:
        raise SpecError("INVALID_INPUT", f"{name} must be > 0")
    if nonneg and d < 0:
        raise SpecError("INVALID_INPUT", f"{name} must be >= 0")
    return d


# ---------------- drawdown ----------------
def drawdown(inp):
    """inp: type static|eod_trailing|intraday_trailing, start_balance, drawdown_amount,
    lock_offset (None = never locks; 0 = locks at start; X = start+X),
    events: list of {"kind":"mark","equity":...} (intraday equity incl. unrealized)
            and {"kind":"eod","balance":...} (session-close balance).
    breach_on_touch (default true): breach when equity <= floor; false: equity < floor."""
    t = inp["type"]
    if t not in ("static", "eod_trailing", "intraday_trailing"):
        raise SpecError("INVALID_RULE_CONFIGURATION", "unknown drawdown type")
    start = dec(inp["start_balance"], "start_balance", positive=True)
    dd = dec(inp["drawdown_amount"], "drawdown_amount", positive=True)
    lo = inp.get("lock_offset")
    lock_level = None
    if lo is not None:
        lo = dec(lo, "lock_offset")
        lock_level = start + lo
        if lock_level < start - dd:
            raise SpecError("INVALID_RULE_CONFIGURATION", "lock level below initial floor")
    if t == "static" and lock_level is not None:
        raise SpecError("INVALID_RULE_CONFIGURATION", "static drawdown has no lock")
    touch = bool(inp.get("breach_on_touch", True))
    hit = (lambda e, f: e <= f) if touch else (lambda e, f: e < f)
    floor = start - dd
    peak = start
    locked = False
    breached = False
    equity = start
    def trail(p):
        nonlocal floor, locked
        if t == "static" or locked:
            return
        cand = p - dd
        if lock_level is not None and cand >= lock_level:
            cand = lock_level; locked = True
        if cand > floor:
            floor = cand
    for ev in inp.get("events", []):
        if breached:
            break  # terminal: later events ignored
        k = ev["kind"]
        if k == "mark":
            equity = dec(ev["equity"], "equity")
            if t == "intraday_trailing" and equity > peak:
                peak = equity; trail(peak)          # peak update before breach check
            if hit(equity, floor):
                breached = True
        elif k == "eod":
            equity = dec(ev["balance"], "balance")
            if hit(equity, floor):
                breached = True; continue
            if t == "eod_trailing" and equity > peak:
                peak = equity; trail(peak)
        else:
            raise SpecError("INVALID_INPUT", "unknown event kind")
    room = D(0) if breached else max(D(0), equity - floor)
    return {"floor": str(money(floor)), "peak": str(money(peak)), "locked": locked,
            "breached": breached, "equity": str(money(equity)), "drawdown_room": str(money(room))}


# ---------------- binding room ----------------
def risk_room(inp):
    dd_room = dec(inp["drawdown_room"], "drawdown_room", nonneg=True)
    dl = inp.get("daily_loss_limit")
    out = {"drawdown_room": str(money(dd_room))}
    if dl is None:
        out.update(daily_room=None, binding_room=str(money(dd_room)), binding="drawdown")
        return out
    dl = dec(dl, "daily_loss_limit", positive=True)
    day_pnl = dec(inp["day_pnl"], "day_pnl")
    day_loss = max(D(0), -day_pnl)
    d_room = max(D(0), dl - day_loss)
    b = min(dd_room, d_room)
    out.update(daily_room=str(money(d_room)), binding_room=str(money(b)),
               binding="daily_loss" if d_room < dd_room else "drawdown")
    return out


# ---------------- sizing ----------------
def size_futures(inp):
    risk = dec(inp["risk"], "risk", nonneg=True)
    ticks = dec(inp["stop_ticks"], "stop_ticks", positive=True)
    tv = dec(inp["tick_value"], "tick_value", positive=True)
    per = ticks * tv
    raw = (risk / per).to_integral_value(rounding=ROUND_FLOOR)
    n = int(raw)
    capped = False
    mc = inp.get("max_contracts")
    if mc is not None:
        mc = int(dec(mc, "max_contracts", nonneg=True))
        if n > mc:
            n = mc; capped = True
    return {"risk_per_contract": str(money(per)), "contracts": n, "capped": capped,
            "actual_risk": str(money(per * n))}


def size_crypto(inp):
    risk = dec(inp["risk"], "risk", nonneg=True)
    e = dec(inp["entry"], "entry", positive=True)
    s = dec(inp["stop"], "stop", positive=True)
    if e == s:
        raise SpecError("INVALID_INPUT", "entry == stop")
    dist = abs(e - s)
    q = risk / dist
    step = inp.get("step_size")
    if step is not None:
        step = dec(step, "step_size", positive=True)
        q = (q / step).to_integral_value(rounding=ROUND_FLOOR) * step
        q = q.quantize(step)
    return {"qty": str(q.normalize() if step is None else q),
            "actual_risk": str(money(q * dist))}


FUNCS = {"drawdown": drawdown, "risk_room": risk_room, "futures": size_futures, "crypto": size_crypto}


def evaluate(kind, inp):
    try:
        return {"ok": True, **FUNCS[kind](inp)}
    except SpecError as e:
        return {"ok": False, "error": e.code, "message": str(e)}


def ev(m): return {"kind": "mark", "equity": m}
def eod(b): return {"kind": "eod", "balance": b}

# (id, description, kind, input). Values are TEST fixtures, not firm rules.
DEFS = [
 ("DD-01", "static: equity above floor", "drawdown",
  {"type": "static", "start_balance": "50000", "drawdown_amount": "2000", "events": [ev("50800"), ev("49100")]}),
 ("DD-02", "static: touch floor exactly = breach", "drawdown",
  {"type": "static", "start_balance": "50000", "drawdown_amount": "2000", "events": [ev("49000"), ev("48000.00"), ev("49500")]}),
 ("DD-03", "eod trailing, no lock; intraday high ignored, floor trails EOD peak only", "drawdown",
  {"type": "eod_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": None,
   "events": [ev("51500"), eod("50600"), eod("50300"), ev("49000")]}),
 ("DD-04", "eod trailing, lock at start (offset 0)", "drawdown",
  {"type": "eod_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": "0",
   "events": [eod("51000"), eod("52500"), eod("54000"), ev("51000")]}),
 ("DD-05", "eod trailing, lock at start+100", "drawdown",
  {"type": "eod_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": "100",
   "events": [eod("51000"), eod("53000"), ev("50150.25")]}),
 ("DD-06", "eod trailing, lock exactly hit (peak-dd == lock level)", "drawdown",
  {"type": "eod_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": "100",
   "events": [eod("52100"), eod("51000")]}),
 ("DD-07", "eod trailing: intraday equity breaches floor between closes", "drawdown",
  {"type": "eod_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": "0",
   "events": [eod("51000"), ev("49200"), ev("48999.99"), eod("50500")]}),
 ("DD-08", "intraday trailing from open-equity peak incl. unrealized", "drawdown",
  {"type": "intraday_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": None,
   "events": [ev("50750.50"), ev("50200"), ev("49100")]}),
 ("DD-09", "intraday trailing, lock at start", "drawdown",
  {"type": "intraday_trailing", "start_balance": "25000", "drawdown_amount": "1000", "lock_offset": "0",
   "events": [ev("26400"), ev("25300")]}),
 ("DD-10", "intraday trailing, lock exactly hit at start+100", "drawdown",
  {"type": "intraday_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": "100",
   "events": [ev("52100"), ev("52600"), ev("50200")]}),
 ("DD-11", "intraday trailing breach after peak; later events ignored", "drawdown",
  {"type": "intraday_trailing", "start_balance": "50000", "drawdown_amount": "2000", "lock_offset": None,
   "events": [ev("51000"), ev("49000"), ev("51500")]}),
 ("RR-12", "daily-loss room binds", "risk_room",
  {"drawdown_room": "1800", "daily_loss_limit": "1000", "day_pnl": "-650"}),
 ("RR-13", "drawdown room binds; positive day pnl gives full daily room", "risk_room",
  {"drawdown_room": "400", "daily_loss_limit": "1000", "day_pnl": "250"}),
 ("FS-14", "futures MES basic: floor(300/(16*1.25))", "futures",
  {"risk": "300", "stop_ticks": "16", "tick_value": "1.25", "max_contracts": "50"}),
 ("FS-15", "futures ES: risk below one contract -> 0", "futures",
  {"risk": "200", "stop_ticks": "20", "tick_value": "12.50", "max_contracts": "5"}),
 ("FS-16", "futures MNQ capped by max contracts", "futures",
  {"risk": "1000", "stop_ticks": "40", "tick_value": "0.50", "max_contracts": "30"}),
 ("CS-17", "crypto perp qty with step size floor", "crypto",
  {"risk": "100", "entry": "65000", "stop": "64350", "step_size": "0.001"}),
 ("CS-18", "crypto perp short, no step", "crypto",
  {"risk": "50", "entry": "3200", "stop": "3240"}),
 ("IV-19", "invalid: crypto entry == stop", "crypto",
  {"risk": "100", "entry": "100", "stop": "100"}),
 ("IV-20", "invalid: futures stop_ticks = 0", "futures",
  {"risk": "100", "stop_ticks": "0", "tick_value": "1.25"}),
]


def build():
    return {"spec_version": SPEC_VERSION, "generated_by": "golden/oracle.py", "label": "TEST fixtures only",
            "cases": [{"id": i, "description": d, "kind": k, "input": inp, "expected": evaluate(k, inp)}
                      for i, d, k, inp in DEFS]}


def main():
    doc = build()
    assert len(doc["cases"]) == 20
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        with open(CASES) as f:
            on_disk = json.load(f)
        bad = 0
        for c in on_disk["cases"]:
            got = evaluate(c["kind"], c["input"])
            if got != c["expected"]:
                bad += 1; print("MISMATCH", c["id"], got, c["expected"])
        if len(on_disk["cases"]) != 20 or on_disk != doc:
            if not bad: print("MISMATCH: file differs from oracle definitions")
            bad += 1
        print("CHECK", "FAIL" if bad else "PASS", f"{len(on_disk['cases'])} cases")
        sys.exit(1 if bad else 0)
    with open(CASES, "w") as f:
        f.write(text)
    print("wrote", CASES)


if __name__ == "__main__":
    main()
