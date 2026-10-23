/* Floorline UI. All arithmetic goes through Oracle (Decimal port of golden/oracle.py); UI only formats. */
(function () {
  "use strict";
  var DATA = window.PDC_DATA, P = DATA.presets.presets, C = DATA.contracts.contracts;
  var $ = function (id) { return document.getElementById(id); };
  var RM = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var MICRO = { MES: 1, MNQ: 1, MGC: 1, MCL: 1, M6E: 1 };
  var CUSTOM = "__custom";
  var state = { preset: null, custom: false };

  // ---------- decimal helpers (display + exact rule derivations only) ----------
  function D(s) { var d = Dec.parse(s); if (d.special) throw new Error("nf"); return d; }
  function isNum(s) { if (s == null || String(s).trim() === "") return false; try { D(s); return true; } catch (e) { return false; } }
  function pctOf(pct, base) { return Dec.toFixed(Dec.div(Dec.mul(D(pct), D(base)), D("100"))); }
  function money(s, sign) {
    if (s == null) return "—";
    var neg = s.charAt(0) === "-"; if (neg) s = s.slice(1);
    var p = s.split("."), i = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return (neg ? "−" : sign && s !== "0.00" ? "+" : "") + "$" + i + (p[1] ? "." + p[1] : "");
  }
  function v(id) { return $(id).value.trim(); }

  // ---------- selects ----------
  var firms = []; P.forEach(function (p) { if (firms.indexOf(p.firm) < 0) firms.push(p.firm); });
  function opt(sel, items) { sel.innerHTML = items.map(function (i) { return '<option value="' + esc(i[0]) + '">' + esc(i[1]) + "</option>"; }).join(""); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  opt($("firm"), firms.map(function (f) { return [f, f]; }).concat([[CUSTOM, "Custom rule"]]));
  opt($("inst"), C.map(function (c) { return [c.symbol, c.symbol + " · " + c.name]; }).concat([["CRYPTO", "Crypto perp (qty)"]]));

  // ---------- firm logos (assets/logos/SOURCES.md); null = neutral text wordmark ----------
  var LOGOS = { "Topstep": "topstep.png", "Tradeify": "tradeify.svg", "Take Profit Trader": "takeprofittrader.svg",
    "Breakout": "breakout.svg", "Vest (Vest Capital)": "vest.svg", "MyFundedFutures": "myfundedfutures.png",
    "Apex Trader Funding": null, "Lucid Trading": null, "MyFundedPerps": null };
  var SHORT = { "Apex Trader Funding": "Apex", "Lucid Trading": "Lucid", "Vest (Vest Capital)": "Vest", "Take Profit Trader": "TPT", "MyFundedFutures": "MFFU", "MyFundedPerps": "MFPerps" };
  function mark(f, cls) {
    var file = LOGOS[f];
    // icon-only official marks get the short name beside them so the firm stays identifiable
    if (file) return '<span class="mk2"><img class="' + cls + '" src="assets/logos/' + file + '" alt="" loading="lazy" decoding="async">' +
      (f === "MyFundedFutures" ? '<span class="wm ' + cls + '">MFFU</span>' : "") + "</span>";
    return '<span class="wm ' + cls + '">' + esc(SHORT[f] || f) + "</span>";
  }
  function chips() {
    var all = firms.concat([CUSTOM]), cur = v("firm");
    $("firmChips").innerHTML = all.map(function (f) {
      var on = f === cur, label = f === CUSTOM ? "Custom rule" : f;
      return '<button type="button" role="radio" class="chip' + (on ? " on" : "") + '" aria-checked="' + on + '" tabindex="' + (on ? 0 : -1) +
        '" data-firm="' + esc(f) + '" title="' + esc(label) + '">' + (f === CUSTOM ? '<span class="wm lg">CUSTOM</span>' : mark(f, "lg")) +
        '<span class="sr">' + esc(label) + "</span></button>";
    }).join("");
  }
  function pickFirm(f, focus) {
    $("firm").value = f; fillPlans(); chips();
    if (focus) { var b = document.querySelector('.chip[data-firm="' + f.replace(/"/g, '\\"') + '"]'); if (b) b.focus(); }
  }
  $("firmChips").addEventListener("click", function (e) { var b = e.target.closest(".chip"); if (b) pickFirm(b.getAttribute("data-firm")); });
  $("firmChips").addEventListener("keydown", function (e) {
    var keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
    if (!keys[e.key] && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    var all = firms.concat([CUSTOM]), i = all.indexOf(v("firm"));
    i = e.key === "Home" ? 0 : e.key === "End" ? all.length - 1 : (i + keys[e.key] + all.length) % all.length;
    pickFirm(all[i], true);
  });
  $("logoStrip").innerHTML = firms.map(function (f) { return '<span class="si" title="' + esc(f) + '">' + mark(f, "sm") + '<span class="sr">' + esc(f) + "</span></span>"; }).join("");
  var CFG = window.FLOORLINE_CONFIG || {};
  if (CFG.TRACKER_URL) { $("trackerLink").href = CFG.TRACKER_URL; $("trackerCta").hidden = false; }

  function fillPlans() {
    var f = v("firm"), plans = [];
    P.forEach(function (p) { if (p.firm === f && plans.indexOf(p.plan) < 0) plans.push(p.plan); });
    opt($("plan"), plans.map(function (x) { return [x, x]; }));
    $("plan").disabled = f === CUSTOM; fillSizes();
  }
  function fillSizes() {
    var rows = P.filter(function (p) { return p.firm === v("firm") && p.plan === v("plan"); });
    opt($("size"), rows.map(function (p) { return [p.id, p.account_size ? money(p.account_size).replace(".00", "") : "Any size"]; }));
    $("size").disabled = !rows.length; applyPreset();
  }

  // ---------- rule fields ----------
  var FIELDS = ["type", "dd", "lock", "dll", "dllpct", "dllbasis", "cap", "touch"];
  function field(f) { return document.querySelector('[data-f="' + f + '"]'); }
  function setEditable(f, on, flagged) {
    var el = field(f), inp = el.querySelector("input,select");
    inp.disabled = !on; el.classList.toggle("flag", !!flagged);
    var tag = el.querySelector(".flagtag");
    if (flagged && !tag) { tag = document.createElement("em"); tag.className = "flagtag"; tag.textContent = "not stated by firm"; el.insertBefore(tag, el.firstChild.nextSibling); }
    if (!flagged && tag) tag.remove();
  }

  function applyPreset() {
    var p = P.filter(function (x) { return x.id === v("size"); })[0] || null;
    state.preset = p; state.custom = v("firm") === CUSTOM || (p && p.status === "custom_only");
    var note = $("ruleNote"); note.hidden = true;
    var sn = $("srcNote"); sn.hidden = !(p && p.note && p.status !== "custom_only"); if (p) sn.querySelector("p").textContent = p.note;
    if (!p) {
      $("presetMeta").innerHTML = '<span class="badge custom">Custom</span><span>Enter every rule field from your firm dashboard.</span>';
    } else {
      $("presetMeta").innerHTML = '<span class="badge ' + p.status + '">' + p.status.replace("_", " ") + "</span>" +
        '<a href="' + esc(p.source_url) + '" target="_blank" rel="noopener noreferrer">source</a>' +
        "<span>checked " + esc(p.checked_date) + "</span>" + (p.source_page_date ? "<span>page dated " + esc(p.source_page_date) + "</span>" : "");
      if (p.status === "custom_only") { note.hidden = false; note.textContent = "This plan can't be preset faithfully, so it opens in Custom. " + p.note; }
      note.className = "note";
    }
    // populate
    FIELDS.forEach(function (f) { setEditable(f, true, false); });
    field("dllpct").hidden = true; field("dllbasis").hidden = true;
    if (p && p.status !== "custom_only") {
      var start = p.account_size || v("start") || "";
      if (p.account_size) $("start").value = p.account_size;
      $("ddType").value = p.drawdown.type;
      $("ddAmt").value = p.drawdown.amount_usd || "";
      $("lockOff").value = p.lock.kind === "offset" ? p.lock.offset_usd : "";
      $("touch").checked = p.breach_on_touch !== false;
      var dl = p.daily_loss;
      $("dll").value = dl.kind === "fixed_usd" ? dl.amount_usd : "";
      if (dl.kind === "pct_choice") {
        opt($("dllPct"), (dl.optional ? [["", "Not selected"]] : []).concat(dl.pct.map(function (x) { return [x, x + "%"]; })));
        $("dllPct").value = dl.pct[0]; field("dllpct").hidden = false;
      } else if (dl.kind === "pct" || dl.kind === "pct_of_start") {
        opt($("dllPct"), [[dl.pct, dl.pct + "%"]]); field("dllpct").hidden = false;
      }
      if (dl.kind === "pct" || dl.kind === "pct_choice") { field("dllbasis").hidden = false; if (!v("dllBasis")) $("dllBasis").value = start; }
      $("cap").value = "";
      var lockUn = p.lock.kind === "unstated", dllUn = dl.kind === "unstated", touchUn = p.breach_on_touch === null;
      FIELDS.forEach(function (f) { setEditable(f, false, false); });
      setEditable("lock", lockUn, lockUn);
      setEditable("dll", dllUn, dllUn);
      setEditable("touch", touchUn, touchUn);
      setEditable("dllpct", dl.kind === "pct_choice", false);
      setEditable("dllbasis", true, false);
      setEditable("cap", true, false); // instrument cap derived below; user may tighten
      field("dll").hidden = dl.kind !== "fixed_usd" && dl.kind !== "unstated" && dl.kind !== "none";
      if (dl.kind === "none") { $("dll").value = ""; }
      if (dl.kind === "fixed_usd" && dl.optional) field("dll").querySelector("small").textContent = "optional at checkout · blank = not selected";
      else field("dll").querySelector("small").textContent = "blank = none";
      if (dl.kind === "fixed_usd" && dl.optional) setEditable("dll", true, false);
      if (!p.drawdown.amount_usd && p.drawdown.pct_of_start) {
        field("dd").querySelector("small") || field("dd").insertAdjacentHTML("beforeend", "");
      }
      $("toCustom").hidden = false;
    } else {
      field("dll").hidden = false; field("dll").querySelector("small").textContent = "blank = none";
      $("toCustom").hidden = true;
      if (p && p.status === "custom_only") { // never inherit another preset's numbers
        ["ddAmt", "lockOff", "dll", "cap"].forEach(function (id) { $(id).value = ""; }); $("touch").checked = true;
      }
    }
    deriveCap(); run(true);
  }

  // Effective drawdown $ (exact) for pct_of_start presets.
  function ddAmount() {
    var p = state.preset;
    if (!state.custom && p && !p.drawdown.amount_usd && p.drawdown.pct_of_start && isNum(v("start"))) {
      var a = pctOf(p.drawdown.pct_of_start, v("start")); $("ddAmt").value = a; return a;
    }
    return v("ddAmt");
  }
  function dllAmount() {
    var p = state.preset, dl = p && !state.custom ? p.daily_loss : null;
    if (dl && (dl.kind === "pct" || dl.kind === "pct_of_start" || dl.kind === "pct_choice")) {
      var r = v("dllPct"); if (!r) return "";
      var base = dl.kind === "pct_of_start" ? v("start") : v("dllBasis");
      return isNum(base) ? pctOf(r, base) : "?";
    }
    return v("dll");
  }

  // Instrument cap: ES/NQ and other minis use max minis; MES/MNQ and other micros use max micros.
  // A generic contract count, and only that, applies to every instrument. Blank is incomplete.
  // NONE is the only unrestricted contract cap. 0 stays 0. Risk, drawdown and daily loss stay active.
  var capInfo = "";
  function capClass(sym) { return MICRO[sym] ? "micro" : "mini"; }
  function deriveCap() {
    var p = state.preset, sym = v("inst"); capInfo = "";
    if (sym === "CRYPTO") { field("cap").classList.remove("flag"); return; }
    if (!p || state.custom || p.status === "custom_only") {
      capInfo = v("cap") === "" ? "enter a number, 0, or NONE" : "";
      field("cap").classList.toggle("flag", v("cap") === "");
      return;
    }
    var m = p.max_contracts, cap = null;
    if (MICRO[sym] && m.micros) { cap = m.micros; capInfo = "firm micro cap " + m.micros; }
    else if (!MICRO[sym] && m.minis) { cap = m.minis; capInfo = "firm mini cap " + m.minis; }
    else if (!m.minis && !m.micros && m.contracts) { cap = m.contracts; capInfo = "firm cap " + m.contracts + " (generic count, this instrument)"; }
    else capInfo = "firm " + capClass(sym) + " cap not stated";
    $("cap").value = cap == null ? "" : String(cap);
    field("cap").classList.toggle("flag", cap == null);
  }

  function toCustom() {
    $("firm").value = CUSTOM; chips(); var keep = { t: v("ddType"), a: v("ddAmt"), l: v("lockOff"), d: dllAmount(), c: v("cap"), touch: $("touch").checked };
    fillPlans(); $("ddType").value = keep.t; $("ddAmt").value = keep.a; $("lockOff").value = keep.l;
    $("dll").value = keep.d === "?" ? "" : keep.d; $("cap").value = keep.c; $("touch").checked = keep.touch; run();
  }

  // ---------- compute ----------
  function events(type, bal, peak) {
    var ev = [];
    if (type === "eod_trailing" && peak) ev.push({ kind: "eod", balance: peak });
    if (type === "intraday_trailing" && peak) ev.push({ kind: "mark", equity: peak });
    ev.push({ kind: "mark", equity: bal });
    return ev;
  }

  var shown = {}, ready = false;
  function run(fromPreset) {
    var type = v("ddType"), sym = v("inst"), crypto = sym === "CRYPTO";
    $("peakLbl").textContent = type === "eod_trailing" ? "Highest EOD close $" : type === "intraday_trailing" ? "Peak equity (intraday) $" : "Peak (unused for static) $";
    $("peak").disabled = type === "static";
    Array.prototype.forEach.call(document.querySelectorAll("[data-cry]"), function (e) { e.hidden = !crypto; });
    Array.prototype.forEach.call(document.querySelectorAll("[data-fut]"), function (e) { e.hidden = crypto; });
    field("cap").hidden = crypto;
    var ci = C.filter(function (c) { return c.symbol === sym; })[0];
    var spec = !ci ? "" : ci.status === "flagged" ? "flagged" : ci.status === "verified" ? "verified on the CME rulebook" : "verified indirectly";
    $("instNote").innerHTML = ci ? esc(ci.symbol) + ": tick " + esc(ci.tick_size) + " = $" + esc(ci.tick_value_usd) +
      ' · <span class="ind">' + spec + '</span> (<a href="' + esc(ci.source_url) +
      '" target="_blank" rel="noopener noreferrer">source</a>, ' + esc(ci.checked_date) + ")." +
      (ci.status === "verified" ? "" : " Confirm on cmegroup.com.") + (capInfo ? " · " + esc(capInfo) : "")
      : "Crypto perp: quantity floored to your exchange's step. Fees, slippage, leverage and margin not modeled.";

    var err = null, out = {};
    var dd = ddAmount(), dllS = dllAmount();
    var start = v("start"), bal = v("bal"), peak = type === "static" ? "" : v("peak");
    var ddIn = { type: type, start_balance: start, drawdown_amount: dd, breach_on_touch: $("touch").checked, events: events(type, bal, peak) };
    if (type !== "static" && v("lockOff") !== "") ddIn.lock_offset = v("lockOff");
    if (!start || !bal || !dd) err = { error: "INCOMPLETE", message: "Enter start balance, current balance and max drawdown." };
    if (dllS === "?") err = { error: "INCOMPLETE", message: "Enter the balance at the last daily reset to convert the % daily loss limit." };
    var r1 = err ? null : Oracle.evaluate("drawdown", ddIn);
    if (r1 && !r1.ok) err = r1;
    var r2 = null, r3 = null, quick = [];
    if (!err) {
      var rr = { drawdown_room: r1.drawdown_room };
      if (dllS) { rr.daily_loss_limit = dllS; rr.day_pnl = v("pnl") || "0"; }
      r2 = Oracle.evaluate("risk_room", rr); if (!r2.ok) err = r2;
    }
    if (!err) {
      if (crypto) {
        r3 = Oracle.evaluate("crypto", { risk: v("risk") || "0", binding_room: r2.binding_room, entry: v("entry"), stop: v("stopPx"), step_size: v("step") });
      } else if (!ci) {
        err = { error: "INVALID", message: "Unknown instrument." };
      } else if (v("cap") === "") {
        err = { error: "INCOMPLETE", message: "Enter the max contracts for this instrument, or NONE for no contract cap. 0 means zero contracts. Risk, drawdown and the daily loss limit still apply." };
      } else {
        var base = { risk: v("risk") || "0", binding_room: r2.binding_room, instrument: sym };
        base[MICRO[sym] ? "max_micros" : "max_minis"] = /^none$/i.test(v("cap")) ? "NONE" : v("cap");
        r3 = Oracle.evaluate("futures", Object.assign({ stop_ticks: v("ticks") }, base));
        var t0 = parseInt(v("ticks"), 10) || 8;
        var stops = [Math.max(1, Math.round(t0 / 2)), t0, t0 * 2, t0 * 3, t0 * 4].filter(function (x, i, a) { return a.indexOf(x) === i; });
        quick = stops.map(function (t) { return [t, Oracle.evaluate("futures", Object.assign({ stop_ticks: String(t) }, base))]; });
      }
    }
    render(r1, r2, r3, quick, err, crypto, ci, dllS, fromPreset);
  }

  // ---------- render ----------
  function tween(el, target, key) {
    var to = parseFloat(String(target).replace(/,/g, "")), from = shown[key];
    shown[key] = to;
    if (RM || !ready || from == null || !isFinite(from) || !isFinite(to) || from === to) { el.textContent = money(target); return; }
    var t0 = performance.now(), dur = 420;
    el.classList.remove("tick"); void el.offsetWidth; el.classList.add("tick");
    (function step(now) {
      var k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      if (k < 1) { el.textContent = money((from + (to - from) * e).toFixed(2)); requestAnimationFrame(step); }
      else el.textContent = money(target); // exact final value from the oracle
    })(t0);
  }

  function render(r1, r2, r3, quick, err, crypto, ci, dllS) {
    var out = document.querySelector(".out");
    $("err").hidden = !err;
    if (err) {
      $("err").innerHTML = "<b>" + esc(err.error.replace(/_/g, " ")) + "</b> " + esc(err.message) + (err.error !== "INCOMPLETE" ? " · sizing is 0 until fixed." : "");
    }
    var level = "none";
    if (r1 && r1.ok) {
      tween($("floor"), r1.floor, "floor");
      var type = v("ddType"), lb = $("lockBadge");
      if (r1.breached) { lb.textContent = "BREACHED"; lb.className = "pill red"; }
      else if (r1.locked) { lb.textContent = "LOCKED"; lb.className = "pill lock"; }
      else if (type === "static") { lb.textContent = "STATIC"; lb.className = "pill"; }
      else if (v("lockOff") !== "") { lb.textContent = "TRAILING · locks at " + money(Dec.toFixed(Dec.add(D(v("start")), D(v("lockOff"))))); lb.className = "pill"; }
      else { lb.textContent = "TRAILING · no lock"; lb.className = "pill"; }
    } else { $("floor").textContent = "—"; shown.floor = null; $("lockBadge").textContent = ""; $("lockBadge").className = "pill"; }
    if (r2 && r2.ok) {
      $("ddRoom").textContent = money(r2.drawdown_room);
      $("dRoom").textContent = r2.daily_room == null ? (field("dll").classList.contains("flag") ? "not entered" : "no DLL") : money(r2.daily_room);
      tween($("bRoom"), r2.binding_room, "broom");
      $("bindBy").textContent = r2.binding === "daily_loss" ? "daily loss" : "drawdown";
      var ratio = parseFloat(r2.binding_room) / parseFloat(v("ddAmt") || "1");
      level = r1.breached || ratio <= 0.25 ? "red" : ratio <= 0.5 ? "amber" : "green";
    } else { ["ddRoom", "dRoom", "bRoom"].forEach(function (i) { $(i).textContent = "—"; }); $("bindBy").textContent = ""; shown.broom = null; }
    out.setAttribute("data-level", err && err.error !== "INCOMPLETE" ? "red" : level);

    // size
    var flags = [];
    if (r3 && r3.ok) {
      if (crypto) {
        $("sizeLbl").textContent = "Max quantity · " + r3.side; $("contracts").textContent = r3.qty;
        $("sizeDetail").innerHTML = "risk used <b>" + money(r3.actual_risk) + "</b> of " + money(r3.effective_risk);
      } else {
        $("sizeLbl").textContent = "Max contracts · " + ci.symbol; $("contracts").textContent = r3.contracts;
        $("sizeDetail").innerHTML = money(r3.risk_per_contract) + " / contract<br>risk used <b>" + money(r3.actual_risk) + "</b>";
        if (r3.capped) flags.push(["CAPPED", "firm max contracts reached"]);
      }
      if (r3.risk_limited_by_room) flags.push(["CLAMPED", "risk cut to binding room " + money(r2.binding_room)]);
    } else {
      $("contracts").textContent = err && err.error !== "INCOMPLETE" ? "0" : r3 && !r3.ok ? "0" : "—";
      $("sizeDetail").textContent = r3 && !r3.ok ? r3.message : "";
    }
    if (r1 && r1.ok && r1.breached) flags.unshift(["BREACHED", "account is past the floor"]);
    $("flags").innerHTML = flags.map(function (f) { return '<span class="flagchip"><b>' + f[0] + "</b> " + esc(f[1]) + "</span>"; }).join("");

    var tb = $("quick").querySelector("tbody");
    $("quick").hidden = crypto || !quick.length;
    $("quickCap").textContent = ci ? ci.symbol + " contracts at your risk, by stop" : "";
    tb.innerHTML = quick.map(function (q) {
      var r = q[1], cur = String(q[0]) === v("ticks");
      return "<tr" + (cur ? ' class="cur"' : "") + "><td>" + q[0] + " t</td><td>" + (r.ok ? money(r.risk_per_contract) : "—") + "</td><td>" + (r.ok ? r.contracts + (r.capped ? "<sup>cap</sup>" : "") : "0") + "</td><td>" + (r.ok ? money(r.actual_risk) : "—") + "</td></tr>";
    }).join("");

    gauge(r1, r2, level);
  }

  function gauge(r1, r2, level) {
    var g = $("gauge");
    if (!(r1 && r1.ok && r2 && r2.ok)) { g.classList.add("off"); return; }
    g.classList.remove("off");
    var f = +r1.floor, eq = +r1.equity, pk = +r1.peak, st = +v("start");
    var lock = v("ddType") !== "static" && v("lockOff") !== "" ? st + +v("lockOff") : null;
    var dllFloor = r2.daily_room != null ? eq - +r2.daily_room : null;
    var lo = Math.min(f, eq, dllFloor == null ? f : dllFloor), hi = Math.max(pk, eq, st, lock || 0);
    var pad = (hi - lo) * 0.08 || 100; lo -= pad; hi += pad;
    var x = function (n) { return ((n - lo) / (hi - lo) * 100).toFixed(3) + "%"; };
    $("gFloor").style.left = x(f); $("gEq").style.left = x(Math.max(eq, lo));
    $("gStart").style.left = x(st); $("gStart").hidden = lock != null && Math.abs(lock - st) < (hi - lo) * 0.03; $("gPeak").style.left = x(pk);
    $("gPeak").hidden = v("ddType") === "static" || Math.abs(pk - st) < (hi - lo) * 0.02;
    $("gLock").hidden = lock == null; if (lock != null) $("gLock").style.left = x(lock);
    $("gDll").hidden = dllFloor == null || dllFloor <= f; if (dllFloor != null) $("gDll").style.left = x(dllFloor);
    var a = Math.min(f, eq), b = Math.max(f, eq);
    $("gFill").style.left = x(a); $("gFill").style.width = ((b - a) / (hi - lo) * 100).toFixed(3) + "%";
    g.querySelector(".danger").style.width = x(f);
  }

  // ---------- wire ----------
  $("firm").addEventListener("change", function () { fillPlans(); chips(); });
  $("plan").addEventListener("change", fillSizes);
  $("size").addEventListener("change", applyPreset);
  $("toCustom").addEventListener("click", toCustom);
  $("inst").addEventListener("change", function () { deriveCap(); run(); });
  document.querySelector("main").addEventListener("input", function (e) { if (e.target.tagName === "INPUT") run(); });
  ["ddType", "dllPct"].forEach(function (id) { $(id).addEventListener("change", function () { run(); }); });
  $("start").addEventListener("input", function () { if (state.preset && !state.custom) { var dl = state.preset.daily_loss; if (dl.kind === "pct" || dl.kind === "pct_choice") {} } });

  // example starting state (illustrative inputs, not a firm rule)
  $("bal").value = "51240.50"; $("peak").value = "51800"; $("pnl").value = "-310"; $("risk").value = "300"; $("ticks").value = "12";
  $("entry").value = "65000"; $("stopPx").value = "64350"; $("step").value = "0.001"; $("inst").value = "MES";
  var h = /^#(P\d{3})$/.exec(location.hash), hp = h && P.filter(function (x) { return x.id === h[1]; })[0];
  if (hp) { $("firm").value = hp.firm; fillPlans(); $("plan").value = hp.plan; fillSizes(); $("size").value = hp.id; applyPreset(); }
  else if (location.hash === "#custom") { $("firm").value = CUSTOM; fillPlans(); }
  else fillPlans();
  chips();
  ready = true;
})();
