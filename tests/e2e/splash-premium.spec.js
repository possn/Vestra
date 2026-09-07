const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash mostra primeiro o símbolo, depois o texto, segura e abre a app', async ({ page }) => {
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

  // The choreography is defined relative to the premium watchdog start, not to
  // page.goto() completion. Assert the actual CSS timeline so slow CI loading
  // cannot make the test sample the wrong animation phase.
  const timing = await page.evaluate(() => {
    const markStyle = getComputedStyle(document.querySelector('.vestra-splash__mark'));
    const brandStyle = getComputedStyle(document.querySelector('.vestra-splash__brand'));
    const taglineStyle = getComputedStyle(document.querySelector('.vestra-splash__tagline'));
    return {
      markDuration: parseFloat(markStyle.animationDuration) * 1000,
      brandDelay: parseFloat(brandStyle.animationDelay) * 1000,
      brandDuration: parseFloat(brandStyle.animationDuration) * 1000,
      taglineDelay: parseFloat(taglineStyle.animationDelay) * 1000,
      taglineDuration: parseFloat(taglineStyle.animationDuration) * 1000,
    };
  });
  expect(timing.markDuration).toBeGreaterThanOrEqual(700);
  expect(timing.brandDelay).toBeGreaterThan(timing.markDuration);
  expect(timing.taglineDelay).toBeGreaterThan(timing.brandDelay);
  expect(timing.brandDelay + timing.brandDuration).toBeLessThanOrEqual(1700);
  expect(timing.taglineDelay + timing.taglineDuration).toBeLessThanOrEqual(2000);

  // The complete identity settles by ~2s and remains readable for >1s before release.
  await expect(splash).toHaveClass(/vestra-splash--copy-ready/, { timeout: 2_500 });
  const settledAt = Date.now();
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.95);
  expect(taglineOpacity).toBeGreaterThan(0.95);

  await page.waitForTimeout(900);
  if (Date.now() - settledAt < 1000) {
    await expect(splash).toBeVisible();
  }

  await expect(splash).toBeHidden({ timeout: 5_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
