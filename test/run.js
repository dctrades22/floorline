#!/usr/bin/env node
// node test/run.js — no dependencies, no network.
"use strict";
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");
const Oracle = require("../js/oracle.js");
const { validate } = require("./schema.js");
const read = f => JSON.parse(fs.readFileSync(path.join(ROOT, f), "utf8"));
const canon = v => Array.isArray(v) ? v.map(canon) : (v && typeof v === "object")
  ? Object.fromEntries(Object.keys(v).sort().map(k => [k, canon(v[k])])) : v;
let fail = 0;

const cases = read("golden/cases.json").cases;
let pass = 0;
for (const c of cases) {
  const got = Oracle.evaluate(c.kind, c.input);
  if (JSON.stringify(canon(got)) === JSON.stringify(canon(c.expected))) pass++;
  else { fail++; console.log("MISMATCH", c.id, JSON.stringify(got), JSON.stringify(c.expected)); }
}
console.log(`GOLDEN ${pass === cases.length ? "PASS" : "FAIL"} ${pass}/${cases.length}`);
if (cases.length !== 80) { fail++; console.log("expected 80 golden cases, got " + cases.length); }
const required = { "IA-01": 13, "IA-02": 1, "IA-03": 5, "IA-04": 50 };
for (const id of Object.keys(required)) {
  const c = cases.find(x => x.id === id);
  const got = c && Oracle.evaluate("futures", c.input);
  if (!c || !got || got.contracts !== required[id]) {
    fail++; console.log("REQUIRED FAIL", id, got && got.contracts);
  } else console.log(`REQUIRED ${id} PASS contracts=${got.contracts} tick=${got.tick_value} class=${got.cap_class} cap=${got.active_cap}`);
}
for (const id of ["DL-01", "DL-02", "DL-03", "DL-04", "DL-05", "DL-06", "DL-07", "DL-08", "DL-11", "DL-12", "DL-14", "DL-15", "DL-16", "DL-17", "DL-18"]) {
  const c = cases.find(x => x.id === id);
  const got = c && Oracle.evaluate(c.kind, c.input);
  const exp = c && c.expected;
  const same = got && exp && got.daily_status === exp.daily_status && got.daily_room === exp.daily_room && got.binding_room === exp.binding_room;
  if (!same) { fail++; console.log("DAILY FAIL", id, got); }
  else console.log(`DAILY ${id} PASS status=${got.daily_status} room=${got.daily_room} binding=${got.binding_room}`);
}
// Independent of cases.json: blank / hard / soft at 0.01, 0, -0.01, -50, and a floor hit.
const rooms = [["0.01", "-999.99", "0.01", "0.01"], ["0.00", "-1000", "0.00", "0.00"], ["-0.01", "-1000.01", "-0.01", "0.00"], ["-50.00", "-1050", "-50.00", "0.00"]];
const words = {
  "unconfirmed|0.01": "OK", "hard|0.01": "OK", "soft|0.01": "OK",
  "unconfirmed|0.00": "DAILY LIMIT REACHED", "hard|0.00": "DAILY LIMIT REACHED", "soft|0.00": "DAILY LIMIT REACHED",
  "unconfirmed|-0.01": "RULE CONFIRMATION REQUIRED", "hard|-0.01": "BREACHED", "soft|-0.01": "DAILY LIMIT EXCEEDED",
  "unconfirmed|-50.00": "RULE CONFIRMATION REQUIRED", "hard|-50.00": "BREACHED", "soft|-50.00": "DAILY LIMIT EXCEEDED"
};
let matrixBad = 0;
for (const row of rooms) {
  for (const rule of ["unconfirmed", "hard", "soft"]) {
    const inp = { drawdown_room: "10000", daily_loss_limit: "1000", day_pnl: row[1] };
    if (rule !== "unconfirmed") inp.dll_enforcement = rule;
    const got = Oracle.evaluate("risk_room", inp);
    const exp = words[rule + "|" + row[0]];
    const floor = Oracle.accountStatus(true, exp);
    const open = Oracle.accountStatus(false, exp);
    if (!got.ok || got.daily_status !== exp || got.dll_rule !== rule || got.daily_room !== row[2] || got.binding_room !== row[3] || floor !== "BREACHED" || open !== exp) {
      matrixBad++; console.log("MATRIX FAIL", rule, row[0], got, exp, floor, open);
    }
  }
}
if (Oracle.accountStatus(false, null) !== "OK") { matrixBad++; console.log("MATRIX FAIL no dll"); }
console.log(`MATRIX ${matrixBad ? "FAIL" : "PASS"} 12 rooms x rule, floor outranks each`);
fail += matrixBad;

const d9 = cases.find(x => x.id === "DL-09");
const g9 = d9 && Oracle.evaluate("futures", d9.input);
if (!g9 || g9.contracts !== 0) { fail++; console.log("DAILY FAIL DL-09", g9); }
else console.log("DAILY DL-09 PASS contracts=0");

const presets = read("data/presets.json");
const errs = validate(presets, read("data/presets.schema.json"));
errs.forEach(e => console.log("PRESET", e));
console.log(`PRESETS ${errs.length ? "FAIL" : "PASS"} ${presets.presets.length} validated against schema + semantic rules`);
fail += errs.length;

// negative self-test: the validator must reject a broken preset (guards against a validator that passes everything)
const broken = JSON.parse(JSON.stringify(presets)); broken.presets[0].bogus = 1; broken.presets[1].status = "verifed";
const be = validate(broken, read("data/presets.schema.json"));
if (be.length < 2) { fail++; console.log("VALIDATOR SELF-TEST FAIL"); } else console.log("VALIDATOR SELF-TEST PASS (rejects unknown key + bad enum)");

const contracts = read("data/contracts.json").contracts;
const badC = contracts.filter(c => !/^[0-9]+(\.[0-9]+)?$/.test(c.tick_value_usd) || !c.source_url || !c.status);
const drift = contracts.filter(c => Oracle.TICKS[c.symbol] !== c.tick_value_usd);
drift.forEach(c => console.log("TICK DRIFT", c.symbol, Oracle.TICKS[c.symbol], c.tick_value_usd));
console.log(`CONTRACTS ${badC.length || drift.length ? "FAIL" : "PASS"} ${contracts.length}`); fail += badC.length + drift.length;

const { render } = require("../tools/build-data.js");
const fresh = render() === fs.readFileSync(path.join(ROOT, "js/data.js"), "utf8");
console.log(`DATA BUNDLE ${fresh ? "PASS in sync" : "FAIL stale: run node tools/build-data.js"}`); if (!fresh) fail++;

process.exit(fail ? 1 : 0);
