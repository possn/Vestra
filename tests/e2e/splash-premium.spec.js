const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash mostra primeiro o símbolo, depois o texto, segura e abre a app', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  const splash = page.locator('#appLoadingOverlay');
  const mark = page.locator('.vestra-splash__mark img');
  const brand = page.locator('.vestra-splash__brand');
  const tagline = page.locator('.vestra-splash__tagline');

  await expect(splash).toBeVisible();
  await expect(mark).toBeVisible();

  // First phase: identity mark only. Copy must not compete with the symbol.
  await page.waitForTimeout(450);
  const markOpacity = await mark.evaluate(node => Number(getComputedStyle(node.parentElement).opacity));
  const earlyBrandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const earlyTaglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(markOpacity).toBeGreaterThan(0.70);
  expect(earlyBrandOpacity).toBeLessThan(0.12);
  expect(earlyTaglineOpacity).toBeLessThan(0.08);

  // Second phase: copy enters only after the mark reveal has completed.
  await page.waitForTimeout(950);
  const enteringBrandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const enteringTaglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(enteringBrandOpacity).toBeGreaterThan(0.65);
  expect(enteringTaglineOpacity).toBeGreaterThan(0.18);
  await expect(brand).toHaveText('Vestra');
  await expect(tagline).toHaveText('Finance, made simple.');

  // By about 2 seconds the complete copy is settled.
  await page.waitForTimeout(650);
  await expect(splash).toHaveClass(/vestra-splash--copy-ready/);
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.95);
  expect(taglineOpacity).toBeGreaterThan(0.95);

  // Deliberate quiet hold after the text is fully readable: roughly 1–2 seconds.
  await page.waitForTimeout(950);
  await expect(splash).toBeVisible();
  const heldSplashOpacity = await splash.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(heldSplashOpacity).toBeGreaterThan(0.95);

  await expect(splash).toBeHidden({ timeout: 5_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
