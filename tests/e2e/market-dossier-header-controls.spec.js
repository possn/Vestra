const { test, expect } = require('@playwright/test');

async function openMarket(page) {
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ quotes: [], news: [], lists: [] }) });
  });
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('#marketSearch')).toBeVisible();
}

test('iPhone/WebKit: favorito e fechar ficam lado a lado e o X fecha o dossier', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);
  await page.locator('#marketSearch').fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await page.waitForFunction(() => window.VestraMarketDossierControls?.version === '1.1');

  const actions = sheet.locator('#marketSheetContent .market-detail-actions');
  const watch = actions.locator('[data-market-watch]');
  const persistentClose = page.locator('.market-close-persistent');
  await expect(actions).toBeVisible();
  await expect(watch).toBeVisible();
  await expect(persistentClose).toBeVisible();
  await expect(actions.locator('.market-close')).toBeHidden();

  const geometry = await page.evaluate(() => {
    const watch = document.querySelector('#marketSheetContent .market-detail-actions [data-market-watch]').getBoundingClientRect();
    const close = document.querySelector('.market-close-persistent').getBoundingClientRect();
    return {
      watchCenterY: watch.top + watch.height / 2,
      closeCenterY: close.top + close.height / 2,
      watchRight: watch.right,
      closeLeft: close.left,
      watchWidth: watch.width,
      closeWidth: close.width,
    };
  });
  expect(Math.abs(geometry.watchCenterY - geometry.closeCenterY)).toBeLessThanOrEqual(1);
  expect(geometry.closeLeft).toBeGreaterThanOrEqual(geometry.watchRight);
  expect(geometry.closeLeft - geometry.watchRight).toBeLessThanOrEqual(12);
  expect(geometry.watchWidth).toBeGreaterThanOrEqual(44);
  expect(geometry.closeWidth).toBeGreaterThanOrEqual(44);

  await sheet.locator('.market-sheet__panel').evaluate(el => { el.scrollTop = el.scrollHeight; });
  await expect(watch).toBeVisible();
  await expect(persistentClose).toBeVisible();
  await persistentClose.click();
  await expect(sheet).toBeHidden();
  await expect(sheet).toHaveAttribute('aria-hidden', 'true');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
