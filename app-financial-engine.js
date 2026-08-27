/* Vestra Financial Engine v1.1 — pure compound/projection mathematics. */
(() => {
  'use strict';

  function compoundGrowth(principal, rateAnnual, years, freq = 12, contributions = 0) {
    const r = Number(rateAnnual || 0) / 100;
    const nYears = Math.max(0, Math.floor(Number(years) || 0));
    const periods = Math.max(1, Math.floor(Number(freq) || 1));
    const monthlyContribution = Number(contributions || 0);
    const result = [];
    let v = Number(principal || 0);

    for (let y = 0; y <= nYears; y++) {
      result.push({ year: y, value: v });
      if (y === nYears) break;
      if (periods <= 1) {
        v = v * (1 + r) + monthlyContribution * 12;
      } else {
        for (let p = 0; p < periods; p++) {
          v = v * (1 + r / periods) + monthlyContribution * (12 / periods);
        }
      }
    }
    return result;
  }

  function projectFireScenarios({ capital = 0, annualExpenses = 0, monthlySavings = 0, horizonYears = 30, passiveYieldRate = 0, scenarios = [] } = {}) {
    const cap0 = Number(capital || 0);
    const exp0 = Number(annualExpenses || 0);
    const saveM = Number(monthlySavings || 0);
    const H = Math.max(0, Math.floor(Number(horizonYears) || 0));
    const py = Number(passiveYieldRate || 0);
    return (Array.isArray(scenarios) ? scenarios : []).map(sc => {
      let cap = cap0, exp = exp0, hit = null;
      const swr = Number(sc && sc.swr || 0);
      const r = Number(sc && sc.r || 0);
      const inf = Number(sc && sc.inf || 0);
      const fireNum = swr > 0 ? exp0 / swr : Infinity;
      for (let t = 0; t <= H; t++) {
        const pass = py * cap;
        const fn = swr > 0 ? exp / swr : Infinity;
        if (!hit && cap >= fn) hit = { t, cap, exp, pass, fireNum: fn };
        if (t < H) {
          cap = cap * (1 + r) + saveM * 12;
          exp = exp * (1 + inf);
        }
      }
      return { sc, hit, fireNum };
    });
  }

  window.VestraFinancialEngine = Object.freeze({ version:'1.1', compoundGrowth, projectFireScenarios });
})();
