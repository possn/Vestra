/* Vestra broker/dividend record normalization v1.1. */
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

function reconcileBrokerDividends(events = [], dividends = []) {
  const byKey = new Map();
  const keyFor = (broker, year) => `${String(broker || "Corretora").trim() || "Corretora"}|${year || "?"}`;
  const rowFor = (broker, year) => {
    const key = keyFor(broker, year);
    if (!byKey.has(key)) byKey.set(key, {
      broker: String(broker || "Corretora").trim() || "Corretora", year: String(year || "?"),
      sourceGross:0, sourceTax:0, sourceNet:0, storedGross:0, storedTax:0, storedNet:0,
      sourceCount:0, storedCount:0
    });
    return byKey.get(key);
  };

  for (const e of (Array.isArray(events) ? events : [])) {
    if (!e || !["DIVIDEND","ROC","DIVIDEND_ADJ"].includes(e.type)) continue;
    const year = String(e.date || "").slice(0,4) || "?";
    const r = rowFor(e.broker, year);
    const rawGross = parseNum(e.totalEUR);
    const gross = e.type === "DIVIDEND_ADJ" ? rawGross : Math.max(0, rawGross);
    const tax = Math.max(0, parseNum(e.taxEUR));
    r.sourceGross += gross;
    r.sourceTax += tax;
    r.sourceNet += gross - tax;
    r.sourceCount += 1;
  }

  for (const d of (Array.isArray(dividends) ? dividends : [])) {
    if (!d || !d.generatedFromBroker) continue;
    const year = String(d.date || "").slice(0,4) || "?";
    const broker = d.divBroker || (String(d.notes || "").match(/(?:^| · )(Trading 212|XTB|Corretora CSV|Corretora)(?: · |$)/i) || [])[1] || "Corretora";
    const r = rowFor(broker, year);
    r.storedGross += getDividendGross(d);
    r.storedTax += Math.max(0, parseNum(d.taxWithheld));
    r.storedNet += getDividendNet(d);
    r.storedCount += 1;
  }

  const round = n => Math.round((Number(n) || 0) * 1000000) / 1000000;
  const rows = [...byKey.values()].map(r => {
    const deltaGross = round(r.storedGross - r.sourceGross);
    const deltaTax = round(r.storedTax - r.sourceTax);
    const deltaNet = round(r.storedNet - r.sourceNet);
    return { ...r,
      sourceGross:round(r.sourceGross), sourceTax:round(r.sourceTax), sourceNet:round(r.sourceNet),
      storedGross:round(r.storedGross), storedTax:round(r.storedTax), storedNet:round(r.storedNet),
      deltaGross, deltaTax, deltaNet,
      ok: Math.abs(deltaGross) < 0.011 && Math.abs(deltaTax) < 0.011 && Math.abs(deltaNet) < 0.011
    };
  }).sort((a,b) => a.year !== b.year ? String(b.year).localeCompare(String(a.year)) : a.broker.localeCompare(b.broker));

  const totals = rows.reduce((a,r) => {
    a.sourceGross += r.sourceGross; a.sourceTax += r.sourceTax; a.sourceNet += r.sourceNet;
    a.storedGross += r.storedGross; a.storedTax += r.storedTax; a.storedNet += r.storedNet;
    return a;
  }, {sourceGross:0,sourceTax:0,sourceNet:0,storedGross:0,storedTax:0,storedNet:0});
  Object.keys(totals).forEach(k => totals[k] = round(totals[k]));
  totals.deltaGross = round(totals.storedGross - totals.sourceGross);
  totals.deltaTax = round(totals.storedTax - totals.sourceTax);
  totals.deltaNet = round(totals.storedNet - totals.sourceNet);
  const ok = rows.every(r => r.ok);
  return { version:1, generatedAt:new Date().toISOString(), ok, rows, totals };
}

  window.VestraBrokerNormalization = Object.freeze({
    divFloor, getDividendGross, getDividendNet, normalizeDividendRecord, reconcileBrokerDividends
  });
})();
