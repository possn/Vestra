/* Vestra Market Portfolio Context v1.0 — portfolio identity helpers for market research. */
(() => {
  'use strict';

  function create(options = {}) {
    const getAssets = typeof options.getAssets === 'function' ? options.getAssets : () => [];
    const text = typeof options.text === 'function' ? options.text : value => String(value ?? '').trim();
    const number = typeof options.number === 'function' ? options.number : value => {
      if (value === null || value === undefined || value === '') return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };

    function portfolioAssets() {
      const assets = getAssets();
      return Array.isArray(assets) ? assets : [];
    }

    function researchEligibleAsset(asset) {
      const cls = text(asset?.class).toLowerCase();
      // Company/fund fundamentals only. Crypto can share symbols with listed companies
      // (e.g. ATOM), so never infer research eligibility from ticker alone.
      if (cls.includes('cripto')) return false;
      return cls.includes('ações') || cls.includes('acoes') || cls.includes('etf') || cls.includes('fund');
    }

    function assetTicker(asset) {
      return text(asset?.yahooTicker || asset?.ticker || asset?.symbol).toUpperCase();
    }

    function portfolioTickers() {
      return new Set(portfolioAssets().filter(researchEligibleAsset).map(assetTicker).filter(Boolean));
    }

    function portfolioValue(asset) {
      return number(asset?.value) ?? number(asset?.marketValueEUR) ?? 0;
    }

    function euro(value) {
      return number(value) == null
        ? '—'
        : new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(number(value));
    }

    function inPortfolio(ticker) {
      const normalized = text(ticker).toUpperCase();
      const base = normalized.replace(/\.[A-Z]+$/, '');
      return [...portfolioTickers()].some(candidate => candidate === normalized || candidate.replace(/\.[A-Z]+$/, '') === base);
    }

    return Object.freeze({
      portfolioAssets,
      researchEligibleAsset,
      assetTicker,
      portfolioTickers,
      portfolioValue,
      euro,
      inPortfolio,
    });
  }

  window.VestraMarketPortfolioContext = Object.freeze({ create, version: '1.0' });
})();
