/* Vestra broker/dividend record normalization v1.0. */
(() => {
  "use strict";
  const { parseNum } = window.VestraUtils || {};
  if (typeof parseNum !== "function") throw new Error("VestraUtils.parseNum unavailable");

// v63: dividend adjustments may legitimately be negative (clawbacks).
// Clamping them to 0 overstates income, so only non-adjustments are floored.
function divFloor(d, v) {
  return (d && d.isAdjustment) ? v : Math.max(0, v);
}

function getDividendGross(d) {
  const tax = Math.max(0, parseNum(d && d.taxWithheld || 0));
  if (!d) return 0;
  if (d.grossAmount !== undefined && d.grossAmount !== null && d.grossAmount !== "") return divFloor(d, parseNum(d.grossAmount));
  if (d.generatedFromBroker && !("grossAmount" in d) && !("netAmount" in d)) {
    // v63: broker imports now store `amount` as GROSS (T212 "Total" is gross —
    // verified against 1871 real rows). Do NOT re-add tax here; that was the
    // ~22% inflation bug.
    return divFloor(d, parseNum(d.amount));
  }
  if (d.netAmount !== undefined && d.netAmount !== null && d.netAmount !== "") return divFloor(d, parseNum(d.netAmount) + tax);
  return divFloor(d, parseNum(d.amount));
}

function getDividendNet(d) {
  const tax = Math.max(0, parseNum(d && d.taxWithheld || 0));
  if (!d) return 0;
  if (d.netAmount !== undefined && d.netAmount !== null && d.netAmount !== "") return divFloor(d, parseNum(d.netAmount));
  if (d.generatedFromBroker && !("grossAmount" in d) && !("netAmount" in d)) {
    return divFloor(d, parseNum(d.amount) - tax);
  }
  return divFloor(d, getDividendGross(d) - tax);
}

function normalizeDividendRecord(d) {
  if (!d || typeof d !== "object") return d;
  const tax = Math.max(0, parseNum(d.taxWithheld || 0));

  if (d.generatedFromBroker) {
    if (!("grossAmount" in d) && !("netAmount" in d)) {
      // v63: `amount` from broker import is GROSS (was wrongly assumed NET).
      const g = divFloor(d, parseNum(d.amount));
      d.grossAmount = g;
      d.netAmount = g - tax;
      d.amount = g; // storage stays GROSS
      return d;
    }
    const gross = ("grossAmount" in d) ? divFloor(d, parseNum(d.grossAmount)) : divFloor(d, parseNum(d.amount));
    const net = ("netAmount" in d) ? divFloor(d, parseNum(d.netAmount)) : divFloor(d, gross - tax);
    d.grossAmount = gross;
    d.netAmount = net;
    d.amount = gross;
    return d;
  }

  // Manual / other sources: amount is gross by convention
  const gross = ("grossAmount" in d) ? divFloor(d, parseNum(d.grossAmount)) : divFloor(d, parseNum(d.amount));
  const net = ("netAmount" in d) ? divFloor(d, parseNum(d.netAmount)) : divFloor(d, gross - tax);
  d.grossAmount = gross;
  d.netAmount = net;
  d.amount = gross;
  return d;
}


  window.VestraBrokerNormalization = Object.freeze({
    divFloor, getDividendGross, getDividendNet, normalizeDividendRecord
  });
})();
