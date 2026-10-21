const { test, expect } = require('@playwright/test');

test('installed iPhone PWA offers manual non-destructive update when published CSS differs', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/index.html');
  const original = await page.locator('link[href^="vestra-iphone-canonical-scale.css"]').getAttribute('href');
  expect(original).toBeTruthy();
  await page.route('**/index.html?vestra-ui-check=*', route => route.fulfill({
    status: 200,
    contentType: 'text/html',
    body: '<html><head><link href="vestra-iphone-canonical-scale.css?v=NEXT-GENERATION" rel="stylesheet"/></head></html>'
  }));
  await page.evaluate(() => window.dispatchEvent(new Event('vestra:service-worker-updated')));
  await expect(page.locator('#vestraUiUpdateNotice')).toBeVisible();
  await expect(page.locator('#vestraUiUpdateNotice button')).toHaveText('Atualizar');
  expect(await page.evaluate(() => location.href)).toContain('index.html');
});

test('no update banner for identical stylesheet generation', async ({ page }) => {
  await page.goto('/index.html');
  const current = await page.locator('link[href^="vestra-iphone-canonical-scale.css"]').getAttribute('href');
  await page.route('**/index.html?vestra-ui-check=*', route => route.fulfill({
    status: 200,
    contentType: 'text/html',
    body: '<link href="' + current + '" rel="stylesheet"/>'
  }));
  await page.evaluate(() => window.dispatchEvent(new Event('vestra:service-worker-updated')));
  await expect(page.locator('#vestraUiUpdateNotice')).toHaveCount(0);
});
