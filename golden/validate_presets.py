#!/usr/bin/env python3
"""Stdlib validator for data/presets.json against data/presets.schema.json (JSON Schema subset:
type, enum, pattern, properties, required, additionalProperties:false, items, $ref) plus semantic rules.
Any unknown key/shape is an error (callers must map to INVALID_RULE_CONFIGURATION, never default)."""
import json, os, re, sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPES = {"string": str, "object": dict, "array": list, "boolean": bool, "null": type(None)}


def tmatch(v, t):
    if t == "boolean": return isinstance(v, bool)
    return isinstance(v, TYPES[t]) and not (t != "boolean" and isinstance(v, bool))


def check(v, s, root, path, errs):
    if "$ref" in s:
        s = root["$defs"][s["$ref"].split("/")[-1]]
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(tmatch(v, t) for t in ts):
            errs.append(f"{path}: type {type(v).__name__} not in {ts}"); return
    if "enum" in s and v not in s["enum"]: errs.append(f"{path}: {v!r} not in enum")
    if isinstance(v, str) and "pattern" in s and not re.search(s["pattern"], v):
        errs.append(f"{path}: {v!r} fails pattern")
    if isinstance(v, dict):
        props = s.get("properties", {})
        for k in s.get("required", []):
            if k not in v: errs.append(f"{path}: missing {k}")
        for k, x in v.items():
            if k in props: check(x, props[k], root, f"{path}.{k}", errs)
            elif s.get("additionalProperties") is False: errs.append(f"{path}: unknown key {k}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v): check(x, s["items"], root, f"{path}[{i}]", errs)


NUMERIC = [("drawdown", "amount_usd"), ("drawdown", "pct_of_start"), ("lock", "offset_usd"),
           ("lock", "trail_trigger_balance_usd"), ("daily_loss", "amount_usd"), ("daily_loss", "pct"),
           ("max_contracts", "minis"), ("max_contracts", "micros"), ("max_contracts", "contracts"),
           ("max_contracts", "micro_ratio_stated")]


def semantic(p, path, errs):
    st = p["status"]
    nums = [f"{a}.{b}" for a, b in NUMERIC if p[a][b] is not None]
    if p["account_size"] is not None: nums.append("account_size")
    if st == "custom_only":
        if nums: errs.append(f"{path}: custom_only carries numbers {nums}")
        if p["drawdown"]["type"] is not None: errs.append(f"{path}: custom_only has drawdown.type")
        if p["breach_on_touch"] is not None: errs.append(f"{path}: custom_only has breach_on_touch")
        return
    d = p["drawdown"]
    if d["type"] is None: errs.append(f"{path}: {st} needs drawdown.type")
    if d["amount_usd"] is None and d["pct_of_start"] is None: errs.append(f"{path}: no drawdown amount")
    if st == "verified":
        for k in ("lock", "daily_loss"):
            if p[k]["kind"] == "unstated": errs.append(f"{path}: verified but {k} unstated")
        if p["breach_on_touch"] is None: errs.append(f"{path}: verified but breach_on_touch null")
    lk = p["lock"]
    if lk["kind"] == "offset" and lk["offset_usd"] is None: errs.append(f"{path}: lock offset missing")
    if lk["kind"] != "offset" and lk["offset_usd"] is not None: errs.append(f"{path}: offset_usd without kind offset")
    if d["type"] == "static" and lk["kind"] == "offset": errs.append(f"{path}: static with offset lock")
    dl = p["daily_loss"]
    if dl["kind"] == "fixed_usd" and dl["amount_usd"] is None: errs.append(f"{path}: fixed_usd without amount")
    if dl["kind"] in ("pct", "pct_of_start") and not isinstance(dl["pct"], str): errs.append(f"{path}: pct must be string")
    if dl["kind"] == "pct_choice" and not isinstance(dl["pct"], list): errs.append(f"{path}: pct_choice needs list")
    if dl["kind"] in ("none", "unstated") and (dl["amount_usd"] or dl["pct"]): errs.append(f"{path}: DLL numbers with kind {dl['kind']}")
    for a, b in NUMERIC:
        v = p[a][b]
        for x in (v if isinstance(v, list) else [v]):
            if x is not None and Decimal(x) < 0 and b != "offset_usd": errs.append(f"{path}: negative {a}.{b}")


def validate(doc, schema):
    errs = []
    check(doc, schema, schema, "$", errs)
    if errs: return errs
    ids = set()
    for i, p in enumerate(doc["presets"]):
        if p["id"] in ids: errs.append(f"$.presets[{i}]: duplicate id")
        ids.add(p["id"]); semantic(p, f"$.presets[{i}]({p['id']})", errs)
    return errs


def main_check():
    doc = json.load(open(os.path.join(ROOT, "data/presets.json")))
    schema = json.load(open(os.path.join(ROOT, "data/presets.schema.json")))
    errs = validate(doc, schema)
    for e in errs: print("PRESET", e)
    print("PRESETS", "FAIL" if errs else "PASS", len(doc.get("presets", [])))
    return len(errs)


if __name__ == "__main__":
    sys.exit(1 if main_check() else 0)
