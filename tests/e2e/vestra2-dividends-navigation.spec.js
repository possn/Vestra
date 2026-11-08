const { test, expect } = require('@playwright/test');
test.use({ serviceWorkers: 'block' });

test('iPhone dividend modes remain readable and do not compress to four tiny columns', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);
  await page.evaluate(() => setView('dividends'));
  const rail = page.locator('#viewDividends > .dividend-mode-tabs');
  await expect(rail).toBeVisible();
  const info = await rail.evaluate(el => {
    const buttons = [...el.querySelectorAll('.seg__btn')];
    const bounds = el.getBoundingClientRect();
    return {
      containerWidth: bounds.width, viewportWidth: document.documentElement.clientWidth,
      display: getComputedStyle(el).display, overflowX: getComputedStyle(el).overflowX,
      scrollWidth: el.scrollWidth, clientWidth: el.clientWidth,
      buttonWidths: buttons.map(b => b.getBoundingClientRect().width),
      buttonHeights: buttons.map(b => b.getBoundingClientRect().height),
      buttonCount: buttons.length
    };
  });
  expect(info.buttonCount).toBe(4);
  expect(info.display).toBe('flex');
  expect(['auto', 'scroll']).toContain(info.overflowX);
  expect(info.containerWidth).toBeLessThanOrEqual(info.viewportWidth + 1);
  expect(info.buttonWidths.every(w => w >= 100)).toBe(true);
  expect(info.buttonHeights.every(h => h >= 44)).toBe(true);
  expect(info.scrollWidth).toBeGreaterThan(info.clientWidth);
  await rail.locator('#segDivMonthly').click();
  await expect(rail.locator('#segDivMonthly')).toHaveClass(/seg__btn--active/);
  await rail.locator('#segDivDetail').click();
  await expect(rail.locator('#segDivDetail')).toHaveClass(/seg__btn--active/);
});
