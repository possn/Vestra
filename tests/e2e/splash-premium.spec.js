const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash shows mark, then Vestra, then tagline before releasing UI', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  const splash = page.locator('#appLoadingOverlay');
  const mark = page.locator('.vestra-splash__mark img');
  const brand = page.locator('.vestra-splash__brand');
  const tagline = page.locator('.vestra-splash__tagline');

  await expect(splash).toBeVisible();
  await expect(mark).toBeVisible();

  // Copy is intentionally delayed so the mark owns the first beat.
  const earlyBrandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(earlyBrandOpacity).toBeLessThan(0.35);

  await page.waitForTimeout(1350);
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.45);
  await expect(brand).toHaveText('Vestra');

  await page.waitForTimeout(750);
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(taglineOpacity).toBeGreaterThan(0.45);
  await expect(tagline).toHaveText('Finance, made simple.');

  // The legacy app.js early fade must not make the overlay transparent before
  // the full identity sequence has been seen.
  const splashOpacity = await splash.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(splashOpacity).toBeGreaterThan(0.75);

  await expect(splash).toBeHidden({ timeout: 7_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
