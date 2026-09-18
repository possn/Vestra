const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: global ECYT search opens canonical dossier and can return to market', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.route('**/quote?ticker=ECYT**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker:'ECYT', name:'Ecovyst Inc.', exchange:'NYQ', quote_type:'EQUITY',
        currency:'USD', price:10.64
      })
    });
  });
  await page.route('**/market?ticker=ECYT**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker:'ECYT', name:'Ecovyst Inc.', exchange:'NYQ', quote_type:'EQUITY',
        currency:'USD', current_price:10.64, market_cap:1280000000,
        forward_pe:12.4, price_to_book:2.1, roe:0.14, fcf_yield:0.065,
        revenue_growth:0.209, earnings_growth:-0.18, operating_margin:0.108,
        profit_margin:0.098, debt_to_equity:71.38, current_ratio:1.7,
        fifty_two_week_high:12.75, fifty_two_week_low:7.90,
        analyst_price_target_mean:13.50, analyst_price_target_upside_pct:0.269,
        sector:'Basic Materials', industry:'Specialty Chemicals', country:'United States'
      })
    });
  });
  await page.route('**/learned-universe', async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' });
    } else {
      await route.continue();
    }
  });
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        quotes:[{symbol:'ECYT',longname:'Ecovyst Inc.',exchange:'NYQ',quoteType:'EQUITY',currency:'USD'}],
        news:[], lists:[]
      })
    });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => Boolean(window.VestraGlobalMarketSearch));

  const search = page.locator('#marketSearch');
  await search.fill('ECYT');
  const globalRow = page.locator('[data-vestra-global-ticker="ECYT"]').first();
  await expect(globalRow).toBeVisible({ timeout: 10_000 });
  await globalRow.tap();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible({ timeout: 12_000 });
  await expect(sheet).toHaveAttribute('data-ticker', 'ECYT');
  await expect(sheet).not.toHaveAttribute('data-tool', 'remote-live');
  await expect(sheet.locator('.market-tabs')).toBeVisible();
  await expect(sheet.locator('.market-detail-actions [data-market-close]')).toBeVisible();
  await expect(sheet.locator('#marketSheetContent')).toContainText('Ecovyst Inc.');
  await expect(sheet.locator('#marketSheetContent')).toContainText('10,64');

  const close = sheet.locator('.market-detail-actions [data-market-close]');
  const closeBox = await close.boundingBox();
  expect(closeBox).not.toBeNull();
  expect(closeBox.x + closeBox.width).toBeLessThanOrEqual(430);

  await close.tap();
  await expect(sheet).toBeHidden();
  await expect(search).toBeVisible();
  await expect(page.locator('html')).not.toHaveClass(/modal-open/);
  await expect(page.locator('body')).not.toHaveClass(/modal-open/);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
