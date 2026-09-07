const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: ETFs start with themes and reveal funds only after choosing one', async ({ page }) => {
  const errors=[];
  page.on('pageerror', e=>errors.push(e.message));
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  const etfMode=page.locator('[data-market-mode="funds"]');
  await expect(etfMode).toBeVisible();
  await etfMode.click();
  await expect(page.locator('.market-etf-theme-grid')).toBeVisible({timeout:15000});
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]')).toHaveCount(0);
  const theme=page.locator('[data-market-fund-theme]:not([data-market-fund-theme=""])').first();
  await expect(theme).toBeVisible();
  await theme.click();
  await expect(page.locator('.market-etf-change-theme')).toBeVisible();
  await expect(page.locator('#marketPrimary .market-row[data-market-ticker]').first()).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
