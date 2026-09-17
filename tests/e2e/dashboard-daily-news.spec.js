const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Dashboard daily news links stay stable and return without relaunch splash', async ({ page }) => {
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
  await dashboard.evaluate(node => {
    const mutation = document.createElement('span');
    mutation.hidden = true;
    node.appendChild(mutation);
    mutation.remove();
  });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect.poll(() => validLink.evaluate(node => node === window.__vestraDailyNewsLinkNode)).toBe(true);

  const popupPromise = page.waitForEvent('popup');
  await validLink.tap();
  const popup = await popupPromise;
  await popup.waitForLoadState('domcontentloaded');
  expect(popup.url()).toBe('https://example.com/markets');
  await popup.close();

  // iOS can emit focus/pageshow first and reload the standalone PWA immediately
  // afterwards. The return marker must survive those resume events long enough
  // for the next boot to consume it and suppress the launch splash.
  await page.evaluate(() => {
    window.dispatchEvent(new Event('focus'));
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: false }));
  });
  const markerBeforeReload = await page.evaluate(() => localStorage.getItem('vestra:daily-news-return-v1'));
  expect(markerBeforeReload).not.toBeNull();

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => Boolean(window.VestraDashboardDailyNews));
  const splash = page.locator('#appLoadingOverlay');
  await expect(splash).toHaveAttribute('data-news-return-skip', '1');
  await expect(splash).toBeHidden({ timeout: 1_500 });
  expect(await page.evaluate(() => localStorage.getItem('vestra:daily-news-return-v1'))).toBeNull();
});
