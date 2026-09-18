const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: global SPIE.PA uses exact identity and the canonical closable dossier', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.route(/\/quote\?ticker=SPIE\.PA(?:&|$)/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker: 'SPIE.PA',
        provider_symbol: 'SPIE.PA',
        retrieval_ticker: 'SPIE.PA',
        price: 44.02,
        currency: 'EUR',
        name: 'SPIE SA',
        exchange: 'PAR',
        quote_type: 'EQUITY',
        updated: '2026-09-18T09:30:00Z',
      }),
    });
  });

  await page.route(/\/market\?ticker=SPIE\.PA(?:&|$)/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker: 'SPIE.PA',
        provider_symbol: 'SPIE.PA',
        retrieval_ticker: 'SPIE.PA',
        name: 'SPIE SA',
        current_price: 44.02,
        currency: 'EUR',
        exchange: 'PAR',
        quote_type: 'EQUITY',
        sector: 'Industrials',
        industry: 'Engineering & Construction',
        country: 'France',
        market_cap: 7426000000,
        forward_pe: 12.77,
        price_to_book: 3.62,
        roe: 0.151,
        revenue_growth: 0.209,
        profit_margin: 0.0283,
        operating_margin: 0.108,
        debt_to_equity: 171.22,
        fifty_two_week_high: 53.45,
        fifty_two_week_low: 41.44,
        analyst_price_target_mean: 57.40,
        analyst_price_target_upside_pct: 30.40,
        updated: '2026-09-18T09:30:00Z',
        quote_updated: '2026-09-18T09:30:00Z',
      }),
    });
  });

  // Central learning must never block the visible dossier path.
  await page.route(/\/learned-universe$/, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(
    window.VestraGlobalMarketSearch &&
    window.VestraMarket?.upsertExternalStock &&
    window.VestraNavigation?.openCompany
  ));

  const opened = await page.evaluate(() => window.VestraGlobalMarketSearch.openRemoteTicker('SPIE.PA'));
  expect(opened).toBeTruthy();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', 'SPIE.PA');
  await expect(sheet).toContainText('SPIE SA');
  await expect(sheet).not.toContainText('Alphabet Inc.');
  await expect(sheet.locator('.market-tabs')).toBeVisible();
  await expect(sheet.locator('[data-live-field="current_price"]')).toContainText('44,02', { timeout: 5_000 });
  await expect(sheet).not.toContainText('DOSSIER GLOBAL · LIVE');

  const close = sheet.locator('[data-market-close]:visible').first();
  await expect(close).toBeVisible();
  await close.tap();
  await expect(sheet).toBeHidden();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: mismatched provider identity cannot open a global dossier', async ({ page }) => {
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

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraGlobalMarketSearch));

  const opened = await page.evaluate(() => window.VestraGlobalMarketSearch.openRemoteTicker('SPIE'));
  expect(opened).toBeFalsy();
  await expect(page.locator('#marketSheet')).toBeHidden();
  await expect(page.locator('body')).not.toContainText('Alphabet Inc.');
});
