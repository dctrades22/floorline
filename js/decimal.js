/* Tiny decimal helper: BigInt coefficient + base-10 exponent, sign kept separately (so -0 survives).
   Mirrors the subset of Python decimal (prec 50) that golden/oracle.py uses. No dependencies. */
(function (root) {
  "use strict";
  var PREC = 50;
  function DecErr(msg) { var e = new Error(msg); e.decimalInvalidOperation = true; return e; }
  function D(neg, c, e) { return { neg: !!neg, c: c, e: e }; }
  var TEN = 10n;
  function pow10(n) { return TEN ** BigInt(n); }
  function ndigits(c) { return c === 0n ? 1 : c.toString().length; }

  function parse(str) {
    var s = String(str).trim();
    if (/^[+-]?(inf|infinity|s?nan\d*)$/i.test(s)) return { special: true };
    var m = /^([+-])?(\d(?:_?\d)*)?(?:\.(\d(?:_?\d)*)?)?(?:[eE]([+-]?\d(?:_?\d)*))?$/.exec(s);
    if (!m || (m[2] === undefined && m[3] === undefined)) throw DecErr("conversion");
    var ip = (m[2] || "").replace(/_/g, ""), fp = (m[3] || "").replace(/_/g, "");
    var exp = m[4] ? parseInt(m[4].replace(/_/g, ""), 10) : 0;
    return D(m[1] === "-", BigInt((ip + fp) || "0"), exp - fp.length);
  }
  function fromInt(n) { return D(n < 0, BigInt(Math.abs(n)), 0); }

  // integer division of non-negative BigInt q*10^k with rounding mode, given sign
  function roundDrop(c, k, mode, neg) {
    if (k <= 0) return c * pow10(-k);
    var p = pow10(k), q = c / p, r = c % p;
    if (r === 0n) return q;
    var half = r * 2n, up;
    switch (mode) {
      case "DOWN": up = false; break;
      case "UP": up = true; break;
      case "CEILING": up = !neg; break;
      case "FLOOR": up = neg; break;
      case "HALF_UP": up = half >= p; break;
      case "HALF_EVEN": up = half > p || (half === p && (q % 2n) === 1n); break;
      default: throw new Error("mode");
    }
    return up ? q + 1n : q;
  }
  function round(x, mode) { // context rounding to PREC significant digits
    var d = ndigits(x.c);
    if (d <= PREC) return x;
    var k = d - PREC, c = roundDrop(x.c, k, mode || "HALF_EVEN", x.neg), e = x.e + k;
    if (ndigits(c) > PREC) { c = c / TEN; e += 1; }
    return D(x.neg, c, e);
  }
  function sval(x) { return x.neg ? -x.c : x.c; }
  function cmp(a, b) {
    var e = Math.min(a.e, b.e), av = sval(a) * pow10(a.e - e), bv = sval(b) * pow10(b.e - e);
    return av < bv ? -1 : av > bv ? 1 : 0;
  }
  function neg(a) { return D(!a.neg, a.c, a.e); }
  function abs(a) { return D(false, a.c, a.e); }
  function add(a, b) {
    var e = Math.min(a.e, b.e), v = sval(a) * pow10(a.e - e) + sval(b) * pow10(b.e - e);
    var n = v < 0n || (v === 0n && a.neg && b.neg);
    return round(D(n, v < 0n ? -v : v, e));
  }
  function sub(a, b) { return add(a, neg(b)); }
  function mul(a, b) { return round(D(a.neg !== b.neg, a.c * b.c, a.e + b.e)); }
  function div(a, b) {
    if (b.c === 0n) throw DecErr("division by zero");
    var n = a.neg !== b.neg, ideal = a.e - b.e;
    if (a.c === 0n) return D(n, 0n, ideal);
    // scale so quotient has > PREC digits
    var shift = Math.max(0, PREC + 2 + ndigits(b.c) - ndigits(a.c));
    var num = a.c * pow10(shift), q = num / b.c, r = num % b.c, e = ideal - shift;
    if (r === 0n) { // exact: strip zeros toward ideal exponent
      while (e < ideal && q % TEN === 0n) { q = q / TEN; e += 1; }
      return round(D(n, q, e));
    }
    // inexact: append sticky digit then round half-even to PREC
    q = q * TEN + 1n; e -= 1;
    return round(D(n, q, e), "HALF_EVEN");
  }
  function quantize(x, exp, mode) {
    var c = x.e >= exp ? x.c * pow10(x.e - exp) : roundDrop(x.c, exp - x.e, mode, x.neg);
    if (ndigits(c) > PREC) throw DecErr("quantize exceeds precision");
    return D(x.neg, c, exp);
  }
  function toIntegral(x, mode) { return x.e >= 0 ? x : D(x.neg, roundDrop(x.c, -x.e, mode, x.neg), 0); }
  function isInteger(x) { return cmp(x, toIntegral(x, "DOWN")) === 0; }
  function isZero(x) { return x.c === 0n; }
  function max(a, b) { return cmp(b, a) > 0 ? b : a; }
  function min(a, b) { return cmp(b, a) < 0 ? b : a; }
  function toFixed(x) { // Python format(x, "f")
    var s = x.c.toString();
    if (x.e >= 0) s = s + "0".repeat(x.c === 0n ? 0 : x.e);
    else {
      var k = -x.e;
      if (s.length <= k) s = "0".repeat(k - s.length + 1) + s;
      s = s.slice(0, s.length - k) + "." + s.slice(s.length - k);
    }
    if (x.c === 0n && x.e > 0) s = "0";
    return (x.neg ? "-" : "") + s;
  }
  function toNumber(x) { return Number(toFixed(x)); }
  var api = { PREC: PREC, parse: parse, fromInt: fromInt, cmp: cmp, neg: neg, abs: abs, add: add, sub: sub,
    mul: mul, div: div, quantize: quantize, toIntegral: toIntegral, isInteger: isInteger, isZero: isZero,
    max: max, min: min, toFixed: toFixed, toNumber: toNumber, ZERO: D(false, 0n, 0) };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Dec = api;
})(this);
