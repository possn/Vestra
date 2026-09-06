const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash mostra a assinatura cedo e mantém-na legível antes de abrir', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  const splash = page.locator('#appLoadingOverlay');
  const mark = page.locator('.vestra-splash__mark img');
  const brand = page.locator('.vestra-splash__brand');
  const tagline = page.locator('.vestra-splash__tagline');

  await expect(splash).toBeVisible();
  await expect(mark).toBeVisible();

  const earlyBrandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(earlyBrandOpacity).toBeLessThan(0.35);

  // Brand and tagline must arrive well before the release phase.
  await page.waitForTimeout(900);
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.70);
  await expect(brand).toHaveText('Vestra');

  await page.waitForTimeout(650);
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(taglineOpacity).toBeGreaterThan(0.90);
  await expect(tagline).toHaveText('Finance, made simple.');
  await expect(splash).toHaveClass(/vestra-splash--copy-ready/);

  // Regression guard: the complete copy remains readable for roughly two seconds
  // instead of appearing only during the final fade.
  await page.waitForTimeout(1200);
  await expect(splash).toBeVisible();
  const heldBrandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const heldTaglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  const heldSplashOpacity = await splash.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(heldBrandOpacity).toBeGreaterThan(0.95);
  expect(heldTaglineOpacity).toBeGreaterThan(0.95);
  expect(heldSplashOpacity).toBeGreaterThan(0.95);

  await expect(splash).toBeHidden({ timeout: 5_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
