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
def _dll_enforcement(inp):
    """hard = exceeding the daily limit fails the account. soft = flat for the session, not a fail.
    Omitted or null = the rule does not define a breach, so it is not treated as hard."""
    if "dll_enforcement" not in inp or inp.get("dll_enforcement") is None:
        return None
    v = inp["dll_enforcement"]
    if not isinstance(v, str):
        bad("dll_enforcement must be hard or soft")
    s = v.strip().lower()
    if s not in ("hard", "soft"):
        bad("dll_enforcement must be hard or soft")
    return s


def _daily_status(capacity, enf):
    if capacity > 0:
        return "OK"
    if capacity == 0:
        return "DAILY LIMIT REACHED"
    return "BREACHED" if enf == "hard" else "DAILY LIMIT EXCEEDED"


def risk_room(inp):
    """Signed daily capacity, then a status. Floor breach is not decided here (see drawdown()).

    capacity > 0 → OK, and binding_room can size.
    capacity == 0 → DAILY LIMIT REACHED. binding_room is 0.
    capacity < 0 and dll_enforcement hard → BREACHED. Otherwise DAILY LIMIT EXCEEDED.
    Unstated enforcement is not a breach. binding_room is never negative: max(0, capacity).
    capacity is ROUND_FLOOR to the cent so a fraction below zero stays negative.
    Non-negative cent values match ROUND_DOWN, so existing positive rooms are unchanged.
    """
    dd_room = dec(need(inp, "drawdown_room"), "drawdown_room", nonneg=True)
    dl = inp.get("daily_loss_limit")
    if dl is None:
        return {"drawdown_room": r_down(dd_room), "daily_room": None,
                "binding_room": r_down(dd_room), "binding": "drawdown", "daily_status": None}
    dl = dec(dl, "daily_loss_limit", positive=True)
    day_pnl = dec(need(inp, "day_pnl"), "day_pnl")
    enf = _dll_enforcement(inp)
    raw = dl - max(D(0), -day_pnl)
    d_q = raw.quantize(CENT, rounding=ROUND_FLOOR)
    if d_q.is_zero():
        d_q = D("0.00")
    sized = max(D(0), d_q)
    return {"drawdown_room": r_down(dd_room), "daily_room": format(d_q, "f"),
            "binding_room": r_down(min(dd_room, sized)),
            "binding": "daily_loss" if d_q < dd_room else "drawdown",
            "daily_status": _daily_status(d_q, enf)}


def eff_risk(inp):
    """H-2: sizing is always bound by binding_room; risk is the request, never the authority."""
    risk = dec(need(inp, "risk"), "risk", nonneg=True)
    room = dec(need(inp, "binding_room"), "binding_room", nonneg=True)
    return min(risk, room), risk > room


# ---------------- sizing ----------------
# OLD single-cap path: the caller supplies tick_value and one optional max_contracts.
# NEW instrument-aware path (instrument present): tick value is derived, ES/NQ use
# max_minis, MES/MNQ (and the other micros) use max_micros. NONE removes only the
# contract cap. Risk is still min(risk, binding_room). Explicit 0 stays 0.
# A supplied tick_value that disagrees with the instrument is a mismatch.
INSTRUMENT_TICK = {
    "ES": D("12.50"), "MES": D("1.25"), "NQ": D("5.00"), "MNQ": D("0.50"),
    "GC": D("10.00"), "MGC": D("1.00"), "CL": D("10.00"), "MCL": D("1.00"),
    "6E": D("6.25"), "M6E": D("1.25"),
}
MICRO_INSTRUMENTS = {"MES", "MNQ", "MGC", "MCL", "M6E"}


def _cap_token(v, name):
    if v is None:
        bad(f"missing {name}")
    if isinstance(v, str) and v.strip().lower() == "none":
        return None
    return int(dec(v, name, nonneg=True, integer=True))


def size_futures_legacy(inp):
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


