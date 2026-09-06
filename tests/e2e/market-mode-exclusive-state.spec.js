const { test, expect } = require('@playwright/test');

async function openMarket(page) {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('#marketSearch')).toBeVisible();
  await expect(page.locator('[data-politicians-mode]')).toBeVisible({ timeout: 10_000 });
  await page.waitForFunction(() => window.VestraMarketUiPolish?.version === '1.0');
}

test('iPhone/WebKit: Políticos perde seleção ao escolher outro modo de mercado', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);

  const politicians = page.locator('[data-politicians-mode]');
  const lows = page.locator('[data-market-mode="lows"]');

  await politicians.click();
  await expect(politicians).toHaveClass(/is-active/);

  await lows.click();
  await expect(lows).toHaveClass(/is-active/);
  await expect(politicians).not.toHaveClass(/is-active/);

  const activeModes = page.locator('.market-mode-grid .market-mode.is-active');
  await expect(activeModes).toHaveCount(1);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
