const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash mostra o símbolo, faz o texto entrar lentamente e abre após ~2s', async ({ page }) => {
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

  // Assert the CSS choreography rather than sampling one fragile CI timestamp.
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
  expect(timing.markDuration).toBeGreaterThanOrEqual(400);
  expect(timing.brandDelay).toBeGreaterThanOrEqual(400);
  expect(timing.taglineDelay).toBeGreaterThan(timing.brandDelay);
  expect(timing.brandDuration).toBeGreaterThanOrEqual(700);
  expect(timing.taglineDuration).toBeGreaterThanOrEqual(650);
  expect(timing.brandDelay + timing.brandDuration).toBeLessThanOrEqual(1300);
  expect(timing.taglineDelay + timing.taglineDuration).toBeLessThanOrEqual(1600);

  // Full copy settles around 1.5s, then the whole splash releases at ~2.0s.
  await expect(splash).toHaveClass(/vestra-splash--copy-ready/, { timeout: 2_000 });
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.95);
  expect(taglineOpacity).toBeGreaterThan(0.95);

  await expect(splash).toBeHidden({ timeout: 3_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