def size_futures_instrument(inp):
    raw = need(inp, "instrument")
    if not isinstance(raw, str) or raw.strip() == "":
        bad("missing instrument")
    sym = raw.strip().upper()
    if sym not in INSTRUMENT_TICK:
        bad("invalid instrument")
    tv = INSTRUMENT_TICK[sym]
    if "tick_value" in inp and inp.get("tick_value") is not None:
        given = dec(inp["tick_value"], "tick_value", positive=True)
        if given != tv:
            bad("tick_value mismatch")
    klass = "micro" if sym in MICRO_INSTRUMENTS else "mini"
    key = "max_micros" if klass == "micro" else "max_minis"
    other = "max_minis" if key == "max_micros" else "max_micros"
    if other in inp and inp.get(other) is not None:
        _cap_token(inp[other], other)
    if key not in inp:
        bad(f"missing {key}")
    cap = _cap_token(inp[key], key)
    legacy = {"risk": need(inp, "risk"), "binding_room": need(inp, "binding_room"),
              "stop_ticks": need(inp, "stop_ticks"), "tick_value": format(tv, "f")}
    if cap is not None:
        legacy["max_contracts"] = str(cap)
    out = size_futures_legacy(legacy)
    out["instrument"] = sym
    out["tick_value"] = format(tv, "f")
    out["cap_class"] = klass
    out["active_cap"] = "NONE" if cap is None else cap
    return out


