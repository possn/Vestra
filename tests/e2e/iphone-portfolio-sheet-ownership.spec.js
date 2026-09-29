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
  await expect(page.locator('#viewMarket')).toHaveCSS('visibility', 'hidden');

  await expect.poll(
    () => sheet.evaluate(el => el.scrollHeight - el.clientHeight),
    { timeout: 15_000 }
  ).toBeGreaterThan(0);
  await sheet.evaluate(el => { el.scrollTop = el.scrollHeight; });
  await expect.poll(() => sheet.evaluate(el => el.scrollTop)).toBeGreaterThan(0);
  await sheet.locator('.market-close-persistent').click();
  await expect(sheet).toBeHidden();
  await expect(page.locator('#viewMarket')).toBeVisible();

  await page.evaluate(() => window.setView('market'));
  await page.locator('[data-market-tool="portfolio"]').first().click();
  await expect(sheet).toBeVisible();
  await page.waitForTimeout(80);
  expect(await sheet.evaluate(el => el.scrollTop)).toBe(0);
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('As minhas posições');
  await expect(sheet).not.toContainText('CF Industries · ENTRY 90');
});


test('iPhone/WebKit: expanded portfolio explorer hides base market and keeps close control in viewport', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => window.VestraMarket?.ensureLoaded);
  await page.evaluate(() => window.VestraMarket.ensureLoaded());

  await page.locator('[data-market-tool="portfolio"]').first().click();
  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(page.locator('#viewMarket')).toHaveCSS('visibility', 'hidden');

  const toggle = sheet.locator('[data-vpu-toggle]').first();
  await expect(toggle).toBeVisible();
  await toggle.click();

  const explorer = sheet.locator('.vpu-tabs-shell');
  await expect(explorer).toBeVisible();
  await expect(sheet.locator('.vpu-portfolio[data-vpu-expanded="1"] > .market-portfolio-section')).toBeHidden();

  const inflation = sheet.locator('[data-ux-kind="inflation"]');
  if (await inflation.count()) {
    await sheet.locator('[data-vpu-tab="monitor"]').click();
    await inflation.scrollIntoViewIfNeeded();
  } else {
    await sheet.evaluate(el => { el.scrollTop = el.scrollHeight; });
  }

  const closeExplorer = sheet.locator('.vpu-tabs-head [data-vpu-toggle]');
  await expect(closeExplorer).toBeVisible();
  const box = await closeExplorer.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);

  await closeExplorer.click();
  await expect(explorer).toBeHidden();
});
