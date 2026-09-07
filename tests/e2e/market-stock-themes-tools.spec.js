const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: stocks open by theme and analysis tools stay visible above results', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => window.VestraMarketStockThemesTools?.version === '1.0');

  const stockMode = page.locator('[data-market-mode="discover"]');
  await expect(stockMode.locator('strong')).toHaveText('Ações');
  await stockMode.click();

  const tools = page.locator('.market-analysis-tools');
  await expect(tools).toBeVisible();
  await expect(page.locator('details.market-tools')).toHaveCount(0);
  await expect(tools.locator('[data-market-tool="compare"]')).toBeVisible();
  await expect(tools.locator('[data-market-tool="scanner"]')).toBeVisible();
  await expect(tools.locator('[data-market-tool="theses"]')).toBeVisible();
  await expect(tools.locator('[data-market-tool="news"]')).toBeVisible();

  const abovePrimary = await page.evaluate(() => {
    const tools = document.querySelector('.market-analysis-tools');
    const primary = document.getElementById('marketPrimary');
    return Boolean(tools && primary && (tools.compareDocumentPosition(primary) & Node.DOCUMENT_POSITION_FOLLOWING));
  });
  expect(abovePrimary).toBe(true);

  await expect(page.locator('.market-stock-theme-grid')).toBeVisible({ timeout: 15000 });
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]')).toHaveCount(0);

  const theme = page.locator('[data-market-stock-theme]:not([data-market-stock-theme=""])').first();
  await expect(theme).toBeVisible();
  await theme.click();

  await expect(page.locator('.market-stock-change-theme')).toBeVisible();
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]').first()).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
