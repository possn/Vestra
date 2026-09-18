const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: ECVT global search uses exact identity and canonical closable dossier', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.route(/\/quote\?ticker=ECVT(?:&|$)/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker: 'ECVT',
        provider_symbol: 'ECVT',
        retrieval_ticker: 'ECVT',
        price: 10.64,
        currency: 'USD',
        name: 'Ecovyst Inc.',
        exchange: 'NYQ',
        quote_type: 'EQUITY',
        updated: '2026-09-18T13:00:00Z',
      }),
    });
  });

  await page.route(/\/market\?ticker=ECVT(?:&|$)/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker: 'ECVT',
        provider_symbol: 'ECVT',
        retrieval_ticker: 'ECVT',
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
        updated: '2026-09-18T13:00:00Z',
        quote_updated: '2026-09-18T13:00:00Z'
      }),
    });
  });

  await page.route(/\/learned-universe$/, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(
    window.VestraGlobalMarketSearch &&
    window.VestraMarket?.upsertRemoteStock &&
    window.VestraNavigation?.openCompany
  ));

  const opened = await page.evaluate(() => window.VestraGlobalMarketSearch.openRemoteTicker('ECVT'));
  expect(opened).toBeTruthy();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', 'ECVT');
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('ECVT');
  await expect(sheet).toContainText('Ecovyst Inc.');
  await expect(sheet.locator('.market-tabs')).toBeVisible();
  await expect(sheet).not.toContainText('DOSSIER GLOBAL · LIVE');

  const identity = await page.evaluate(() => {
    const row = window.VestraMarket.resolvePortfolioStock({
      ticker: 'ECVT',
      yahooTicker: 'ECVT',
      symbol: 'ECVT',
      class: 'Ações'
    });
    return row ? {
      ticker: row.ticker,
      provider_symbol: row.provider_symbol,
      identity_verified: row.identity_verified,
      market_cap: row.market_cap,
      forward_pe: row.forward_pe,
      fifty_two_week_high: row.fifty_two_week_high,
      fifty_two_week_low: row.fifty_two_week_low,
    } : null;
  });
  expect(identity).toMatchObject({
    ticker: 'ECVT',
    provider_symbol: 'ECVT',
    identity_verified: true,
    market_cap: 890000000,
    forward_pe: 13.8,
    fifty_two_week_high: 12.72,
    fifty_two_week_low: 6.82,
  });

  const persistentClose = sheet.locator(':scope > .market-close-persistent[data-market-close]');
  await expect(persistentClose).toBeVisible();
  await persistentClose.tap();
  await expect(sheet).toBeHidden();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: mismatched provider identity cannot open a global dossier', async ({ page }) => {
  let marketRequests = 0;

  await page.route(/\/quote\?ticker=SPIE(?:&|$)/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker: 'SPIE',
        provider_symbol: 'GOOG',
        retrieval_ticker: 'SPIE',
        price: 343.68,
        currency: 'USD',
        name: 'Alphabet Inc.',
        exchange: 'NMS',
        quote_type: 'EQUITY',
      }),
    });
  });

  await page.route(/\/market\?ticker=SPIE(?:&|$)/, async route => {
    marketRequests += 1;
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: 'must not be called' }) });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraGlobalMarketSearch));

  const opened = await page.evaluate(() => window.VestraGlobalMarketSearch.openRemoteTicker('SPIE'));
  expect(opened).toBeFalsy();
  expect(marketRequests).toBe(0);
  await expect(page.locator('#marketSheet')).toBeHidden();
  await expect(page.locator('body')).not.toContainText('Alphabet Inc.');
});
