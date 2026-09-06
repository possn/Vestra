const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash shows mark, then copy, holds it, then releases UI', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  const splash = page.locator('#appLoadingOverlay');
  const mark = page.locator('.vestra-splash__mark img');
  const brand = page.locator('.vestra-splash__brand');
  const tagline = page.locator('.vestra-splash__tagline');

  await expect(splash).toBeVisible();
  await expect(mark).toBeVisible();

  // The mark owns the first beat.
  const earlyBrandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(earlyBrandOpacity).toBeLessThan(0.35);

  // Copy now arrives earlier than before.
  await page.waitForTimeout(1050);
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.45);
  await expect(brand).toHaveText('Vestra');

  await page.waitForTimeout(850);
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(taglineOpacity).toBeGreaterThan(0.70);
  await expect(tagline).toHaveText('Finance, made simple.');

  // Critical regression: once the complete copy is visible it must stay on screen
  // long enough to read, rather than immediately transitioning to the app.
  const holdStarted = Date.now();
  await page.waitForTimeout(1050);
  await expect(splash).toBeVisible();
  const heldBrandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const heldTaglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  const heldSplashOpacity = await splash.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(Date.now() - holdStarted).toBeGreaterThanOrEqual(1000);
  expect(heldBrandOpacity).toBeGreaterThan(0.90);
  expect(heldTaglineOpacity).toBeGreaterThan(0.90);
  expect(heldSplashOpacity).toBeGreaterThan(0.90);

  await expect(splash).toBeHidden({ timeout: 5_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
