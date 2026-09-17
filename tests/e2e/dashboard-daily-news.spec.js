const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Dashboard daily news links stay stable and return without a cold-start splash', async ({ page }) => {
  await page.route('**/data/dashboard-news.json', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        generated_at: '2026-09-15T10:50:12Z',
        items: [
          {
            title: 'Markets steady ahead of central-bank decision',
            source: 'Reuters',
            published: '2026-09-15T10:30:00Z',
            link: 'https://example.com/markets',
            kind: 'market',
            impact_score: 90,
            tickers: [],
          },
          {
            title: 'Unsafe feed item remains visible but cannot execute',
            source: 'Test Feed',
            published: '2026-09-15T10:20:00Z',
            link: 'javascript:alert(1)',
            kind: 'market',
            impact_score: 80,
            tickers: [],
          },
        ],
      }),
    });
  });
  await page.context().route('https://example.com/markets', async route => {
    await route.fulfill({ status: 200, contentType: 'text/html', body: '<title>Market story</title><p>ok</p>' });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraDashboardDailyNews));

  const dashboard = page.locator('#viewDashboard');
  const card = dashboard.locator('#vestraDailyNewsCard');
  await expect(card).toBeVisible({ timeout: 15_000 });
  await expect(card).toContainText('Notícias do dia');
  await expect(card).toContainText('Markets steady ahead of central-bank decision');

  const validLink = card.locator('a.vestra-daily-news-item').filter({ hasText: 'Markets steady' });
  await expect(validLink).toHaveAttribute('href', 'https://example.com/markets');
  await expect(validLink).toHaveAttribute('rel', 'noopener noreferrer');

  const unsafeItem = card.locator('.vestra-daily-news-item.is-disabled').filter({ hasText: 'Unsafe feed item' });
  await expect(unsafeItem).toBeVisible();
  await expect(unsafeItem).not.toHaveAttribute('href', /.+/);

  const placement = await dashboard.evaluate(node => {
    const cardNode = node.querySelector('#vestraDailyNewsCard');
    const quick = node.querySelector('.kpi-quick');
    return Boolean(cardNode && quick && cardNode.parentElement === node && cardNode.nextElementSibling === quick);
  });
  expect(placement).toBe(true);

  await validLink.evaluate(node => { window.__vestraDailyNewsLinkNode = node; });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect.poll(() => validLink.evaluate(node => node === window.__vestraDailyNewsLinkNode)).toBe(true);

  const popupPromise = page.waitForEvent('popup');
  await validLink.tap();
  const popup = await popupPromise;
  await popup.waitForLoadState('domcontentloaded');
  expect(popup.url()).toBe('https://example.com/markets');

  // The outbound tap must leave a one-shot return marker before WebKit hands
  // control to the external page. This covers the installed-PWA case where iOS
  // reclaims the Vestra process while Safari is showing the article.
  let marker = await page.evaluate(() => JSON.parse(localStorage.getItem('vestra:daily-news-return-v1') || 'null'));
  expect(marker).not.toBeNull();
  expect(Number(marker.ts)).toBeGreaterThan(0);

  // iOS may emit focus/pageshow while handing the standalone PWA off to Safari.
  // Those signals alone must never consume the marker, otherwise a later
  // process recreation is mistaken for a cold start and shows the splash.
  await page.evaluate(() => {
    window.dispatchEvent(new Event('focus'));
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
  });
  marker = await page.evaluate(() => JSON.parse(localStorage.getItem('vestra:daily-news-return-v1') || 'null'));
  expect(marker).not.toBeNull();

  // Model iOS recreating the PWA document while the article is still open.
  // Returning must be a warm continuation, not another branded cold start.
  await page.reload({ waitUntil: 'domcontentloaded' });
  const splash = page.locator('#appLoadingOverlay');
  await expect(splash).toBeHidden({ timeout: 1_500 });
  await expect(splash).toHaveAttribute('data-news-return-skip', '1');
  await expect(page.locator('#viewDashboard')).toBeVisible();
  await page.waitForFunction(() => Boolean(window.VestraDashboardDailyNews));
  await expect(page.locator('#vestraDailyNewsCard')).toBeVisible({ timeout: 15_000 });
  expect(await page.evaluate(() => localStorage.getItem('vestra:daily-news-return-v1'))).toBeNull();

  await popup.close();
});
