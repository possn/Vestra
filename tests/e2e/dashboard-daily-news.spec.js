const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Dashboard renders the daily news card in the live dashboard structure', async ({ page }) => {
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
});
