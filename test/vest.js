// Vest proposal checks plus frozen results for the account types that already shipped.
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const Dec = require("../js/decimal.js");

const LEGACY_HASH = "d8234d2826af6f774f72ee7a4d660befe16d9bd51e256c8c4f1c5922259d7bec";
const SIZES = [
  ["5000", "300", "4700.00", "500", "250", "150.00", "200.00"],
  ["10000", "600", "9400.00", "1000", "500", "300.00", "400.00"],
  ["25000", "1500", "23500.00", "2500", "1250", "750.00", "1000.00"],
  ["50000", "3000", "47000.00", "5000", "2500", "1500.00", "2000.00"]
];

function canon(v) {
  return Array.isArray(v) ? v.map(canon) : (v && typeof v === "object")
    ? Object.fromEntries(Object.keys(v).sort().map(k => [k, canon(v[k])])) : v;
}
function pctOf(pct, base) {
  return Dec.toFixed(Dec.div(Dec.mul(Dec.parse(pct), Dec.parse(base)), Dec.parse("100")));
}
function same(got, exp) {
  return JSON.stringify(canon(got)) === JSON.stringify(canon(exp));
}

function run(presets, Oracle) {
  let fail = 0, n = 0;
  function check(name, ok, detail) {
    n++;
    if (!ok) { fail++; console.log("VEST FAIL", name, detail === undefined ? "" : detail); }
  }
  const byId = Object.fromEntries(presets.presets.map(p => [p.id, p]));
  const legacy = [];
  for (let i = 1; i <= 55; i++) {
    const id = "P" + String(i).padStart(3, "0");
    check("legacy id " + id, !!byId[id]);
    if (byId[id]) legacy.push(byId[id]);
  }
  const hash = crypto.createHash("sha256").update(JSON.stringify(canon(legacy))).digest("hex");
  check("P001-P055 canonical hash", hash === LEGACY_HASH, hash);

  const legacyCases = JSON.parse(fs.readFileSync(path.join(__dirname, "legacy-oracle.json"), "utf8"));
  for (const c of legacyCases) {
    const got = Oracle.evaluate(c.kind, c.input);
    check("legacy " + c.name, same(got, c.expected), JSON.stringify(got));
  }
  check("legacy oracle case count", legacyCases.length === 17, legacyCases.length);

  // Existing Vest rows stay the pre-proposal plans.
  check("P031 plan", byId.P031.plan === "Evaluation" && byId.P031.breach_on_touch === false && byId.P031.drawdown.amount_usd === "300");
  check("P033 still 25000", byId.P033.account_size === "25000" && byId.P033.drawdown.amount_usd === "1500");
  const oldInstant = ["P027", "P028", "P029", "P030"].map(id => byId[id].account_size);
  check("old instant sizes", JSON.stringify(oldInstant) === JSON.stringify(["500", "5000", "10000", "25000"]));
  const oldEvalSizes = presets.presets.filter(p => p.plan === "Evaluation").map(p => p.account_size);
  check("old Evaluation has no 50000", JSON.stringify(oldEvalSizes) === JSON.stringify(["5000", "10000", "25000"]));

  function expectRow(id, plan, size, amount, dllKind) {
    const p = byId[id];
    check(id + " exists", !!p);
    if (!p) return;
    check(id + " plan/size", p.firm === "Vest (Vest Capital)" && p.plan === plan && p.account_size === size && p.status === "partial");
    check(id + " static floor", p.drawdown.type === "static" && p.drawdown.amount_usd === amount && p.lock.kind === "none" && p.lock.offset_usd === null);
    check(id + " touch unset", p.breach_on_touch === null && p.breach_on_touch_after_lock === null);
    check(id + " no contract cap", p.max_contracts.minis === null && p.max_contracts.micros === null && p.max_contracts.contracts === null);
    check(id + " dll kind", p.daily_loss.kind === dllKind);
    if (dllKind === "pct_choice") {
      check(id + " dll menu", JSON.stringify(p.daily_loss.pct) === JSON.stringify(["3", "4"]) && p.daily_loss.optional === true && p.daily_loss.enforcement === "hard" && p.daily_loss.boundary === "exceed");
    } else if (dllKind === "pct") {
      check(id + " dll fixed 3", p.daily_loss.pct === "3" && p.daily_loss.optional === false && p.daily_loss.enforcement === "hard" && p.daily_loss.boundary === "exceed");
    } else {
      check(id + " no dll fields", p.daily_loss.pct === null && p.daily_loss.enforcement === null && p.daily_loss.boundary === null);
    }
  }

  SIZES.forEach((row, i) => {
    const [size, amount, floor, p1, p2, dll3] = row;
    expectRow("P" + String(56 + i).padStart(3, "0"), "1-Step Evaluation", size, amount, "pct_choice");
    expectRow("P" + String(60 + i).padStart(3, "0"), "2-Step Phase 1", size, amount, "pct");
    expectRow("P" + String(64 + i).padStart(3, "0"), "2-Step Phase 2", size, amount, "pct");
    expectRow("P" + String(68 + i).padStart(3, "0"), "Funded after 1-Step", size, amount, "pct_choice");
    expectRow("P" + String(72 + i).padStart(3, "0"), "Funded after 2-Step", size, amount, "pct");
    const phase1 = byId["P" + String(60 + i).padStart(3, "0")];
    const phase2 = byId["P" + String(64 + i).padStart(3, "0")];
    check(size + " phase targets differ", phase1 && phase2 && phase1.note.includes("$" + Number(p1).toLocaleString("en-US")) && phase2.note.includes("$" + Number(p2).toLocaleString("en-US")) && phase1.drawdown.amount_usd === phase2.drawdown.amount_usd);
    check(size + " phase 2 keeps original size", phase2 && phase2.account_size === size && phase2.note.includes("original size"));
    check(size + " 3% converts exactly", pctOf("3", size) === String(Number(dll3)));

    const high = Oracle.evaluate("drawdown", { type: "static", start_balance: size, drawdown_amount: amount, breach_on_touch: false, events: [{ kind: "mark", equity: String(Number(size) + Number(amount)) }] });
    check(size + " static ignores profit", high.ok && high.floor === floor && high.locked === false && high.breached === false && high.peak === Number(size).toFixed(2));
    const atFloor = String(Number(floor));
    const equalOff = Oracle.evaluate("drawdown", { type: "static", start_balance: size, drawdown_amount: amount, breach_on_touch: false, events: [{ kind: "mark", equity: atFloor }] });
    const equalOn = Oracle.evaluate("drawdown", { type: "static", start_balance: size, drawdown_amount: amount, breach_on_touch: true, events: [{ kind: "mark", equity: atFloor }] });
    const through = Oracle.evaluate("drawdown", { type: "static", start_balance: size, drawdown_amount: amount, breach_on_touch: false, events: [{ kind: "mark", equity: (Number(floor) - 0.01).toFixed(2) }] });
    check(size + " equality off", equalOff.ok && equalOff.breached === false && equalOff.drawdown_room === "0.00" && equalOff.floor === floor);
    check(size + " equality on", equalOn.ok && equalOn.breached === true && equalOn.drawdown_room === "0.00");
    check(size + " one cent through", through.ok && through.breached === true);
    check(size + " floor outranks daily", Oracle.accountStatus(true, "DAILY LIMIT REACHED") === "BREACHED" && Oracle.accountStatus(true, "OK") === "BREACHED");

    const room = dll3;
    const exact = Oracle.evaluate("risk_room", { drawdown_room: room, daily_loss_limit: dll3, day_pnl: "-" + dll3.replace(".00", ""), dll_enforcement: "hard", dll_boundary: "exceed" });
    const cent = Oracle.evaluate("risk_room", { drawdown_room: room, daily_loss_limit: dll3, day_pnl: "-" + (Number(dll3) + 0.01).toFixed(2), dll_enforcement: "hard", dll_boundary: "exceed" });
    check(size + " DLL exact zero reached", exact.ok && exact.daily_status === "DAILY LIMIT REACHED" && exact.daily_room === "0.00" && exact.binding === "daily_loss" && exact.breached === undefined);
    check(size + " DLL one cent is a hard breach", cent.ok && cent.daily_status === "BREACHED" && cent.daily_room === "-0.01" && cent.binding_room === "0.00");
    check(size + " daily breach is not a floor breach", Oracle.accountStatus(false, cent.daily_status) === "BREACHED" && Oracle.accountStatus(false, exact.daily_status) === "DAILY LIMIT REACHED");
  });

  expectRow("P076", "Instant", "50000", "2000", "none");
  const instant = Oracle.evaluate("drawdown", { type: "static", start_balance: "50000", drawdown_amount: "2000", breach_on_touch: false, events: [{ kind: "mark", equity: "60000" }] });
  check("instant 50k floor stays 48000", instant.ok && instant.floor === "48000.00" && instant.locked === false && instant.drawdown_room === "12000.00");
  const instantEqual = Oracle.evaluate("drawdown", { type: "static", start_balance: "50000", drawdown_amount: "2000", breach_on_touch: false, events: [{ kind: "mark", equity: "48000" }] });
  const instantTouch = Oracle.evaluate("drawdown", { type: "static", start_balance: "50000", drawdown_amount: "2000", breach_on_touch: true, events: [{ kind: "mark", equity: "48000" }] });
  check("instant 50k both touch readings", instantEqual.breached === false && instantTouch.breached === true);
  check("P076 4 percent", byId.P076 && pctOf("4", "50000") === "2000" && byId.P076.note.includes("0.040000"));

  const locked = Oracle.evaluate("drawdown", { type: "static", start_balance: "50000", drawdown_amount: "3000", breach_on_touch: false, lock_offset: "0", events: [{ kind: "mark", equity: "50000" }] });
  check("static rejects a lock", locked.ok === false && locked.error === "INVALID_RULE_CONFIGURATION");

  const trailed = Oracle.evaluate("drawdown", { type: "intraday_trailing", start_balance: "50000", drawdown_amount: "3000", breach_on_touch: false, events: [{ kind: "mark", equity: "56000" }, { kind: "mark", equity: "53000" }] });
  const stayed = Oracle.evaluate("drawdown", { type: "static", start_balance: "50000", drawdown_amount: "3000", breach_on_touch: false, events: [{ kind: "mark", equity: "56000" }, { kind: "mark", equity: "53000" }] });
  check("counterfactual trail would rise", trailed.ok && trailed.floor === "53000.00" && trailed.locked === false);
  check("Vest static does not rise", stayed.ok && stayed.floor === "47000.00" && stayed.drawdown_room === "6000.00");

  // 4% choice exists only on 1-step and funded-after-1-step. 2-step stays 3%.
  check("1-step 4% converts", pctOf("4", "25000") === "1000");
  const four = Oracle.evaluate("risk_room", { drawdown_room: "1000.00", daily_loss_limit: "1000", day_pnl: "-1000", dll_enforcement: "hard", dll_boundary: "exceed" });
  check("25k 4% DLL binds before the 6% floor", four.ok && four.daily_status === "DAILY LIMIT REACHED" && four.binding === "daily_loss");
  check("2-step is not a 4% menu", byId.P062.daily_loss.pct === "3" && !Array.isArray(byId.P062.daily_loss.pct));
  check("funded paths differ", byId.P070.daily_loss.kind === "pct_choice" && byId.P074.daily_loss.kind === "pct" && byId.P070.account_size === "25000" && byId.P074.account_size === "25000");

  const newIds = presets.presets.map(p => p.id).filter(id => Number(id.slice(1)) >= 56);
  check("new id set", JSON.stringify(newIds) === JSON.stringify(Array.from({ length: 21 }, (_, i) => "P" + String(56 + i).padStart(3, "0"))));

  const Sel = require("../js/selector.js");
  const shown = Sel.selectablePresets(presets.presets);
  const shownIds = shown.map(p => p.id);
  ["P031", "P032", "P033"].forEach(id => {
    check(id + " not publicly selectable", shownIds.indexOf(id) < 0 && Sel.isHidden(id));
  });
  const vestPlans = Sel.publicPlans(presets.presets, "Vest (Vest Capital)");
  check("legacy Evaluation plan absent from selector", vestPlans.indexOf("Evaluation") < 0);
  check("Evaluation size list is empty", Sel.publicSizes(presets.presets, "Vest (Vest Capital)", "Evaluation").length === 0);
  check("hidden list is only the combined eval", JSON.stringify(Sel.HIDDEN_FROM_SELECTOR) === JSON.stringify(["P031", "P032", "P033"]));
  const newPublic = Array.from({ length: 21 }, (_, i) => "P" + String(56 + i).padStart(3, "0"));
  check("P056-P076 remain selectable", newPublic.every(id => shownIds.indexOf(id) >= 0));
  const nonVest = presets.presets.filter(p => p.firm !== "Vest (Vest Capital)");
  check("every non-Vest preset remains selectable", nonVest.length > 0 && nonVest.every(p => shownIds.indexOf(p.id) >= 0));
  check("existing Instant rows remain selectable", ["P027", "P028", "P029", "P030"].every(id => shownIds.indexOf(id) >= 0));
  check("hidden records still stored", !!byId.P031 && !!byId.P032 && byId.P032.plan === "Evaluation" && byId.P032.account_size === "10000" && byId.P032.drawdown.amount_usd === "600" && byId.P032.breach_on_touch === false);

  const filled = Sel.nextDllBasis("", undefined, "5000");
  check("empty reset balance fills from the new size", filled.replaced === true && filled.basis === "5000" && filled.autoBasis === "5000");
  const resized = Sel.nextDllBasis(filled.basis, filled.autoBasis, "50000");
  check("size change updates an automatic reset balance", resized.replaced === true && resized.basis === "50000" && resized.autoBasis === "50000");
  const typed = Sel.nextDllBasis("12345", resized.autoBasis, "10000");
  check("size change keeps a reset balance the user typed", typed.replaced === false && typed.basis === "12345" && typed.autoBasis === "50000");
  const cleared = Sel.nextDllBasis("", resized.autoBasis, "25000");
  check("a cleared reset balance fills from the new size", cleared.replaced === true && cleared.basis === "25000" && cleared.autoBasis === "25000");

  newPublic.forEach(id => {
    const p = byId[id];
    const note = (p && p.note) || "";
    check(id + " drawdown-touch warning kept", note.includes("Drawdown touch is not preset.") && note.includes("equality alone does not breach") && note.includes("touching the max-drawdown floor closes the account"));
    if (p && p.daily_loss.kind !== "none") {
      check(id + " daily-loss reset warning kept", note.includes("DLL basis text is the Loss Limits page") && note.includes("20:00 ET"));
    } else {
      check(id + " no daily-loss row still keeps the touch warning", p && p.daily_loss.kind === "none" && note.includes("No daily loss limit.") && note.includes("Drawdown touch is not preset."));
    }
  });

  console.log(`VEST ${fail ? "FAIL" : "PASS"} ${n - fail}/${n}`);
  return fail;
}

module.exports = run;
