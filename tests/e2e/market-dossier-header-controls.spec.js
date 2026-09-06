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

test('iPhone/WebKit: favorito e fechar são um único grupo fixo compacto', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);
  await page.locator('#marketSearch').fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await page.waitForFunction(() => window.VestraMarketDossierControls?.version === '1.2');
  await page.waitForFunction(() => window.VestraMarketUiPolish?.version === '1.2');

  const actions = sheet.locator('#marketSheetContent .market-detail-actions');
  const watch = actions.locator('[data-market-watch]');
  const close = actions.locator('[data-market-close]');
  const persistentClose = sheet.locator(':scope > .market-close-persistent');
  await expect(actions).toBeVisible();
  await expect(watch).toBeVisible();
  await expect(close).toBeVisible();
  await expect(persistentClose).toBeHidden();

  const geometry = await page.evaluate(() => {
    const actions = document.querySelector('#marketSheetContent .market-detail-actions');
    const watch = actions.querySelector('[data-market-watch]').getBoundingClientRect();
    const close = actions.querySelector('[data-market-close]').getBoundingClientRect();
    const group = actions.getBoundingClientRect();
    const style = getComputedStyle(actions);
    return {
      position: style.position,
      flexDirection: style.flexDirection,
      watchTop: watch.top,
      closeTop: close.top,
      watchHeight: watch.height,
      closeHeight: close.height,
      watchRight: watch.right,
      closeLeft: close.left,
      gap: close.left - watch.right,
      watchWidth: watch.width,
      closeWidth: close.width,
      groupWidth: group.width,
    };
  });

  expect(geometry.position).toBe('fixed');
  expect(geometry.flexDirection).toBe('row');
  expect(Math.abs(geometry.watchTop - geometry.closeTop)).toBeLessThanOrEqual(1);
  expect(Math.abs(geometry.watchHeight - geometry.closeHeight)).toBeLessThanOrEqual(1);
  expect(geometry.watchWidth).toBeGreaterThanOrEqual(45);
  expect(geometry.closeWidth).toBeGreaterThanOrEqual(45);
  expect(geometry.gap).toBeGreaterThanOrEqual(7);
  expect(geometry.gap).toBeLessThanOrEqual(9);
  expect(geometry.groupWidth).toBeLessThanOrEqual(102);

  const beforeScroll = await actions.boundingBox();
  await sheet.locator('.market-sheet__panel').evaluate(el => { el.scrollTop = el.scrollHeight; });
  await page.waitForTimeout(100);
  const afterScroll = await actions.boundingBox();
  expect(Math.abs(afterScroll.y - beforeScroll.y)).toBeLessThanOrEqual(1);
  expect(Math.abs(afterScroll.x - beforeScroll.x)).toBeLessThanOrEqual(1);

  await close.click();
  await expect(sheet).toBeHidden();
  await expect(sheet).toHaveAttribute('aria-hidden', 'true');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
