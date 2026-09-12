const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: splash runs one entrance, remains legible and exits smoothly', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  // Observe launch choreography from the earliest possible page time. The regression
  // we are guarding against changed animation-name after the deferred UI module ran,
  // causing WebKit/iOS to start a second visual entrance.
  await page.addInitScript(() => {
    window.__vestraSplashTimeline = { copyReadyAt: null, animationStarts: [] };
    document.addEventListener('animationstart', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (!target.closest('#appLoadingOverlay')) return;
      window.__vestraSplashTimeline.animationStarts.push({
        name: event.animationName,
        at: performance.now(),
        className: target.className || '',
      });
    }, true);
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
      markAnimation: markStyle.animationName,
      markDuration: parseFloat(markStyle.animationDuration) * 1000,
      brandAnimation: brandStyle.animationName,
      brandDelay: parseFloat(brandStyle.animationDelay) * 1000,
      brandDuration: parseFloat(brandStyle.animationDuration) * 1000,
      taglineAnimation: taglineStyle.animationName,
      taglineDelay: parseFloat(taglineStyle.animationDelay) * 1000,
      taglineDuration: parseFloat(taglineStyle.animationDuration) * 1000,
    };
  });

  expect(css.backgroundColor).toBe('rgb(238, 240, 236)');
  expect(css.markAnimation).toContain('vestraMarkIn');
  expect(css.markAnimation).not.toContain('vestraPremium');
  expect(css.markDuration).toBeGreaterThanOrEqual(700);
  expect(css.markDuration).toBeLessThanOrEqual(760);
  expect(css.brandAnimation).toContain('vestraCopyIn');
  expect(css.brandAnimation).not.toContain('vestraPremium');
  expect(css.brandDelay).toBeGreaterThanOrEqual(120);
  expect(css.brandDelay).toBeLessThanOrEqual(180);
  expect(css.brandDuration).toBeGreaterThanOrEqual(520);
  expect(css.brandDuration).toBeLessThanOrEqual(580);
  expect(css.taglineAnimation).toContain('vestraCopyIn');
  expect(css.taglineAnimation).not.toContain('vestraPremium');
  expect(css.taglineDelay).toBeGreaterThanOrEqual(200);
  expect(css.taglineDelay).toBeLessThanOrEqual(250);
  expect(css.taglineDelay).toBeGreaterThan(css.brandDelay);
  expect(css.taglineDuration).toBeGreaterThanOrEqual(520);
  expect(css.taglineDuration).toBeLessThanOrEqual(580);

  // Let all entrance starts fire, then prove that no second premium family appeared
  // and that the mark itself started exactly once.
  await page.waitForTimeout(900);
  const starts = await page.evaluate(() => window.__vestraSplashTimeline?.animationStarts || []);
  const names = starts.map(item => item.name);
  expect(names.some(name => String(name).startsWith('vestraPremium'))).toBe(false);
  expect(names.filter(name => name === 'vestraMarkIn')).toHaveLength(1);
  expect(names.filter(name => name === 'vestraCopyIn')).toHaveLength(2);

  // app-ui-core owns the hold/release contract without replacing animation names.
  await expect(splash).toHaveClass(/vestra-splash--copy-ready/, { timeout: 2_400 });
  const brandOpacity = await brand.evaluate(node => Number(getComputedStyle(node).opacity));
  const taglineOpacity = await tagline.evaluate(node => Number(getComputedStyle(node).opacity));
  expect(brandOpacity).toBeGreaterThan(0.95);
  expect(taglineOpacity).toBeGreaterThan(0.95);

  const remainingHoldMs = await page.evaluate(() => {
    const copyReadyAt = window.__vestraSplashTimeline?.copyReadyAt;
    if (!Number.isFinite(copyReadyAt)) return null;
    return Math.max(0, 1600 - (performance.now() - copyReadyAt));
  });
  expect(remainingHoldMs).not.toBeNull();
  if (remainingHoldMs > 0) await page.waitForTimeout(remainingHoldMs);
  await expect(splash).toBeVisible({ timeout: 500 });

  await expect(splash).toBeHidden({ timeout: 4_000 });
  await expect(page.locator('#viewDashboard')).toBeVisible();
  expect(errors, `Browser page errors: ${errors.join(' | ')}`).toEqual([]);
});
