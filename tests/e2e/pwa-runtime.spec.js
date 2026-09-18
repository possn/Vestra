const { test, expect } = require('@playwright/test');

// The normal functional suite deliberately blocks service workers to keep UI
// regressions deterministic. This spec is the explicit PWA integration gate.
test.use({ serviceWorkers: 'allow' });

async function readPwaState(page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await page.evaluate(async () => {
        const registration = await navigator.serviceWorker.getRegistration();
        const cacheNames = await caches.keys();
        const vestraCacheName = cacheNames.find(name => name.startsWith('vestra-cache-')) || '';
        const cache = vestraCacheName ? await caches.open(vestraCacheName) : null;
        const cachedUrls = cache ? (await cache.keys()).map(request => new URL(request.url).pathname.split('/').pop()) : [];
        const updateButton = document.getElementById('btnForceUpdate');
        return {
          controlled: Boolean(navigator.serviceWorker.controller),
          scriptURL: registration?.active?.scriptURL || registration?.waiting?.scriptURL || registration?.installing?.scriptURL || '',
          cacheName: vestraCacheName,
          hasAppShell: cachedUrls.includes('app.js'),
          hasMarketRuntime: cachedUrls.includes('market-analysis-tools-runtime.js'),
          safeUpdateApiReady: typeof window.VestraUiCore?.installSafeUpdateGuard === 'function' &&
            typeof window.VestraUiCore?.forceFreshReload === 'function',
          updateButtonPresent: Boolean(updateButton),
        };
      });
    } catch (error) {
      // On first install the canonical index bootstrap can reload after
      // controllerchange. WebKit can destroy the evaluate context there.
      if (!/Execution context was destroyed|navigation/i.test(String(error?.message || error)) || attempt === 2) throw error;
      await page.waitForLoadState('load');
      await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 10_000 });
    }
  }
  throw new Error('Unable to read stable PWA runtime state');
}

test('iPhone/WebKit: installed PWA runtime gains a service-worker controller and safe update ownership', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html', { waitUntil: 'load' });
  await page.waitForFunction(() => 'serviceWorker' in navigator);

  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });

  // skipWaiting + clients.claim should make the first loaded client controlled.
  // Allow WebKit a short lifecycle turn; if it still is not controlled, one reload
  // is legitimate and mirrors opening an already-installed PWA again.
  try {
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 5_000 });
  } catch (_) {
    await page.reload({ waitUntil: 'load' });
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller), null, { timeout: 10_000 });
  }

  const pwa = await readPwaState(page);

  expect(pwa.controlled).toBeTruthy();
  expect(pwa.scriptURL).toContain('/sw.js');
  expect(pwa.cacheName).toMatch(/^vestra-cache-/);
  expect(pwa.hasAppShell).toBeTruthy();
  expect(pwa.hasMarketRuntime).toBeTruthy();
  expect(pwa.safeUpdateApiReady).toBeTruthy();
  expect(pwa.updateButtonPresent).toBeTruthy();

  // Prove the loaded UI-core capture guard owns the real update button in
  // WebKit: a target listener added after app bootstrap must never receive the
  // click. Returning false from confirm keeps this ownership probe navigation-free.
  const safeCaptureOwnsClick = await page.evaluate(() => {
    const button = document.getElementById('btnForceUpdate');
    if (!button) return false;
    let targetRan = false;
    const originalConfirm = window.confirm;
    window.confirm = () => false;
    button.addEventListener('click', () => { targetRan = true; }, { once: true });
    button.click();
    window.confirm = originalConfirm;
    return !targetRan;
  });
  expect(safeCaptureOwnsClick).toBeTruthy();

  const survivesControllerSwapWithoutReload = await page.evaluate(async () => {
    window.__vestraControllerSwapSentinel = 'alive';
    navigator.serviceWorker.dispatchEvent(new Event('controllerchange'));
    await new Promise(resolve => setTimeout(resolve, 250));
    return window.__vestraControllerSwapSentinel === 'alive' &&
      window.__vestraServiceWorkerUpdated === true;
  });
  expect(survivesControllerSwapWithoutReload).toBeTruthy();

  // WebKit can emit this transient pageerror when controllerchange replaces the
  // execution context during first install. readPwaState explicitly recovers from
  // that navigation; keep every other browser error fatal.
  const unexpectedPageErrors = pageErrors.filter(message => message !== 'Context is stopped');
  expect(unexpectedPageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: a global live ticker opens the canonical dossier and can always close', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  const livePayload = {
    ticker: 'ECVT',
    name: 'Ecovyst Inc.',
    quote_type: 'EQUITY',
    exchange: 'NYQ',
    currency: 'USD',
    sector: 'Basic Materials',
    industry: 'Specialty Chemicals',
    country: 'United States',
    current_price: 10.64,
    market_cap: 1450000000,
    forward_pe: 12.3,
    price_to_book: 2.1,
    roe: 0.11,
    fcf_yield: 0.06,
    revenue_growth: 0.209,
    earnings_growth: -0.969,
    operating_margin: 0.108,
    profit_margin: -0.098,
    debt_to_equity: 71.38,
    current_ratio: 1.7,
    quick_ratio: 1.2,
    free_cash_flow: 118000000,
    operating_cash_flow: 164000000,
    fifty_two_week_high: 13.4,
    fifty_two_week_low: 8.2,
    analyst_price_target_mean: 14.0,
    analyst_price_target_upside_pct: 0.315,
    analyst_next_earnings_date: '2026-11-04',
    data_coverage_pct: 58,
    data_confidence: 'medium',
    quote_updated: '2026-09-18T09:20:00Z'
  };

  await page.route('**/market?ticker=ECVT', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(livePayload) });
  });
  await page.route('**/learned-universe', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Boolean(window.VestraMarket?.openLiveStock && window.VestraGlobalMarketSearch?.openRemoteTicker));
  await page.evaluate(() => { if (typeof setView === 'function') setView('market'); });

  const opened = await page.evaluate(() => window.VestraGlobalMarketSearch.openRemoteTicker('ECVT'));
  expect(opened).toBeTruthy();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', 'ECVT');
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('ECVT');
  await expect(sheet).toContainText('Ecovyst Inc.');

  // A live/global ticker must use the same canonical dossier as the daily universe.
  await expect(sheet.locator('.market-tabs .market-tab')).toHaveCount(8);
  await expect(sheet).not.toContainText('DOSSIER GLOBAL · LIVE');
  await expect(sheet.locator('[data-live-field="current_price"]')).toContainText('10,64');
  await expect(sheet.locator('[data-live-field="forward_pe"]')).toContainText('12,3');

  await sheet.locator('[data-detail-tab="financials"]').tap();
  await expect(sheet.locator('#marketDetailBody')).toContainText('Current ratio');
  await expect(sheet.locator('#marketDetailBody')).toContainText('1,7');
  await expect(sheet.locator('#marketDetailBody')).toContainText('Free cash flow');

  const close = sheet.locator('.market-detail-actions [data-market-close]');
  await expect(close).toBeVisible();
  await expect(close).toHaveAttribute('aria-label', 'Fechar dossier');
  await close.tap();
  await expect(sheet).toBeHidden();
  await expect(page.locator('#viewMarket')).toBeVisible();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
