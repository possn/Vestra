const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: global ticker uses canonical dossier and can return to Market', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.route('**/market?ticker=ECVT', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker: 'ECVT',
        name: 'Ecovyst Inc.',
        current_price: 10.64,
        currency: 'USD',
        exchange: 'NYQ',
        quote_type: 'EQUITY',
        sector: 'Basic Materials',
        industry: 'Specialty Chemicals',
        country: 'United States',
        market_cap: 890000000,
        trailing_pe: 18.2,
        forward_pe: 13.8,
        price_to_book: 2.1,
        roe: 0.12,
        revenue_growth: 0.209,
        earnings_growth: -0.18,
        operating_margin: 0.108,
        profit_margin: -0.098,
        debt_to_equity: 71.38,
        current_ratio: 1.9,
        free_cash_flow: 64000000,
        fcf_yield: 7.19,
        fifty_two_week_high: 12.72,
        fifty_two_week_low: 6.82,
        analyst_price_target_mean: 13.5,
        analyst_price_target_upside_pct: 26.88,
        price_history_1y: [
          { date:'2026-06-01', close:8.2 },
          { date:'2026-07-01', close:9.4 },
          { date:'2026-08-01', close:10.1 },
          { date:'2026-09-01', close:10.64 }
        ],
        source: 'test-global-market',
        updated: '2026-09-18T09:30:00Z',
        quote_updated: '2026-09-18T09:30:00Z'
      }),
    });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraGlobalMarketSearch && window.VestraNavigation && window.VestraMarket));
  await page.evaluate(() => window.setView?.('market'));

  const opened = await page.evaluate(() => window.VestraGlobalMarketSearch.openRemoteTicker('ECVT'));
  expect(opened).toBeTruthy();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible({ timeout: 10_000 });
  await expect(sheet).toHaveAttribute('data-ticker', 'ECVT');
  await expect(sheet).not.toHaveAttribute('data-tool', 'remote-live');

  const content = page.locator('#marketSheetContent');
  await expect(content).toContainText('Ecovyst Inc.');
  await expect(content).toContainText('10,64');
  await expect(content).toContainText('13,8');
  await expect(content).toContainText(/12[,.]0%/);
  await expect(content).toContainText(/20[,.]9%/);
  await expect(content).toContainText(/7[,.]2%/);
  expect(await content.locator('[data-detail-tab]').count()).toBeGreaterThanOrEqual(7);
  await expect(content).not.toContainText('DOSSIER GLOBAL · LIVE');
  await expect(content).not.toContainText('Não tem ainda Score Vestra pré-calculado');

  const close = sheet.locator(':scope > [data-market-close].market-close-persistent');
  await expect(close).toBeVisible();
  await close.tap();
  await expect(sheet).toBeHidden({ timeout: 3_000 });
  await expect(page.locator('#viewMarket')).toBeVisible();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
