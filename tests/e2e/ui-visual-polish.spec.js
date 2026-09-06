const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: visual polish loads without hiding content and softens secondary cards', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.waitForFunction(() => window.VestraUiVisualPolish?.version === '1.0');

  const style = page.locator('#vestraUiVisualPolishStyle');
  await expect(style).toHaveCount(1);

  const secondary = page.locator('#viewDashboard .card:not(.hero):not(#dashboardWeeklyEventsCard)').first();
  await expect(secondary).toBeVisible();
  const metrics = await secondary.evaluate(el => {
    const cs = getComputedStyle(el);
    return { display: cs.display, visibility: cs.visibility, boxShadow: cs.boxShadow, borderRadius: cs.borderRadius };
  });
  expect(metrics.display).not.toBe('none');
  expect(metrics.visibility).not.toBe('hidden');
  expect(metrics.boxShadow).toBe('none');
  expect(parseFloat(metrics.borderRadius)).toBeGreaterThanOrEqual(16);

  const focusRulePresent = await style.evaluate(el => el.textContent.includes(':focus-visible'));
  expect(focusRulePresent).toBe(true);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
