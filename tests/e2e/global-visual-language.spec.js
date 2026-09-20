const { test, expect } = require('@playwright/test');

test.use({ serviceWorkers: 'block' });

test('iPhone/WebKit: youthful premium language stays contained across primary views', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);

  for (const [view, intro] of [
    ['dividends', '.view-intro--dividends'],
    ['analysis', '.view-intro--analysis'],
  ]) {
    await page.evaluate(next => setView(next), view);
    const header = page.locator(intro);
    await expect(header).toBeVisible();
    const metrics = await header.evaluate(el => {
      const style = getComputedStyle(el);
      return {
        radius: parseFloat(style.borderRadius),
        width: el.getBoundingClientRect().width,
        viewport: document.documentElement.clientWidth,
      };
    });
    expect(metrics.radius).toBeGreaterThanOrEqual(18);
    expect(metrics.width).toBeLessThanOrEqual(metrics.viewport);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  }

  await expect(page.locator('.bottomnav')).toBeVisible();
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
