const { test, expect } = require('@playwright/test');

// Guard the canonical Intelligence Home against duplicate headings injected by
// the older Dashboard UI Refresh module. Preserve the opt-out classic Dashboard.
test('iPhone/WebKit: Intelligence patrimony never duplicates the daily brief', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({ timeout: 20000 });
  await page.waitForFunction(() => window.VestraDashboardUiRefresh?.version === '1.9');

  // The asynchronous dashboard refresh and the explicit refresh share a gate.
  await page.evaluate(() => window.VestraDashboardUiRefresh.refresh());
  await page.locator('#vestraIntelligenceHome button[data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toBeHidden();
  await page.evaluate(() => window.VestraDashboardUiRefresh.refresh());
  for (const id of ['dashboardTodayHeading', 'dashboardTodayBrief', 'dashboardPortfolioHeading']) {
    await expect(page.locator('#' + id)).toHaveCount(0);
  }
  // Real dashboard cards survive; no data or navigation nodes are removed.
  await expect(page.locator('#viewDashboard .kpi-quick')).toHaveCount(1);
  await expect(page.locator('#v2-history-disclosure')).toHaveCount(1);
  expect(errors).toEqual([]);
});

test('iPhone/WebKit: classic Dashboard retains its original editorial reading', async ({ page }) => {
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => window.VestraDashboardUiRefresh?.version === '1.9');
  await page.evaluate(() => window.VestraDashboardUiRefresh.refresh());
  await expect(page.locator('#dashboardTodayHeading')).toHaveCount(1);
  await expect(page.locator('#dashboardTodayBrief')).toHaveCount(1);
  await expect(page.locator('#dashboardPortfolioHeading')).toHaveCount(1);
});
