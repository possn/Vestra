/* Vestra canonical quote recovery v1.0 — recover assets previously poisoned by a wrong quote without weakening normal sanity checks. */
(() => {
  'use strict';

  const RULES = Object.freeze({
    // Trading 212 source of truth: Siemens Healthineers AG
    // ISIN DE000SHL1006 · broker ticker SHL · Xetra/Yahoo SHL.DE · EUR.
    // A historical wrong quote was persisted as ~78k USD and can otherwise trap
    // the asset because the normal >5x sanity guard correctly rejects the repair.
    DE000SHL1006: Object.freeze({ ticker: 'SHL.DE', currency: 'EUR', minPrice: 5, maxPrice: 200 })
  });

  function canonicalRecoveryAllowed(asset, q, rawTicker) {
    const isin = String(asset && asset.isin || '').trim().toUpperCase();
    const rule = RULES[isin];
    if (!rule || !q) return false;

    const quoteTicker = String(q.ticker || rawTicker || '').trim().toUpperCase();
    const quoteCurrency = String(q.currency || '').trim().toUpperCase();
    const quotePrice = Number(q.price);

    return quoteTicker === rule.ticker &&
      quoteCurrency === rule.currency &&
      Number.isFinite(quotePrice) &&
      quotePrice >= rule.minPrice &&
      quotePrice <= rule.maxPrice;
  }

  function install() {
    const original = window.quoteSanityCheck;
    if (typeof original !== 'function' || original.__vestraCanonicalRepairWrapped) return false;

    function wrappedQuoteSanityCheck(asset, q, priceEur, rawTicker, previousYahooTicker) {
      const result = original(asset, q, priceEur, rawTicker, previousYahooTicker);
      if (result && result.ok) return result;
      if (canonicalRecoveryAllowed(asset, q, rawTicker)) {
        return { ok: true, canonicalRecovery: true };
      }
      return result;
    }

    Object.defineProperty(wrappedQuoteSanityCheck, '__vestraCanonicalRepairWrapped', { value: true });
    window.quoteSanityCheck = wrappedQuoteSanityCheck;
    return true;
  }

  if (!install()) {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  }

  window.VestraCanonicalQuoteRepair = Object.freeze({
    version: '1.0',
    rules: RULES,
    canonicalRecoveryAllowed,
    install
  });
})();
