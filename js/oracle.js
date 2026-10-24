/* Faithful JS port of golden/oracle.py (spec v0.2.0). Same inputs, same outputs, same error codes/messages. */
(function (root) {
  "use strict";
  var Dec = (typeof module !== "undefined" && module.exports) ? require("./decimal.js") : root.Dec;
  function SpecError(code, msg) { var e = new Error(msg); e.specCode = code; return e; }
  function bad(m) { throw SpecError("INVALID_INPUT", m); }
  function badcfg(m) { throw SpecError("INVALID_RULE_CONFIGURATION", m); }
  function isDict(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function get(o, k) { return has(o, k) ? o[k] : null; }           // dict.get(k) -> None
  function need(inp, key) { if (!isDict(inp) || !has(inp, key)) bad("missing " + key); return inp[key]; }

  var CENT = -2;
  function rFloorLevel(x) { return Dec.toFixed(Dec.quantize(x, CENT, "CEILING")); }
  function rDown(x) { return Dec.toFixed(Dec.quantize(x, CENT, "DOWN")); }
  function dllEnforcement(inp) {
    if (!has(inp, "dll_enforcement") || inp.dll_enforcement === null) return null;
    var v = inp.dll_enforcement;
    if (typeof v !== "string") bad("dll_enforcement must be hard or soft");
    var s = v.trim().toLowerCase();
    if (s !== "hard" && s !== "soft") bad("dll_enforcement must be hard or soft");
    return s;
  }
  function dllBoundary(inp) {
    if (!has(inp, "dll_boundary") || inp.dll_boundary === null) return null;
    var v = inp.dll_boundary;
    if (typeof v !== "string") bad("dll_boundary must be reach or exceed");
    var s = v.trim().toLowerCase();
    if (s !== "reach" && s !== "exceed") bad("dll_boundary must be reach or exceed");
    return s;
  }
  function dllRule(enf) { return enf === "hard" || enf === "soft" ? enf : "unconfirmed"; }
  function boundaryRule(boundary) { return boundary === "reach" || boundary === "exceed" ? boundary : "unconfirmed"; }
  // >0 OK. <0 ignores boundary. ==0: hard+reach BREACHED; confirmed exceed, or soft+reach, DAILY LIMIT REACHED.
  // Soft never breaches. Either classification omitted at exactly 0 is RULE CONFIRMATION REQUIRED.
  function dailyStatus(capacity, enf, boundary) {
    if (Dec.cmp(capacity, Dec.ZERO) > 0) return "OK";
    if (Dec.cmp(capacity, Dec.ZERO) < 0) {
      if (enf === "hard") return "BREACHED";
      if (enf === "soft") return "DAILY LIMIT EXCEEDED";
      return "RULE CONFIRMATION REQUIRED";
    }
    if ((enf !== "hard" && enf !== "soft") || (boundary !== "reach" && boundary !== "exceed")) return "RULE CONFIRMATION REQUIRED";
    if (enf === "hard" && boundary === "reach") return "BREACHED";
    return "DAILY LIMIT REACHED";
  }
  // After empty / INCOMPLETE / INVALID. Floor outranks every daily word.
  function accountStatus(floorBreached, dailyStatusWord) {
    if (floorBreached) return "BREACHED";
    if (dailyStatusWord === "BREACHED" || dailyStatusWord === "RULE CONFIRMATION REQUIRED" ||
        dailyStatusWord === "DAILY LIMIT EXCEEDED" || dailyStatusWord === "DAILY LIMIT REACHED") return dailyStatusWord;
    return "OK";
  }
  function rNear(x) { return Dec.toFixed(Dec.quantize(x, CENT, "HALF_UP")); }

  function dec(v, name, o) {
    o = o || {};
    var s;
    if (typeof v === "string") s = v;
    else if (typeof v === "number" && Number.isInteger(v)) s = String(BigInt(v));  // Python int
    else bad(name + " must be a decimal string or int");
    var d;
    try { d = Dec.parse(s); } catch (e) { bad(name + " not a decimal"); }
    if (d.special) bad(name + " not finite");
    if (o.positive && Dec.cmp(d, Dec.ZERO) <= 0) bad(name + " must be > 0");
    if (o.nonneg && Dec.cmp(d, Dec.ZERO) < 0) bad(name + " must be >= 0");
    if (o.integer && !Dec.isInteger(d)) bad(name + " must be an integer");
    return d;
  }

  function drawdown(inp) {
    var t = need(inp, "type");
    if (["static", "eod_trailing", "intraday_trailing"].indexOf(t) < 0) badcfg("unknown drawdown type");
    var start = dec(need(inp, "start_balance"), "start_balance", { positive: true });
    var dd = dec(need(inp, "drawdown_amount"), "drawdown_amount", { positive: true });
    var touch = has(inp, "breach_on_touch") ? inp.breach_on_touch : true;
    if (typeof touch !== "boolean") bad("breach_on_touch must be boolean");
    var lo = get(inp, "lock_offset"), lockLevel = null;
    if (lo !== null) {
      if (t === "static") badcfg("static drawdown has no lock");
      lockLevel = Dec.add(start, dec(lo, "lock_offset"));
      if (Dec.cmp(lockLevel, Dec.sub(start, dd)) <= 0) badcfg("lock level must be above initial floor");
    }
    var events = need(inp, "events");
    if (!Array.isArray(events)) bad("events must be a list");
    var parsed = events.map(function (e) {
      var k = need(e, "kind");
      if (k === "mark") return ["mark", dec(need(e, "equity"), "equity")];
      if (k === "eod") return ["eod", dec(need(e, "balance"), "balance")];
      bad("unknown event kind");
    });
    var hit = touch ? function (e, f) { return Dec.cmp(e, f) <= 0; } : function (e, f) { return Dec.cmp(e, f) < 0; };
    var floor = Dec.sub(start, dd), peak = start, locked = false, breached = false, equity = start;
    function trail(p) {
      if (t === "static" || locked) return;
      var c = Dec.sub(p, dd);
      if (lockLevel !== null && Dec.cmp(c, lockLevel) >= 0) { c = lockLevel; locked = true; }
      if (Dec.cmp(c, floor) > 0) floor = c;
    }
    for (var i = 0; i < parsed.length; i++) {
      if (breached) break;
      var k = parsed[i][0], v = parsed[i][1];
      equity = v;
      if (t === "intraday_trailing" && Dec.cmp(v, peak) > 0) { peak = v; trail(peak); }
      if (hit(v, floor)) { breached = true; continue; }
      if (t === "eod_trailing" && k === "eod" && Dec.cmp(v, peak) > 0) { peak = v; trail(peak); }
    }
    var room = breached ? Dec.ZERO : Dec.max(Dec.ZERO, Dec.sub(equity, floor));
    return { floor: rFloorLevel(floor), peak: rNear(peak), locked: locked, breached: breached,
      equity: rDown(equity), drawdown_room: rDown(room) };
  }

  // Signed daily capacity. >0 OK (dll_rule or dll_boundary may still be unconfirmed).
  // ==0 is BREACHED only for confirmed hard + reach. Soft never breaches, so soft + reach is
  // DAILY LIMIT REACHED. Confirmed exceed at exactly 0 is DAILY LIMIT REACHED.
  // Either classification omitted at exactly 0 is RULE CONFIRMATION REQUIRED.
  // <0 ignores boundary: BREACHED only when dll_enforcement is hard, DAILY LIMIT EXCEEDED when
  // soft, RULE CONFIRMATION REQUIRED when omitted. Omitted enforcement is not soft and not hard.
  // Capacity is ROUND_FLOOR to the cent. binding_room is max(0, capacity).
  // A drawdown-floor breach is drawdown(), not this function. accountStatus applies floor first.
  function riskRoom(inp) {
    var ddRoom = dec(need(inp, "drawdown_room"), "drawdown_room", { nonneg: true });
    var dl = get(inp, "daily_loss_limit");
    if (dl === null) return { drawdown_room: rDown(ddRoom), daily_room: null, binding_room: rDown(ddRoom), binding: "drawdown", daily_status: null, dll_rule: null, dll_boundary: null };
    dl = dec(dl, "daily_loss_limit", { positive: true });
    var dayPnl = dec(need(inp, "day_pnl"), "day_pnl");
    var enf = dllEnforcement(inp);
    var boundary = dllBoundary(inp);
    var raw = Dec.sub(dl, Dec.max(Dec.ZERO, Dec.neg(dayPnl)));
    var dQ = Dec.quantize(raw, CENT, "FLOOR");
    var sized = Dec.max(Dec.ZERO, dQ);
    var roomStr = Dec.isZero(dQ) ? "0.00" : Dec.toFixed(dQ);
    return { drawdown_room: rDown(ddRoom), daily_room: roomStr, binding_room: rDown(Dec.min(ddRoom, sized)),
      binding: Dec.cmp(dQ, ddRoom) < 0 ? "daily_loss" : "drawdown", daily_status: dailyStatus(dQ, enf, boundary),
      dll_rule: dllRule(enf), dll_boundary: boundaryRule(boundary) };
  }

  function effRisk(inp) {
    var risk = dec(need(inp, "risk"), "risk", { nonneg: true });
    var room = dec(need(inp, "binding_room"), "binding_room", { nonneg: true });
    return [Dec.min(risk, room), Dec.cmp(risk, room) > 0];
  }

  // OLD single-cap: caller supplies tick_value and one optional max_contracts.
  // NEW (instrument present): tick is derived. ES/NQ use max_minis; micros use max_micros.
  // NONE removes only the contract cap. Explicit 0 stays 0. A disagreeing tick_value is a mismatch.
  var TICKS = { ES: "12.50", MES: "1.25", NQ: "5.00", MNQ: "0.50", GC: "10.00", MGC: "1.00", CL: "10.00", MCL: "1.00", "6E": "6.25", M6E: "1.25" };
  var MICROS = { MES: 1, MNQ: 1, MGC: 1, MCL: 1, M6E: 1 };
  function capToken(v, name) {
    if (v === null || v === undefined) bad("missing " + name);
    if (typeof v === "string" && v.trim().toLowerCase() === "none") return null;
    return Dec.toNumber(Dec.toIntegral(dec(v, name, { nonneg: true, integer: true }), "DOWN"));
  }
  function sizeFuturesLegacy(inp) {
    var r = effRisk(inp), risk = r[0];
    var ticks = dec(need(inp, "stop_ticks"), "stop_ticks", { positive: true, integer: true });
    var tv = dec(need(inp, "tick_value"), "tick_value", { positive: true });
    var mc = get(inp, "max_contracts");
    if (mc !== null) mc = Dec.toNumber(Dec.toIntegral(dec(mc, "max_contracts", { nonneg: true, integer: true }), "DOWN"));
    var per = Dec.mul(ticks, tv);
    var n = Dec.toNumber(Dec.toIntegral(Dec.div(risk, per), "FLOOR"));
    var capped = mc !== null && n > mc;
    if (capped) n = mc;
    return { effective_risk: rDown(risk), risk_limited_by_room: r[1], risk_per_contract: Dec.toFixed(per),
      contracts: n, capped: capped, actual_risk: rDown(Dec.mul(per, Dec.fromInt(n))) };
  }
  function sizeFuturesInstrument(inp) {
    var raw = need(inp, "instrument");
    if (typeof raw !== "string" || raw.trim() === "") bad("missing instrument");
    var sym = raw.trim().toUpperCase();
    if (!has(TICKS, sym)) bad("invalid instrument");
    var tv = dec(TICKS[sym], "tick_value", { positive: true });
    if (has(inp, "tick_value") && inp.tick_value !== null) {
      var given = dec(inp.tick_value, "tick_value", { positive: true });
      if (Dec.cmp(given, tv) !== 0) bad("tick_value mismatch");
    }
    var klass = MICROS[sym] ? "micro" : "mini";
    var key = klass === "micro" ? "max_micros" : "max_minis";
    var other = key === "max_micros" ? "max_minis" : "max_micros";
    if (has(inp, other) && inp[other] !== null) capToken(inp[other], other);
    if (!has(inp, key)) bad("missing " + key);
    var cap = capToken(inp[key], key);
    var legacy = { risk: need(inp, "risk"), binding_room: need(inp, "binding_room"), stop_ticks: need(inp, "stop_ticks"), tick_value: TICKS[sym] };
    if (cap !== null) legacy.max_contracts = String(cap);
    var out = sizeFuturesLegacy(legacy);
    out.instrument = sym;
    out.tick_value = TICKS[sym];
    out.cap_class = klass;
    out.active_cap = cap === null ? "NONE" : cap;
    return out;
  }
  function sizeFutures(inp) {
    if (isDict(inp) && has(inp, "instrument")) return sizeFuturesInstrument(inp);
    return sizeFuturesLegacy(inp);
  }

  function sizeCrypto(inp) {
    var r = effRisk(inp), risk = r[0];
    var e = dec(need(inp, "entry"), "entry", { positive: true });
    var s = dec(need(inp, "stop"), "stop", { positive: true });
    var step = dec(need(inp, "step_size"), "step_size", { positive: true });
    if (Dec.cmp(e, s) === 0) bad("entry == stop");
    var dist = Dec.abs(Dec.sub(e, s));
    var q = Dec.mul(Dec.toIntegral(Dec.div(Dec.div(risk, dist), step), "FLOOR"), step);
    q = Dec.quantize(q, step.e, "FLOOR");
    return { effective_risk: rDown(risk), risk_limited_by_room: r[1], side: Dec.cmp(s, e) < 0 ? "long" : "short",
      qty: Dec.toFixed(q), actual_risk: rDown(Dec.mul(q, dist)) };
  }

  var FUNCS = { drawdown: drawdown, risk_room: riskRoom, futures: sizeFutures, crypto: sizeCrypto };

  function evaluate(kind, inp) {
    try {
      if (!has(FUNCS, kind)) bad("unknown kind");
      var out = FUNCS[kind](inp), res = { ok: true };
      Object.keys(out).forEach(function (k) { res[k] = out[k]; });
      return res;
    } catch (e) {
      if (e && e.specCode) return { ok: false, error: e.specCode, message: e.message };
      if (e && e.decimalInvalidOperation) return { ok: false, error: "INVALID_INPUT", message: "malformed input: InvalidOperation" };
      return { ok: false, error: "INVALID_INPUT", message: "malformed input: " + ((e && e.name) || "Error") };
    }
  }
  var api = { evaluate: evaluate, accountStatus: accountStatus, SPEC_VERSION: "0.2.0", TICKS: TICKS, MICROS: MICROS };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Oracle = api;
})(this);
