// JS port of golden/validate_presets.py: JSON Schema subset + semantic rules. Stdlib only.
"use strict";
const TYPES = { string: v => typeof v === "string", object: v => v !== null && typeof v === "object" && !Array.isArray(v),
  array: Array.isArray, boolean: v => typeof v === "boolean", null: v => v === null };
function check(v, s, root, p, errs) {
  if (s.$ref) s = root.$defs[s.$ref.split("/").pop()];
  if (s.type) { const ts = Array.isArray(s.type) ? s.type : [s.type];
    if (!ts.some(t => TYPES[t](v))) { errs.push(`${p}: type not in ${ts}`); return; } }
  if (s.enum && !s.enum.includes(v)) errs.push(`${p}: ${JSON.stringify(v)} not in enum`);
  if (typeof v === "string" && s.pattern && !new RegExp(s.pattern).test(v)) errs.push(`${p}: ${v} fails pattern`);
  if (TYPES.object(v)) { const props = s.properties || {};
    for (const k of s.required || []) if (!(k in v)) errs.push(`${p}: missing ${k}`);
    for (const [k, x] of Object.entries(v)) { if (k in props) check(x, props[k], root, `${p}.${k}`, errs);
      else if (s.additionalProperties === false) errs.push(`${p}: unknown key ${k}`); } }
  if (Array.isArray(v) && s.items) v.forEach((x, i) => check(x, s.items, root, `${p}[${i}]`, errs));
}
const NUMERIC = [["drawdown","amount_usd"],["drawdown","pct_of_start"],["lock","offset_usd"],["lock","trail_trigger_balance_usd"],
  ["daily_loss","amount_usd"],["daily_loss","pct"],["max_contracts","minis"],["max_contracts","micros"],["max_contracts","contracts"],["max_contracts","micro_ratio_stated"]];
const neg = x => /^-/.test(x) && !/^-0+(\.0+)?$/.test(x);
function semantic(pr, p, errs) {
  const st = pr.status, nums = NUMERIC.filter(([a, b]) => pr[a][b] !== null).map(([a, b]) => `${a}.${b}`);
  if (pr.account_size !== null) nums.push("account_size");
  if (st === "custom_only") {
    if (nums.length) errs.push(`${p}: custom_only carries numbers ${nums}`);
    if (pr.drawdown.type !== null) errs.push(`${p}: custom_only has drawdown.type`);
    if (pr.breach_on_touch !== null) errs.push(`${p}: custom_only has breach_on_touch`);
    return;
  }
  const d = pr.drawdown;
  if (d.type === null) errs.push(`${p}: ${st} needs drawdown.type`);
  if (d.amount_usd === null && d.pct_of_start === null) errs.push(`${p}: no drawdown amount`);
  if (st === "verified") { for (const k of ["lock", "daily_loss"]) if (pr[k].kind === "unstated") errs.push(`${p}: verified but ${k} unstated`);
    if (pr.breach_on_touch === null) errs.push(`${p}: verified but breach_on_touch null`); }
  const lk = pr.lock;
  if (lk.kind === "offset" && lk.offset_usd === null) errs.push(`${p}: lock offset missing`);
  if (lk.kind !== "offset" && lk.offset_usd !== null) errs.push(`${p}: offset_usd without kind offset`);
  if (d.type === "static" && lk.kind === "offset") errs.push(`${p}: static with offset lock`);
  const dl = pr.daily_loss;
  if (dl.kind === "fixed_usd" && dl.amount_usd === null) errs.push(`${p}: fixed_usd without amount`);
  if (["pct", "pct_of_start"].includes(dl.kind) && typeof dl.pct !== "string") errs.push(`${p}: pct must be string`);
  if (dl.kind === "pct_choice" && !Array.isArray(dl.pct)) errs.push(`${p}: pct_choice needs list`);
  const truthy = x => x !== null && x !== "" && !(Array.isArray(x) && !x.length);
  if (["none", "unstated"].includes(dl.kind) && (truthy(dl.amount_usd) || truthy(dl.pct))) errs.push(`${p}: DLL numbers with kind ${dl.kind}`);
  for (const [a, b] of NUMERIC) { const v = pr[a][b];
    for (const x of (Array.isArray(v) ? v : [v])) if (x !== null && neg(x) && b !== "offset_usd") errs.push(`${p}: negative ${a}.${b}`); }
}
function validate(doc, schema) {
  const errs = []; check(doc, schema, schema, "$", errs); if (errs.length) return errs;
  const ids = new Set();
  doc.presets.forEach((pr, i) => { if (ids.has(pr.id)) errs.push(`$.presets[${i}]: duplicate id`); ids.add(pr.id); semantic(pr, `$.presets[${i}](${pr.id})`, errs); });
  return errs;
}
module.exports = { validate };
