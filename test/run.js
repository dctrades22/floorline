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
if (cases.length !== 63) { fail++; console.log("expected 63 golden cases, got " + cases.length); }
const required = { "IA-01": 13, "IA-02": 1, "IA-03": 5, "IA-04": 50 };
for (const id of Object.keys(required)) {
  const c = cases.find(x => x.id === id);
  const got = c && Oracle.evaluate("futures", c.input);
  if (!c || !got || got.contracts !== required[id]) {
    fail++; console.log("REQUIRED FAIL", id, got && got.contracts);
  } else console.log(`REQUIRED ${id} PASS contracts=${got.contracts} tick=${got.tick_value} class=${got.cap_class} cap=${got.active_cap}`);
}

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
