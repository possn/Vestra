const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: news refreshes on resume and cold return never exposes an empty portfolio', async ({ page }) => {
  let newsRequestCount = 0;

  await page.addInitScript(() => {
    localStorage.setItem('PF_STATE_V6', JSON.stringify({
      settings: { currency: 'EUR', autoRefreshQuotes: false },
      assets: [{
        id: 'persisted-asset',
        class: 'Ações / ETFs',
        name: 'Persisted Portfolio Asset',
        ticker: 'AAPL',
        value: 1234,
        costBasis: 1000,
        yieldType: 'none',
        yieldValue: 0,
      }],
      liabilities: [],
      transactions: [],
      bankTransactions: [],
      dividends: [],
      divSummaries: [],
      history: [],
      brokerData: { files: [], events: [], positions: [] },
      priceHistory: {},
      fxHistory: {},
    }));

    window.__preHydrationPortfolioExposed = false;
    const installProbe = () => {
      const check = () => {
        if (document.body?.dataset?.appHydrated === '1') return;
        const overlay = document.getElementById('appLoadingOverlay');
        if (!overlay) return;
        const style = getComputedStyle(overlay);
        const shieldMissing = style.display === 'none' || Number(style.opacity || 0) === 0 || style.pointerEvents === 'none';
        if (shieldMissing) window.__preHydrationPortfolioExposed = true;
      };
      check();
      new MutationObserver(check).observe(document.documentElement, {
        attributes: true,
        childList: true,
        subtree: true,
        attributeFilter: ['style', 'class', 'data-app-hydrated', 'data-external-return-pending'],
      });
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installProbe, { once: true });
    else installProbe();
  });

  await page.route('**/data/dashboard-news.json**', async route => {
    newsRequestCount += 1;
    const resumed = newsRequestCount > 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        generated_at: resumed ? '2026-09-18T07:15:00Z' : '2026-09-18T07:00:00Z',
        items: [{
          title: resumed ? 'Fresh headline after returning to Vestra' : 'Initial market headline',
          source: 'Reuters',
          published: resumed ? '2026-09-18T07:14:00Z' : '2026-09-18T06:59:00Z',
          link: 'https://example.com/markets',
          kind: 'market',
          impact_score: 90,
          tickers: [],
        }],
      }),
    });
  });

  await page.context().route('https://example.com/markets', async route => {
    await route.fulfill({ status: 200, contentType: 'text/html', body: '<title>Market story</title><p>ok</p>' });
  });

  // Hold app.js only during the cold-return probe so the synchronous head
  // guard can be inspected deterministically before hydration clears it.
  // A fixed delay is racy on fast CI runners because app.js may hydrate
  // between waitForFunction() and the following evaluate().
  let holdAppJs = false;
  let releaseHeldAppJs = null;
  let heldAppJs = Promise.resolve();
  await page.route('**/app.js?v=20260918v1', async route => {
    if (holdAppJs) await heldAppJs;
    await route.continue();
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);
  await page.waitForFunction(() => Boolean(window.VestraDashboardDailyNews));

  const dashboard = page.locator('#viewDashboard');
  const card = dashboard.locator('#vestraDailyNewsCard');
  await expect(card).toBeVisible({ timeout: 15_000 });
  await expect(card).toContainText('Initial market headline');
  await expect(page.locator('#kpiNet')).not.toHaveText('0 €');

  const validLink = card.locator('a.vestra-daily-news-item').first();
  await expect(validLink).toHaveAttribute('href', 'https://example.com/markets');
  await expect(validLink).toHaveAttribute('rel', 'noopener noreferrer');

  const popupPromise = page.waitForEvent('popup');
  await validLink.tap();
  const popup = await popupPromise;
  await popup.waitForLoadState('domcontentloaded');
  await popup.close();

  // Normal resume: same document, no app restart. Only the feed refreshes.
  await page.evaluate(() => {
    window.dispatchEvent(new Event('focus'));
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: false }));
  });
  await expect(card).toContainText('Fresh headline after returning to Vestra', { timeout: 5_000 });
  expect(await page.evaluate(() => localStorage.getItem('vestra:external-return-v1'))).not.toBeNull();
  expect(await page.evaluate(() => window.__vestraAppHydrated)).toBe(true);

  // Cold resume: reproduce iOS discarding the PWA while Safari was in front.
  // The external-return shield must cover the pre-hydration HTML until the
  // persisted portfolio has been read and rendered again.
  holdAppJs = true;
  heldAppJs = new Promise(resolve => { releaseHeldAppJs = resolve; });
  await page.reload({ waitUntil: 'commit' });
  await page.waitForFunction(
    () => document.documentElement?.dataset?.externalReturnBootstrap === '1',
    null,
    { timeout: 1_000 }
  );
  const preHydrationGuard = await page.evaluate(() => {
    const html = document.documentElement;
    const splash = document.getElementById('appLoadingOverlay');
    const kpi = document.getElementById('kpiNet');
    const splashStyle = splash ? getComputedStyle(splash) : null;
    const kpiStyle = kpi ? getComputedStyle(kpi) : null;
    return {
      marker: html?.dataset?.externalReturnBootstrap || '',
      splashVisible: !!splashStyle && splashStyle.display !== 'none' && Number(splashStyle.opacity || 0) > 0,
      dashboardHidden: !kpi || kpiStyle?.visibility === 'hidden' || kpi.closest('body > *')?.style?.visibility === 'hidden',
    };
  });
  expect(preHydrationGuard.marker).toBe('1');
  expect(preHydrationGuard.splashVisible).toBe(true);
  expect(preHydrationGuard.dashboardHidden).toBe(true);

  holdAppJs = false;
  releaseHeldAppJs?.();
  await page.waitForLoadState('domcontentloaded');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);

  await expect(page.locator('#kpiNet')).not.toHaveText('0 €');
  expect(await page.evaluate(() => window.__preHydrationPortfolioExposed)).toBe(false);
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 1_500 });
  expect(await page.evaluate(() => localStorage.getItem('vestra:external-return-v1'))).toBeNull();
  expect(newsRequestCount).toBeGreaterThan(1);
});
