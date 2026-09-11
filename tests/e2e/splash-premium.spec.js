const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash é opaco, texto entra lentamente, permanece legível e sai suavemente', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  // Record the real copy-ready transition in page time. Using Date.now() after a
  // Playwright assertion is racy on WebKit because polling can observe the class
  // hundreds of milliseconds after it was actually added.
  await page.addInitScript(() => {
    window.__vestraSplashTimeline = { copyReadyAt: null };
    document.addEventListener('DOMContentLoaded', () => {
      const splash = document.getElementById('appLoadingOverlay');
      if (!splash) return;
      const record = () => {
        if (splash.classList.contains('vestra-splash--copy-ready') && window.__vestraSplashTimeline.copyReadyAt == null) {
          window.__vestraSplashTimeline.copyReadyAt = performance.now();
        }
      };
      record();
      new MutationObserver(record).observe(splash, { attributes: true, attributeFilter: ['class'] });
    }, { once: true });
  });

  // DOMContentLoaded is the correct observation point for launch choreography.
  // Waiting for the full load event can include slow third-party resources and let
  // the intentionally short splash finish before the first assertion on WebKit.
  await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
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

  expect(css.backgroundColor).toBe('rgb(238, 240, 236)');
  expect(css.markDuration).toBeGreaterThanOrEqual(430);
  expect(css.brandDelay).toBeLessThanOrEqual(400);
  expect(css.brandDuration).toBeGreaterThanOrEqual(850);
  expect(css.taglineDelay).toBeGreaterThanOrEqual(760);
  expect(css.taglineDelay).toBeLessThanOrEqual(820);
  expect(css.taglineDelay).toBeGreaterThan(css.brandDelay);
  expect(css.taglineDuration).toBeGreaterThanOrEqual(1100);

  // A tagline termina perto dos 2s; nesse momento o texto deve estar totalmente legível.
  await expect(splash).toHaveClass(/vestra-splash--copy-ready/, { timeout: 2_400 });
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.95);
  expect(taglineOpacity).toBeGreaterThan(0.95);

  // Prove a retenção a partir do instante real em que a classe foi aplicada,
  // não do instante tardio em que o runner acabou de a observar.
  const remainingHoldMs = await page.evaluate(() => {
    const copyReadyAt = window.__vestraSplashTimeline?.copyReadyAt;
    if (!Number.isFinite(copyReadyAt)) return null;
    return Math.max(0, 1600 - (performance.now() - copyReadyAt));
  });
  expect(remainingHoldMs).not.toBeNull();
  if (remainingHoldMs > 0) await page.waitForTimeout(remainingHoldMs);
  await expect(splash).toBeVisible({ timeout: 500 });

  // On a cold WebKit run app readiness may arrive after the nominal choreography;
  // the watchdog is allowed to use its bounded failsafe, but the splash must release.
  await expect(splash).toBeHidden({ timeout: 4_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
