const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Dashboard renders weekly macro catalysts plus portfolio earnings', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraWeeklyEvents));

  // Reproduce the real default Dashboard state: secondary cards are collapsed.
  await page.evaluate(() => document.getElementById('viewDashboard')?.classList.remove('dash-secondary-open'));

  await page.evaluate(() => {
    window.VestraWeeklyEvents.render({
      now: new Date(2026, 8, 6, 9, 0, 0),
      portfolioTickers: new Set(['NVDA']),
      stocks: [
        { ticker:'NVDA', name:'NVIDIA Corporation', quote_type:'EQUITY', market_cap:4_000_000_000_000, analyst_next_earnings_date:'2026-09-08' },
        { ticker:'AAPL', name:'Apple Inc.', quote_type:'EQUITY', market_cap:3_500_000_000_000, analyst_next_earnings_date:'2026-09-09' },
        { ticker:'ETF1', name:'Not an earnings issuer', quote_type:'ETF', market_cap:8_000_000_000, analyst_next_earnings_date:'2026-09-07' },
      ],
      macroEvents: {
        events: [
          { date:'2026-09-10', short_title:'PPI EUA', title:'PPI EUA · agosto', category:'inflation', region:'EUA', importance:'high', source:'bls', time_local:'08:30 ET' },
          { date:'2026-09-11', short_title:'CPI EUA', title:'CPI EUA · agosto', category:'inflation', region:'EUA', importance:'critical', source:'bls', time_local:'08:30 ET' },
          { date:'2026-09-15', short_title:'FOMC', title:'FOMC', category:'central_bank', region:'EUA', importance:'critical', source:'fed' },
        ]
      }
    });
  });

  const card = page.locator('#dashboardWeeklyEventsCard');
  await expect(card).toBeVisible({ timeout: 15_000 });
  await expect(card.locator('.weekly-events-title')).toHaveText('Eventos da semana');
  await expect(card.locator('.weekly-events-range')).toContainText('6 set');
  await expect(card.locator('.weekly-events-range')).toContainText('12 set');

  const earnings = card.locator('[data-weekly-event-ticker]');
  await expect(earnings).toHaveCount(2);
  await expect(earnings.nth(0)).toHaveAttribute('data-weekly-event-ticker', 'NVDA');
  await expect(earnings.nth(0)).toContainText('NVIDIA Corporation');
  await expect(earnings.nth(0)).toContainText('No portefólio');
  await expect(earnings.nth(1)).toHaveAttribute('data-weekly-event-ticker', 'AAPL');
  await expect(card).toContainText('PPI EUA');
  await expect(card).toContainText('CPI EUA');
  await expect(card).toContainText('Inflação');
  await expect(card).toContainText('Impacto elevado');
  await expect(card).not.toContainText('FOMC');
  await expect(card).not.toContainText('ETF1');

  const order = await page.locator('#viewDashboard > .card').evaluateAll(nodes => nodes.map(node => node.id || node.className));
  const heroIndex = order.findIndex(value => String(value).includes('hero'));
  const weeklyIndex = order.findIndex(value => value === 'dashboardWeeklyEventsCard');
  expect(weeklyIndex).toBe(heroIndex + 1);
  await expect(page.locator('#viewDashboard .card.hero')).toBeVisible();
  await expect(card).toBeVisible();
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
