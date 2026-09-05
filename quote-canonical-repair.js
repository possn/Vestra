/* Vestra Asset Identity Guard v2.1 — detect identity anomalies and recover stale broker quote identities without weakening normal sanity checks. */
(() => {
  'use strict';

  // Portfolio-backed listing corrections. An ISIN identifies the instrument but not
  // necessarily the broker venue. These two holdings were being forced onto a
  // different listing than the one actually held in the imported portfolio.
  const IDENTITY_MAP_REPAIRS = Object.freeze({
    AU0000185993: 'IREN',   // IREN Ltd — Nasdaq line held by the broker portfolio
    IE00BLCHJ534: 'PAVE.L', // Global X U.S. Infrastructure Development UCITS ETF USD Acc — LSE
  });

  // Explicit historical corruption rules. These are deliberately narrow and
  // only exist where we have source-of-truth broker identity plus a known bad
  // persisted quote that can otherwise trap the asset behind the >5x guard.
  const SPECIAL_RECOVERY_RULES = Object.freeze({
    DE000SHL1006: Object.freeze({ ticker: 'SHL.DE', currency: 'EUR', minPrice: 5, maxPrice: 200 }),
    US12468P1049: Object.freeze({ ticker: 'AI', currency: 'USD', minPrice: 1, maxPrice: 100 }),
  });

  const VENUE_CURRENCY = Object.freeze({
    '.DE':'EUR', '.F':'EUR', '.PA':'EUR', '.AS':'EUR', '.BR':'EUR', '.MI':'EUR',
    '.LS':'EUR', '.MC':'EUR', '.VI':'EUR', '.HE':'EUR', '.IR':'EUR',
    '.SW':'CHF', '.TO':'CAD', '.AX':'AUD', '.CO':'DKK', '.ST':'SEK',
    '.OL':'NOK', '.HK':'HKD', '.SI':'SGD', '.NZ':'NZD'
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

  // app.js keeps a reference to the same mutable map object, so repairing the map
  // here also fixes subsequent manual/automatic quote refreshes without rewriting
  // stored assets or touching quantities/cost basis.
  applyIdentityMapRepairs();

  function canonicalTickerFor(asset) {
    const isin = clean(asset && asset.isin);
    if (!isin) return '';
    return clean(identityMap()[isin]);
  }

  function expectedCurrencyForTicker(ticker) {
    const t = clean(ticker);
    for (const [suffix, currency] of Object.entries(VENUE_CURRENCY)) {
      if (t.endsWith(suffix)) return currency;
    }
    // London is intentionally omitted because Yahoo may expose GBP or GBp.
    // Bare symbols are intentionally omitted too: many non-US issuers trade
    // on US venues and the ISIN country alone does not determine quote currency.
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

    if (isin && canonicalTicker && storedTicker && storedTicker !== canonicalTicker) {
      issues.push({
        code: 'stored_ticker_mismatch',
        severity: 'warning',
        expected: canonicalTicker,
        actual: storedTicker
      });
    }

    if (q && canonicalTicker && quote.ticker && quote.ticker !== canonicalTicker) {
      issues.push({
        code: 'quote_ticker_mismatch',
        severity: 'block',
        expected: canonicalTicker,
        actual: quote.ticker
      });
    }

    if (q && expectedCurrency && quote.currency && quote.currency !== expectedCurrency) {
      issues.push({
        code: 'quote_currency_mismatch',
        severity: 'block',
        expected: expectedCurrency,
        actual: quote.currency
      });
    }

    if (q && (!Number.isFinite(quote.price) || quote.price <= 0)) {
      issues.push({ code: 'invalid_quote_price', severity: 'block', actual: q && q.price });
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

  function specialRecoveryAllowed(asset, q, rawTicker) {
    const isin = clean(asset && asset.isin);
    const rule = SPECIAL_RECOVERY_RULES[isin];
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

    // Recovery is only possible when the incoming quote itself is the exact
    // ISIN-backed canonical ticker and passes currency/price identity checks.
    if (report.issues.some(issue => issue.severity === 'block')) return false;
    if (report.quoteTicker !== report.canonicalTicker) return false;
    if (report.expectedCurrency && report.quoteCurrency !== report.expectedCurrency) return false;
    if (!Number.isFinite(report.quotePrice) || report.quotePrice <= 0) return false;

    // Generic recovery: a stale stored Yahoo identity differs from the exact
    // canonical mapping. The canonical quote is allowed to replace it.
    if (report.storedTicker && report.storedTicker !== report.canonicalTicker) return true;

    // Known historical contaminations may have already persisted the canonical
    // ticker while retaining a wrong price/currency history. Keep these explicit.
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
    version: '2.1',
    identityMapRepairs: IDENTITY_MAP_REPAIRS,
    specialRules: SPECIAL_RECOVERY_RULES,
    applyIdentityMapRepairs,
    canonicalTickerFor,
    expectedCurrencyForTicker,
    assess,
    auditAssets,
    canonicalRecoveryAllowed,
    install
  });

  window.VestraAssetIdentityGuard = api;
  // Backward-compatible alias used by the existing bootstrap/tests.
  window.VestraCanonicalQuoteRepair = api;
})();
