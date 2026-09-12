const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: visual polish loads without hiding expanded content and softens secondary cards', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.waitForFunction(() => window.VestraUiVisualPolish?.version === '1.1');
  await page.evaluate(() => {
    // Analytical Dashboard cards are intentionally suppressed in the first-run
    // empty state. Seed one local asset so this test exercises the expanded
    // secondary-card styling rather than onboarding visibility rules.
    try {
      state.assets = [{
        id: 'e2e-visual-polish-cash',
        name: 'E2E Visual Polish Cash',
        type: 'cash',
        value: 1000,
        currency: 'EUR',
      }];
      if (typeof renderDashboard === 'function') renderDashboard();
    } catch (_) {}
    document.getElementById('viewDashboard')?.classList.add('dash-secondary-open');
    window.VestraDashboardUiRefresh?.refresh?.();
  });

  const style = page.locator('#vestraUiVisualPolishStyle');
  await expect(style).toHaveCount(1);
  await expect(style).toHaveAttribute('rel', 'stylesheet');
  await expect(style).toHaveAttribute('href', /ui-visual-polish\.css\?v=1\.0$/);
  await page.waitForFunction(() => {
    const link = document.getElementById('vestraUiVisualPolishStyle');
    return Boolean(link?.sheet && link.sheet.cssRules?.length);
  });

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

  const focusRulePresent = await page.evaluate(() => {
    const link = document.getElementById('vestraUiVisualPolishStyle');
    const rules = link?.sheet?.cssRules ? Array.from(link.sheet.cssRules) : [];
    return rules.some(rule => rule.cssText.includes(':focus-visible'));
  });
  expect(focusRulePresent).toBe(true);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
