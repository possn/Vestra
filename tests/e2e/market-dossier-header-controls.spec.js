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

test('iPhone/WebKit: favorito fica fixo e fechar usa controlo persistente seguro', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);
  await page.locator('#marketSearch').fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await page.waitForFunction(() => window.VestraMarketDossierControls?.version === '1.7');
  await page.waitForFunction(() => window.VestraMarketUiPolish?.version === '1.3');

  const actions = sheet.locator('#marketSheetContent .market-detail-actions');
  const watch = actions.locator('[data-market-watch]');
  const close = actions.locator('[data-market-close]');
  const persistentClose = sheet.locator(':scope > .market-close-persistent');
  await expect(actions).toBeVisible();
  await expect(watch).toBeVisible();
  await expect(close).toBeHidden();
  await expect(persistentClose).toBeVisible();

  const geometry = await page.evaluate(() => {
    const actions = document.querySelector('#marketSheetContent .market-detail-actions');
    const watch = actions.querySelector('[data-market-watch]').getBoundingClientRect();
    const persistent = document.querySelector('#marketSheet > .market-close-persistent').getBoundingClientRect();
    const style = getComputedStyle(actions);
    return {
      position: style.position,
      flexDirection: style.flexDirection,
      watchWidth: watch.width,
      watchHeight: watch.height,
      persistentLeft: persistent.left,
      persistentRight: persistent.right,
      persistentTop: persistent.top,
      persistentWidth: persistent.width,
      viewportWidth: window.innerWidth,
    };
  });

  expect(geometry.position).toBe('fixed');
  expect(geometry.flexDirection).toBe('row');
  expect(geometry.watchWidth).toBeGreaterThanOrEqual(45);
  expect(Math.abs(geometry.watchWidth - geometry.watchHeight)).toBeLessThanOrEqual(1);
  expect(geometry.persistentWidth).toBeGreaterThanOrEqual(40);
  expect(geometry.persistentLeft).toBeGreaterThanOrEqual(0);
  expect(geometry.persistentRight).toBeLessThanOrEqual(geometry.viewportWidth);
  expect(geometry.persistentTop).toBeGreaterThanOrEqual(0);

  const beforeScroll = await actions.boundingBox();
  await sheet.locator('.market-sheet__panel').evaluate(el => { el.scrollTop = el.scrollHeight; });
  await page.waitForTimeout(100);
  const afterScroll = await actions.boundingBox();
  expect(Math.abs(afterScroll.y - beforeScroll.y)).toBeLessThanOrEqual(1);
  expect(Math.abs(afterScroll.x - beforeScroll.x)).toBeLessThanOrEqual(1);

  await persistentClose.click();
  await expect(sheet).toBeHidden();
  await expect(sheet).toHaveAttribute('aria-hidden', 'true');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});