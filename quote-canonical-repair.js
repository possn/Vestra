/* Vestra Asset Identity Guard v2.3 — detect identity anomalies and recover stale broker quote identities without weakening normal sanity checks. */
(() => {
  'use strict';

  const IDENTITY_MAP_REPAIRS = Object.freeze({
    AU0000185993: 'IREN',
    IE00BLCHJ534: 'PAVE.L',
    GB00BL6K5J42: 'EDV.TO',
    GB00BVZK7T90: 'UNA.AS',
    GB0007188757: 'RIO.L',
    CH0334081137: 'CRSP',
    US64110L1061: 'NFC.DE',
    DE0006047004: 'HEI.DE',
  });

  const BROKER_ALIAS_REPAIRS = Object.freeze({
    RIO1: 'RIO.L',
    'HEI.DE': 'HEI.DE',
  });

  const SPECIAL_RECOVERY_RULES = Object.freeze({
    DE000SHL1006: Object.freeze({ ticker: 'SHL.DE', currency: 'EUR', minPrice: 5, maxPrice: 200 }),
    US12468P1049: Object.freeze({ ticker: 'AI', currency: 'USD', minPrice: 1, maxPrice: 100 }),
    AU0000185993: Object.freeze({ ticker: 'IREN', currency: 'USD', minPrice: 5, maxPrice: 150 }),
    DE0006047004: Object.freeze({ ticker: 'HEI.DE', currency: 'EUR', minPrice: 50, maxPrice: 400 }),
  });

  const BROKER_ALIAS_RECOVERY_RULES = Object.freeze({
    RIO1: Object.freeze({ ticker: 'RIO.L', currency: 'GBP', minPrice: 10, maxPrice: 150 }),
    'HEI.DE': Object.freeze({ ticker: 'HEI.DE', currency: 'EUR', minPrice: 50, maxPrice: 400 }),
  });

  const VENUE_CURRENCY = Object.freeze({
    '.DE':'EUR', '.F':'EUR', '.PA':'EUR', '.AS':'EUR', '.BR':'EUR', '.MI':'EUR',
    '.LS':'EUR', '.MC':'EUR', '.VI':'EUR', '.HE':'EUR', '.IR':'EUR',
    '.SW':'CHF', '.TO':'CAD', '.AX':'AUD', '.CO':'DKK', '.ST':'SEK',
    '.OL':'NOK', '.HK':'HKD', '.SI':'SGD', '.NZ':'NZD', '.L':'GBP'
  });

  const clean = value => String(value == null ? '' : value).trim().toUpperCase();

  function identityMap() {
    return (window.VestraAssetIdentity && window.VestraAssetIdentity.ISIN_YAHOO_MAP) || {};
  }

  function applyIdentityMapRepairs() {
    const map = identityMap();
    for (const [isin, ticker] of Object.entries(IDENTITY_MAP_REPAIRS)) map[isin] = ticker;
    return map;
  }

  applyIdentityMapRepairs();

  function localBrokerTicker(asset) {
    return clean(asset && (asset.ticker || asset.symbol));
  }

  function canonicalTickerFor(asset) {
    const isin = clean(asset && asset.isin);
    const byIsin = isin ? clean(identityMap()[isin]) : '';
    if (byIsin) return byIsin;
    return clean(BROKER_ALIAS_REPAIRS[localBrokerTicker(asset)]);
  }

  function expectedCurrencyForTicker(ticker) {
    const t = clean(ticker);
    for (const [suffix, currency] of Object.entries(VENUE_CURRENCY)) {
      if (t.endsWith(suffix)) return currency;
    }
    return '';
  }

  function storedTickerFor(asset, previousYahooTicker) {
    return clean(
      previousYahooTicker ||
      (asset && (asset.yahooTicker || asset.yahoo_ticker || asset._yahooTicker || asset.quoteTicker))
    );
  }

  function quoteIdentity(q, rawTicker) {
    return {
      ticker: clean(q && (q.ticker || q.symbol) || rawTicker),
      currency: clean(q && q.currency),
      price: Number(q && q.price)
    };
  }

  function assess(asset, q, rawTicker, previousYahooTicker) {
    const isin = clean(asset && asset.isin);
    const canonicalTicker = canonicalTickerFor(asset);
    const storedTicker = storedTickerFor(asset, previousYahooTicker);
    const expectedCurrency = expectedCurrencyForTicker(canonicalTicker);
    const quote = q ? quoteIdentity(q, rawTicker) : { ticker:'', currency:'', price:NaN };
    const issues = [];

    if (canonicalTicker && storedTicker && storedTicker !== canonicalTicker) {
      issues.push({ code:'stored_ticker_mismatch', severity:'warning', expected:canonicalTicker, actual:storedTicker });
    }
    if (q && canonicalTicker && quote.ticker && quote.ticker !== canonicalTicker) {
      issues.push({ code:'quote_ticker_mismatch', severity:'block', expected:canonicalTicker, actual:quote.ticker });
    }
    if (q && expectedCurrency && quote.currency && quote.currency !== expectedCurrency) {
      issues.push({ code:'quote_currency_mismatch', severity:'block', expected:expectedCurrency, actual:quote.currency });
    }
    if (q && (!Number.isFinite(quote.price) || quote.price <= 0)) {
      issues.push({ code:'invalid_quote_price', severity:'block', actual:q && q.price });
    }

    return Object.freeze({
      isin,
      canonicalTicker,
      storedTicker,
      expectedCurrency,
      quoteTicker: quote.ticker,
      quoteCurrency: quote.currency,
      quotePrice: Number.isFinite(quote.price) ? quote.price : null,
      issues
    });
  }

  function ruleForAsset(asset) {
    const isin = clean(asset && asset.isin);
    if (isin && SPECIAL_RECOVERY_RULES[isin]) return SPECIAL_RECOVERY_RULES[isin];
    return BROKER_ALIAS_RECOVERY_RULES[localBrokerTicker(asset)] || null;
  }

  function specialRecoveryAllowed(asset, q, rawTicker) {
    const rule = ruleForAsset(asset);
    if (!rule || !q) return false;
    const quote = quoteIdentity(q, rawTicker);
    return quote.ticker === rule.ticker &&
      quote.currency === rule.currency &&
      Number.isFinite(quote.price) &&
      quote.price >= rule.minPrice &&
      quote.price <= rule.maxPrice;
  }

  function canonicalRecoveryAllowed(asset, q, rawTicker, previousYahooTicker) {
    if (!asset || !q) return false;
    const report = assess(asset, q, rawTicker, previousYahooTicker);
    if (!report.canonicalTicker) return false;
    if (report.issues.some(issue => issue.severity === 'block')) return false;
    if (report.quoteTicker !== report.canonicalTicker) return false;
    if (report.expectedCurrency && report.quoteCurrency !== report.expectedCurrency) return false;
    if (!Number.isFinite(report.quotePrice) || report.quotePrice <= 0) return false;
    if (report.storedTicker && report.storedTicker !== report.canonicalTicker) return true;
    return specialRecoveryAllowed(asset, q, rawTicker);
  }

  function auditAssets(assets) {
    const rows = (Array.isArray(assets) ? assets : []).map(asset => assess(asset));
    const flaggedRows = rows.filter(row => row.issues.length > 0);
    const counts = {};
    for (const row of flaggedRows) {
      for (const issue of row.issues) counts[issue.code] = (counts[issue.code] || 0) + 1;
    }
    return Object.freeze({
      total: rows.length,
      mapped: rows.filter(row => row.canonicalTicker).length,
      flagged: flaggedRows.length,
      counts: Object.freeze(counts),
      rows: Object.freeze(flaggedRows)
    });
  }

  function install() {
    const original = window.quoteSanityCheck;
    if (typeof original !== 'function' || original.__vestraIdentityGuardWrapped) return false;

    function wrappedQuoteSanityCheck(asset, q, priceEur, rawTicker, previousYahooTicker) {
      const result = original(asset, q, priceEur, rawTicker, previousYahooTicker);
      if (result && result.ok) return result;
      if (canonicalRecoveryAllowed(asset, q, rawTicker, previousYahooTicker)) {
        return {
          ok: true,
          canonicalRecovery: true,
          canonicalTicker: canonicalTickerFor(asset),
          previousYahooTicker: storedTickerFor(asset, previousYahooTicker)
        };
      }
      return result;
    }

    Object.defineProperty(wrappedQuoteSanityCheck, '__vestraIdentityGuardWrapped', { value: true });
    window.quoteSanityCheck = wrappedQuoteSanityCheck;
    return true;
  }

  if (!install()) document.addEventListener('DOMContentLoaded', install, { once: true });

  const api = Object.freeze({
    version: '2.3',
    identityMapRepairs: IDENTITY_MAP_REPAIRS,
    brokerAliasRepairs: BROKER_ALIAS_REPAIRS,
    specialRules: SPECIAL_RECOVERY_RULES,
    brokerAliasRules: BROKER_ALIAS_RECOVERY_RULES,
    applyIdentityMapRepairs,
    canonicalTickerFor,
    expectedCurrencyForTicker,
    assess,
    auditAssets,
    canonicalRecoveryAllowed,
    install
  });

  window.VestraAssetIdentityGuard = api;
  window.VestraCanonicalQuoteRepair = api;
})();
