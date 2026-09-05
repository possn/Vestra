const { test, expect } = require('@playwright/test');

async function isolateExternalSearch(page) {
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ quotes: [], news: [], lists: [] })
    });
  });
}

async function openMsftDossier(page) {
  await isolateExternalSearch(page);
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('#marketSearch')).toBeVisible();
  await page.locator('#marketSearch').fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();
  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', 'MSFT');
  await page.waitForFunction(() => !!window.VestraMarketDossierControls);
  return sheet;
}

test('iPhone/WebKit: dossier close is independent and favorite stays circular', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  const sheet = await openMsftDossier(page);
  const favorite = sheet.locator('.market-watch--detail');
  const close = sheet.locator('.market-detail-actions [data-market-close]');
  await expect(favorite).toBeVisible();
  await expect(close).toBeVisible();

  const geometry = await favorite.evaluate(el => {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return {
      width: box.width,
      height: box.height,
      flexShrink: style.flexShrink,
      borderRadius: style.borderRadius,
    };
  });
  expect(Math.abs(geometry.width - geometry.height)).toBeLessThan(0.5);
  expect(geometry.width).toBeGreaterThanOrEqual(40);
  expect(geometry.flexShrink).toBe('0');

  await close.click();
  await expect(sheet).toBeHidden();
  await expect(sheet).toHaveAttribute('aria-hidden', 'true');
  await expect(page.locator('html')).not.toHaveClass(/modal-open/);
  await expect(page.locator('body')).not.toHaveClass(/modal-open/);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
