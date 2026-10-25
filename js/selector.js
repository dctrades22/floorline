/* Public account selector. Hidden ids live here, not on the preset records,
   so the P001–P055 canonical hash stays byte-identical. */
(function (root) {
  "use strict";
  var HIDDEN_FROM_SELECTOR = ["P031", "P032", "P033"];

  function isHidden(id) {
    return HIDDEN_FROM_SELECTOR.indexOf(id) >= 0;
  }
  function selectablePresets(presets) {
    return presets.filter(function (p) { return !isHidden(p.id); });
  }
  function publicPlans(presets, firm) {
    var plans = [];
    selectablePresets(presets).forEach(function (p) {
      if (p.firm === firm && plans.indexOf(p.plan) < 0) plans.push(p.plan);
    });
    return plans;
  }
  function publicSizes(presets, firm, plan) {
    return selectablePresets(presets).filter(function (p) {
      return p.firm === firm && p.plan === plan;
    });
  }
  /* current is the field; autoBasis is the last value this page wrote; start is the new size.
     Empty or still equal to the autofill updates. Anything else is a user entry and stays. */
  function nextDllBasis(current, autoBasis, start) {
    if (!current || current === autoBasis) return { basis: start, autoBasis: start, replaced: true };
    return { basis: current, autoBasis: autoBasis, replaced: false };
  }

  var api = {
    HIDDEN_FROM_SELECTOR: HIDDEN_FROM_SELECTOR,
    isHidden: isHidden,
    selectablePresets: selectablePresets,
    publicPlans: publicPlans,
    publicSizes: publicSizes,
    nextDllBasis: nextDllBasis
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.FLOORLINE_SELECTOR = api;
})(typeof window !== "undefined" ? window : (typeof global !== "undefined" ? global : this));
