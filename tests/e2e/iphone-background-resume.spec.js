const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: foreground resume refreshes stale quotes once without disturbing the app', async ({ page }) => {
  const quoteRequests = [];
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.addInitScript(() => {
    const now = Date.now();
    const today = new Date(now).toISOString().slice(0, 10);
    const initialState = {
      settings: {
        currency: 'EUR',
        autoRefreshQuotes: true,
        workerUrl: '/__resume-worker',
        lastQuoteRefreshTs: now,
        lastQuoteRefreshDate: today,
        lastQuoteRefresh: {
          updated: 1,
          failed: 0,
          skipped: 0,
          errors: [],
          ts: new Date(now).toISOString(),
          durationMs: 10,
        },
      },
      assets: [{
        id: 'resume-msft',
        class: 'Ações/ETFs',
        name: 'Microsoft',
        ticker: 'MSFT',
        yahooTicker: 'MSFT',
        qty: 1,
        value: 300,
        currency: 'USD',
        priceCurrency: 'USD',
      }],
      liabilities: [],
      transactions: [],
      bankTransactions: [],
      dividends: [],
      divSummaries: [],
      history: [],
      priceHistory: {},
      fxHistory: {},
      brokerData: { files: [], events: [], positions: [] },
    };
    localStorage.setItem('PF_STATE_V6', JSON.stringify(initialState));

    // Track registration of the real lifecycle listeners. This gives WebKit a
    // deterministic readiness signal without relying on a synthetic app-ready
    // event that Vestra does not emit.
    window.__vestraVisibilityListenerRegistrations = 0;
    const originalDocumentAddEventListener = document.addEventListener.bind(document);
    document.addEventListener = function(type, listener, options) {
      if (type === 'visibilitychange') window.__vestraVisibilityListenerRegistrations += 1;
      return originalDocumentAddEventListener(type, listener, options);
    };

    // WebKit does not expose a CDP visibility override. Shadow the document
    // properties before Vestra registers its listener so the test can exercise
    // the real visibilitychange path deterministically.
    window.__vestraTestVisibility = 'visible';
    try {
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        get: () => window.__vestraTestVisibility,
      });
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        get: () => window.__vestraTestVisibility === 'hidden',
      });
    } catch (_) {}
  });

  await page.route('**/__resume-worker/**', async route => {
    const url = new URL(route.request().url());
    const tickerParam = url.searchParams.get('tickers') || url.searchParams.get('ticker') || '';
    const tickers = tickerParam.split(',').map(value => decodeURIComponent(value).trim()).filter(Boolean);
    if (tickers.some(ticker => ticker === 'MSFT')) quoteRequests.push(url.pathname + url.search);

    if (url.pathname.endsWith('/quotes')) {
      const payload = {};
      for (const ticker of tickers) {
        payload[ticker] = ticker === 'EURUSD=X'
          ? { symbol: ticker, price: 1.1, currency: 'USD' }
          : { symbol: ticker, price: 320, currency: 'USD' };
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
      return;
    }

    const ticker = tickers[0] || 'MSFT';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ticker === 'EURUSD=X'
        ? { symbol: ticker, price: 1.1, currency: 'USD' }
        : { symbol: ticker, price: 320, currency: 'USD' }),
    });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => (
    typeof window.setView === 'function'
    && window.__vestraVisibilityListenerRegistrations >= 2
  ));

  // The persisted timestamp is fresh on boot, so startup must not hit the quote worker.
  await page.waitForTimeout(350);
  expect(quoteRequests).toHaveLength(0);

  await page.evaluate(() => {
    window.__vestraTestVisibility = 'hidden';
    document.dispatchEvent(new Event('visibilitychange'));

    const realNow = Date.now.bind(Date);
    Date.now = () => realNow() + 61_000;

    window.__vestraTestVisibility = 'visible';
    document.dispatchEvent(new Event('visibilitychange'));
    // A second foreground signal in the same lifecycle turn must not launch a
    // second live refresh while the first one is already in flight.
    document.dispatchEvent(new Event('visibilitychange'));
  });

  await expect.poll(() => quoteRequests.length, { timeout: 5_000 }).toBe(1);

  // Resume must not break navigation or leave the mobile runtime unusable.
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('#viewMarket')).toBeVisible();
  await expect(page.locator('#marketSearch')).toBeVisible();
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});