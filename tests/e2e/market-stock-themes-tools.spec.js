const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Ideias coexist with a separate broad stock-theme browser', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => window.VestraMarketStockThemesTools?.version === '1.3');

  const ideas = page.locator('[data-market-mode="discover"]');
  await expect(ideas.locator('strong')).toHaveText('Ideias');
  await ideas.click();
  await expect(page.locator('.market-discover-section')).toBeVisible({ timeout: 15000 });

  const stocksMode = page.locator('[data-market-stock-browser]');
  await expect(stocksMode.locator('strong')).toHaveText('Ações');
  await stocksMode.click();
  await expect(page.locator('.market-stock-theme-grid')).toBeVisible({ timeout: 15000 });
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]')).toHaveCount(0);

  const theme = page.locator('[data-market-stock-theme]:not([data-market-stock-theme=""])').first();
  await expect(theme).toBeVisible();
  await theme.click();
  await expect(page.locator('.market-stock-change-theme')).toBeVisible();
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]').first()).toBeVisible();

  const tools = page.locator('.market-analysis-tools');
  await expect(tools).toBeVisible();
  await expect(tools.locator('[data-market-tool="compare"]')).toBeVisible();
  await expect(tools.locator('[data-market-tool="scanner"]')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
