const { test, expect } = require('@playwright/test');

test.use({ serviceWorkers: 'block' });

test('iPhone/WebKit: portfolio sheet owns the viewport and always reopens at the top', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => window.VestraMarket?.ensureLoaded);
  await page.evaluate(() => window.VestraMarket.ensureLoaded());

  // Reproduce the reported failure with a visible opportunity-shaped row in
  // the underlying Market surface. It must never bleed through the sheet.
  await page.evaluate(() => {
    const sentinel = document.createElement('div');
    sentinel.id = 'underlyingOpportunitySentinel';
    sentinel.className = 'ux453-opp';
    sentinel.textContent = 'CF Industries · ENTRY 90';
    sentinel.style.cssText = 'position:fixed;inset:auto 0 0 0;height:90px;z-index:1';
    document.getElementById('viewMarket').appendChild(sentinel);
  });

  const trigger = page.locator('[data-market-tool="portfolio"]').first();
  await trigger.click();
  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(page.locator('body')).toHaveClass(/market-sheet-open/);
  await expect(page.locator('#viewMarket')).toBeVisible();
  expect(await page.evaluate(() => {
    const top = document.elementFromPoint(window.innerWidth / 2, window.innerHeight - 12);
    return Boolean(top?.closest('#marketSheet'));
  })).toBeTruthy();

  await sheet.evaluate(el => { el.scrollTop = el.scrollHeight; });
  expect(await sheet.evaluate(el => el.scrollTop)).toBeGreaterThan(0);
  await sheet.locator('.market-close-persistent').click();
  await expect(sheet).toBeHidden();
  await expect(page.locator('body')).not.toHaveClass(/market-sheet-open/);

  await page.evaluate(() => window.setView('market'));
  await page.locator('[data-market-tool="portfolio"]').first().click();
  await expect(sheet).toBeVisible();
  await page.waitForTimeout(80);
  expect(await sheet.evaluate(el => el.scrollTop)).toBe(0);
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('As minhas posições');
  await expect(sheet).not.toContainText('CF Industries · ENTRY 90');
});
