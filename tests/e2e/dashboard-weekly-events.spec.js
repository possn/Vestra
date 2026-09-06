const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Dashboard renders rolling weekly earnings with portfolio priority', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));
  await expect(page.locator('#dashboardWeeklyEventsCard')).toBeVisible({ timeout: 15_000 });

  await page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 6, 9, 0, 0),
      portfolioTickers: new Set(['NVDA']),
      stocks: [
        { ticker:'NVDA', name:'NVIDIA Corporation', quote_type:'EQUITY', market_cap:4_000_000_000_000, analyst_next_earnings_date:'2026-09-08' },
        { ticker:'AAPL', name:'Apple Inc.', quote_type:'EQUITY', market_cap:3_500_000_000_000, analyst_next_earnings_date:'2026-09-09' },
        { ticker:'ETF1', name:'Not an earnings issuer', quote_type:'ETF', market_cap:8_000_000_000, analyst_next_earnings_date:'2026-09-07' },
      ],
    });
  });

  const card = page.locator('#dashboardWeeklyEventsCard');
  await expect(card.locator('.weekly-events-title')).toHaveText('Eventos da semana');
  await expect(card.locator('.weekly-events-range')).toContainText('6 set');
  await expect(card.locator('.weekly-events-range')).toContainText('12 set');

  const events = card.locator('[data-weekly-event-ticker]');
  await expect(events).toHaveCount(2);
  await expect(events.nth(0)).toHaveAttribute('data-weekly-event-ticker', 'NVDA');
  await expect(events.nth(0)).toContainText('NVIDIA Corporation');
  await expect(events.nth(0)).toContainText('No portefólio');
  await expect(events.nth(1)).toHaveAttribute('data-weekly-event-ticker', 'AAPL');
  await expect(card).not.toContainText('ETF1');

  const hero = page.locator('#viewDashboard .card.hero');
  const weekly = page.locator('#dashboardWeeklyEventsCard');
  const order = await page.locator('#viewDashboard > .card').evaluateAll(nodes => nodes.map(node => node.id || node.className));
  const heroIndex = order.findIndex(value => String(value).includes('hero'));
  const weeklyIndex = order.findIndex(value => value === 'dashboardWeeklyEventsCard');
  expect(weeklyIndex).toBe(heroIndex + 1);
  await expect(hero).toBeVisible();
  await expect(weekly).toBeVisible();
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
