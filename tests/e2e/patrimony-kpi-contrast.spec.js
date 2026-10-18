const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: patrimony KPI text follows its real dark/light surface', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({ timeout: 20000 });
  await page.locator('#vestraIntelligenceHome button[data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#viewDashboard .kpi-quick')).toBeVisible();
  const samples = await page.evaluate(() => {
    const selectors = [
      ['dark-income-title', '.kpi-quick__cell--income .kpi-income__head span', 'light'],
      ['dark-income-amount', '.kpi-quick__cell--income .kpi-income__values strong', 'light'],
      ['dark-income-label', '.kpi-quick__cell--income .kpi-income__values small', 'light'],
      ['ivory-dividends-value', '.kpi-quick__cell--vio .kpi-quick__v', 'dark'],
      ['ivory-yield-value', '.kpi-quick__cell--amber .kpi-quick__v', 'dark'],
      ['ivory-realized-value', '.kpi-quick__cell--purple .kpi-quick__v', 'dark'],
    ];
    return selectors.map(([name, selector, tone]) => {
      const el = document.querySelector('#viewDashboard ' + selector);
      if (!el) return { name, missing: true };
      const st = getComputedStyle(el);
      const paint = st.webkitTextFillColor && st.webkitTextFillColor !== 'currentcolor'
        ? st.webkitTextFillColor : st.color;
      const numbers = paint.match(/[0-9]+/g)?.slice(0, 3).map(Number);
      return { name, tone, paint, numbers, opacity: Number(st.opacity) };
    });
  });
  for (const sample of samples) {
    expect(sample.missing, sample.name).toBeFalsy();
    expect(sample.opacity, sample.name).toBeGreaterThanOrEqual(.99);
    expect(sample.numbers?.length, sample.name).toBe(3);
    if (sample.tone === 'light') expect(Math.min(...sample.numbers), sample.name).toBeGreaterThan(150);
    else expect(Math.max(...sample.numbers), sample.name).toBeLessThan(115);
  }
});
