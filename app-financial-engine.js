/* Vestra Financial Engine v1.0 — pure compound/projection mathematics. */
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
        // Annual compounding: interest once, then twelve monthly contributions.
        v = v * (1 + r) + monthlyContribution * 12;
      } else {
        for (let p = 0; p < periods; p++) {
          v = v * (1 + r / periods) + monthlyContribution * (12 / periods);
        }
      }
    }
    return result;
  }

  window.VestraFinancialEngine = Object.freeze({ version:'1.0', compoundGrowth });
})();