def size_futures(inp):
    if isinstance(inp, dict) and "instrument" in inp:
        return size_futures_instrument(inp)
    return size_futures_legacy(inp)


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
 ("FS-22", "OLD single-cap (kept): MES-equivalent tick 1.25 and one max_contracts 50. NEW path derives the tick from the instrument and picks max_minis or max_micros. Inner floor-division invariant unchanged.", "futures", {"risk": "300", "binding_room": "1000", "stop_ticks": "16", "tick_value": "1.25", "max_contracts": "50"}),
 ("FS-23", "OLD single-cap (kept): ES-equivalent tick 12.50 and one max_contracts 5, below one contract -> 0. NEW path derives tick 12.50 from ES.", "futures", {"risk": "200", "binding_room": "1000", "stop_ticks": "20", "tick_value": "12.50", "max_contracts": "5"}),
 ("FS-24", "OLD single-cap (kept): MNQ-equivalent tick 0.50 and one max_contracts 30. NEW path uses max_micros for MNQ.", "futures", {"risk": "1000", "binding_room": "2000", "stop_ticks": "40", "tick_value": "0.50", "max_contracts": "30"}),
 ("FS-25", "OLD single-cap (kept): H-2 risk above binding room is clamped. Arbitrary tick 1 is not an instrument tick; the sheet no longer accepts it. Room clamp stays in force on the new path.", "futures", {"risk": "999999", "binding_room": "350", "stop_ticks": "1", "tick_value": "1"}),
 ("FS-26", "OLD single-cap (kept): max_contracts 0 -> 0. NEW path: an explicit 0 cap stays 0.", "futures", {"risk": "500", "binding_room": "500", "stop_ticks": "4", "tick_value": "1.25", "max_contracts": "0"}),
 ("FS-27", "OLD single-cap (kept): risk 0 -> 0 with no max_contracts. NEW path: NONE removes only the contract cap; risk 0 is still 0.", "futures", {"risk": "0", "binding_room": "500", "stop_ticks": "4", "tick_value": "1.25"}),
 ("FS-28", "OLD single-cap (kept): M-7 actual_risk never above risk. Sub-cent tick 0.995 is not an instrument tick.", "futures", {"risk": "0.996", "binding_room": "10", "stop_ticks": "1", "tick_value": "0.995"}),
 ("CS-29", "crypto long with step", "crypto", {"risk": "100", "binding_room": "1000", "entry": "65000", "stop": "64350", "step_size": "0.001"}),
 ("CS-30", "crypto short with step", "crypto", {"risk": "50", "binding_room": "1000", "entry": "3200", "stop": "3240", "step_size": "0.01"}),
 ("CS-31", "crypto sub-step result -> 0", "crypto", {"risk": "1", "binding_room": "1000", "entry": "65000", "stop": "60000", "step_size": "0.001"}),
 ("CS-32", "crypto tiny price, integer step", "crypto", {"risk": "30", "binding_room": "1000", "entry": "0.00001234", "stop": "0.00001200", "step_size": "1"}),
 ("CS-33", "crypto huge price", "crypto", {"risk": "250", "binding_room": "1000", "entry": "1250000", "stop": "1237500", "step_size": "0.0001"}),
 ("CS-34", "crypto risk clamped by room", "crypto", {"risk": "500", "binding_room": "120", "entry": "100", "stop": "98", "step_size": "0.1"}),
 ("IV-35", "invalid: crypto entry == stop", "crypto", {"risk": "100", "binding_room": "1000", "entry": "100", "stop": "100", "step_size": "0.01"}),
 ("IV-36", "OLD single-cap (kept): invalid futures stop_ticks = 0. Still invalid on the instrument path.", "futures", {"risk": "100", "binding_room": "1000", "stop_ticks": "0", "tick_value": "1.25"}),
 ("IV-37", "invalid: crypto without step_size (M-2)", "crypto", {"risk": "100", "binding_room": "1000", "entry": "100", "stop": "97"}),
 ("IV-38", "OLD single-cap (kept): sizing without binding_room (H-2). Still required when an instrument is set; risk, drawdown and daily loss stay active.", "futures", {"risk": "100", "stop_ticks": "4", "tick_value": "1.25"}),
 ("IV-39", "config: lock level below initial floor", "drawdown", DDI("eod_trailing", "50000", "2000", [], lock_offset="-2500")),
 ("IV-40", "config: static with lock", "drawdown", DDI("static", "50000", "2000", [], lock_offset="0")),
 ("IV-41", "config: unknown drawdown type", "drawdown", DDI("hybrid", "50000", "2000", [])),
 ("IV-42", "M-1: event without kind", "drawdown", DDI("static", "50000", "2000", [{"equity": "49000"}])),
 ("IV-43", "M-1: DLL without day_pnl", "risk_room", {"drawdown_room": "500", "daily_loss_limit": "1000"}),
 ("IV-44", "M-1: missing type", "drawdown", {"start_balance": "50000", "drawdown_amount": "2000", "events": []}),
 ("IV-45", "M-1: crypto huge risk / tiny step overflows precision", "crypto", {"risk": "1E+40", "binding_room": "1E+40", "entry": "2", "stop": "1", "step_size": "1E-20"}),
 ("IV-46", "OLD single-cap (kept): fractional max_contracts. NEW path rejects a fractional active cap the same way.", "futures", {"risk": "100", "binding_room": "100", "stop_ticks": "4", "tick_value": "1.25", "max_contracts": "2.9"}),
 ("IV-47", "OLD single-cap (kept): fractional stop_ticks. Still invalid on the instrument path.", "futures", {"risk": "100", "binding_room": "100", "stop_ticks": "0.5", "tick_value": "1.25"}),
 ("IA-01", "NEW instrument-aware: MES $200, 12-tick stop, 50 micro cap -> 13. Mini cap is not used.", "futures", {"instrument": "MES", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "1", "max_micros": "50"}),
 ("IA-02", "NEW instrument-aware: ES $200, 12 ticks, 5 mini cap -> 1. Micro cap is not used.", "futures", {"instrument": "ES", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "5", "max_micros": "1"}),
 ("IA-03", "NEW instrument-aware: NQ $200, 8 ticks, 10 mini cap -> 5.", "futures", {"instrument": "NQ", "risk": "200", "binding_room": "10000", "stop_ticks": "8", "max_minis": "10", "max_micros": "NONE"}),
 ("IA-04", "NEW instrument-aware: MNQ $200, 8 ticks, 100 micro cap -> 50.", "futures", {"instrument": "MNQ", "risk": "200", "binding_room": "10000", "stop_ticks": "8", "max_minis": "NONE", "max_micros": "100"}),
 ("IA-05", "NEW: MES missing max_micros is an error. A mini cap does not fill it.", "futures", {"instrument": "MES", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "5"}),
 ("IA-06", "NEW: ES missing max_minis is an error. A micro cap does not fill it.", "futures", {"instrument": "ES", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_micros": "50"}),
 ("IA-07", "NEW: explicit micro cap 0 stays 0.", "futures", {"instrument": "MES", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "NONE", "max_micros": "0"}),
 ("IA-08", "NEW: NONE removes only the contract cap. Binding room (drawdown or daily loss) still clamps.", "futures", {"instrument": "MES", "risk": "200", "binding_room": "15", "stop_ticks": "12", "max_minis": "NONE", "max_micros": "NONE"}),
 ("IA-09", "NEW: invalid instrument.", "futures", {"instrument": "ZZ", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "5", "max_micros": "50"}),
 ("IA-10", "NEW: blank instrument.", "futures", {"instrument": "", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "5", "max_micros": "50"}),
 ("IA-11", "NEW: tick_value that disagrees with the instrument is a mismatch.", "futures", {"instrument": "MES", "tick_value": "12.50", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "NONE", "max_micros": "50"}),
 ("IA-12", "NEW: tick_value that matches the instrument is accepted and cannot disagree.", "futures", {"instrument": "MES", "tick_value": "1.25", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "1", "max_micros": "50"}),
 ("IA-13", "NEW: MES uses the micro cap even when the mini cap is tighter.", "futures", {"instrument": "mes", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "1", "max_micros": "50"}),
 ("IA-14", "NEW: ES uses the mini cap even when the micro cap is tighter.", "futures", {"instrument": "ES", "risk": "200", "binding_room": "10000", "stop_ticks": "12", "max_minis": "5", "max_micros": "1"}),
 ("DL-01", "daily capacity $0.01 left sizes normally. Status OK. The stop may still round to 0 contracts.", "risk_room", {"drawdown_room": "1000.01", "daily_loss_limit": "1000", "day_pnl": "-999.99"}),
 ("DL-02", "daily capacity exactly 0 is DAILY LIMIT REACHED. binding_room 0. Not a breach.", "risk_room", {"drawdown_room": "1000", "daily_loss_limit": "1000", "day_pnl": "-1000"}),
 ("DL-03", "daily capacity -50 with enforcement unstated is DAILY LIMIT EXCEEDED, not a breach.", "risk_room", {"drawdown_room": "950", "daily_loss_limit": "1000", "day_pnl": "-1050"}),
 ("DL-04", "daily capacity -50 with hard enforcement is BREACHED.", "risk_room", {"drawdown_room": "950", "daily_loss_limit": "1000", "day_pnl": "-1050", "dll_enforcement": "hard"}),
 ("DL-05", "one cent past the daily limit, enforcement unstated, is DAILY LIMIT EXCEEDED. Floor-to-cent does not collapse this to zero.", "risk_room", {"drawdown_room": "999.99", "daily_loss_limit": "1000", "day_pnl": "-1000.01"}),
 ("DL-06", "one cent past the daily limit, hard enforcement, is BREACHED.", "risk_room", {"drawdown_room": "999.99", "daily_loss_limit": "1000", "day_pnl": "-1000.01", "dll_enforcement": "hard"}),
 ("DL-07", "explicit soft enforcement on a negative capacity is DAILY LIMIT EXCEEDED, not BREACHED.", "risk_room", {"drawdown_room": "950", "daily_loss_limit": "1000", "day_pnl": "-1050", "dll_enforcement": "soft"}),
 ("DL-08", "hard enforcement with capacity still positive stays OK and sizes from that room.", "risk_room", {"drawdown_room": "1800", "daily_loss_limit": "1000", "day_pnl": "-650", "dll_enforcement": "hard"}),
 ("DL-09", "binding room 0 sizes 0 contracts. A numeric 0 is not a daily-limit status.", "futures", {"instrument": "MES", "risk": "200", "binding_room": "0", "stop_ticks": "12", "max_minis": "NONE", "max_micros": "50"}),
 ("DL-10", "dll_enforcement other than hard or soft is INVALID_INPUT.", "risk_room", {"drawdown_room": "950", "daily_loss_limit": "1000", "day_pnl": "-1050", "dll_enforcement": "nope"}),
 ("DL-11", "a fraction of a cent below zero floors to -0.01, so it is DAILY LIMIT EXCEEDED and not reported as zero.", "risk_room", {"drawdown_room": "1000", "daily_loss_limit": "1000", "day_pnl": "-1000.004"}),
 ("DL-12", "enforcement token HARD is case-insensitive and means hard.", "risk_room", {"drawdown_room": "950", "daily_loss_limit": "1000", "day_pnl": "-1050", "dll_enforcement": "HARD"}),
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
