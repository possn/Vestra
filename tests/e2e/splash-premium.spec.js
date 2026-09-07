const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash é opaco, texto entra cedo e saída é suave', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  await page.goto('/index.html');
  const splash = page.locator('#appLoadingOverlay');
  const mark = page.locator('.vestra-splash__mark');
  const brand = page.locator('.vestra-splash__brand');
  const tagline = page.locator('.vestra-splash__tagline');

  await expect(splash).toBeVisible();
  await expect(mark).toBeVisible();
  await expect(brand).toHaveText('Vestra');
  await expect(tagline).toHaveText('Finance, made simple.');

  const css = await page.evaluate(() => {
    const splashStyle = getComputedStyle(document.querySelector('#appLoadingOverlay'));
    const markStyle = getComputedStyle(document.querySelector('.vestra-splash__mark'));
    const brandStyle = getComputedStyle(document.querySelector('.vestra-splash__brand'));
    const taglineStyle = getComputedStyle(document.querySelector('.vestra-splash__tagline'));
    return {
      backgroundColor: splashStyle.backgroundColor,
      markDuration: parseFloat(markStyle.animationDuration) * 1000,
      brandDelay: parseFloat(brandStyle.animationDelay) * 1000,
      brandDuration: parseFloat(brandStyle.animationDuration) * 1000,
      taglineDelay: parseFloat(taglineStyle.animationDelay) * 1000,
      taglineDuration: parseFloat(taglineStyle.animationDuration) * 1000,
    };
  });

  // O fundo tem de ser sólido: o Dashboard nunca pode ser visível por trás.
  expect(css.backgroundColor).toBe('rgb(238, 240, 236)');

  // Copy starts much earlier than the previous 0.82s/1.18s delays, but still fades in slowly.
  expect(css.markDuration).toBeGreaterThanOrEqual(430);
  expect(css.brandDelay).toBeLessThanOrEqual(400);
  expect(css.brandDuration).toBeGreaterThanOrEqual(780);
  expect(css.taglineDelay).toBeLessThanOrEqual(760);
  expect(css.taglineDelay).toBeGreaterThan(css.brandDelay);
  expect(css.taglineDuration).toBeGreaterThanOrEqual(740);

  await expect(splash).toHaveClass(/vestra-splash--copy-ready/, { timeout: 2_000 });
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.95);
  expect(taglineOpacity).toBeGreaterThan(0.95);

  // The release begins at ~2s but takes ~0.7s, avoiding the abrupt disappearance.
  await expect(splash).toBeHidden({ timeout: 3_500 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
