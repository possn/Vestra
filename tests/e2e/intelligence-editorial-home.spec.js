const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Intelligence 2.0 editorial preview preserves evidence and existing dashboard', async ({page}) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/index.html?vestra2=1');
  // Wait for initial app navigation/hydration rather than racing setView().
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home).toBeVisible();
  const opening = home.locator('.vi-opening');
  await expect(opening).toBeVisible();
  await expect(opening.locator('.vi-lead')).toHaveCount(1);
  await expect(opening.locator('.vi-regime')).toHaveCount(1);
  await expect(opening).toHaveCSS('grid-template-columns', /.+/);
  // The preview must own the app chrome, not merely insert another card.
  await expect(page.locator('body')).toHaveCSS('background-color', /.+/);
  await expect(page.locator('.topbar')).toHaveCSS('background-color', 'rgb(17, 21, 20)');
  await expect(page.locator('.bottomnav')).toHaveCSS('background-color', 'rgb(20, 25, 24)');
  await expect(home.getByText('O essencial, sem ruído.')).toBeVisible();
  await expect(home.getByRole('heading', {name:/Regime de mercado/})).toBeVisible();
  await expect(home.locator('.vi-action')).toHaveCount(3);
  await expect(home.locator('[data-vestra-market-status]')).not.toBeEmpty();
  await expect(home.locator('[data-vestra-portfolio-evidence]')).not.toBeEmpty();
  await expect(home.locator('[data-vestra-decision-state]')).not.toBeEmpty();
  await expect(home.locator('.vi-research-details')).not.toHaveAttribute('open', '');
  await home.locator('.vi-research-details summary').click();
  await expect(home.locator('.vi-research-details')).toHaveAttribute('open', '');
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeHidden();
  await home.locator('[data-vestra-go="dashboard"]').click();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeVisible();
  await page.locator('#btnReturnIntelligence').click();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeHidden();
  await expect(home).toBeVisible();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toHaveCount(1);
  await expect(page.locator('#kpiNet')).toHaveCount(1);
  expect(errors).toEqual([]);
});

test('iPhone/WebKit: Intelligence is default with legacy dashboard preserved', async ({page}) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home).toBeVisible();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeHidden();
  await expect(home.locator('.vi-action')).toHaveCount(3);
  await home.locator('[data-vestra-go="dashboard"]').click();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeVisible();
  await expect(page.locator('#kpiNet')).toHaveCount(1);
  await page.locator('#btnReturnIntelligence').click();
  await expect(home).toBeVisible();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeHidden();
});
test('iPhone/WebKit: explicit legacy rollback disables Intelligence and keeps tools', async ({page}) => {
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  await expect(page.locator('#vestraIntelligenceHome')).toBeHidden();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeVisible();
  await expect(page.locator('#kpiNet')).toHaveCount(1);
  await expect(page.locator('.vi-entry-link a')).toHaveAttribute('href', '?vestra2=0');
});


test('iPhone/WebKit: default Intelligence actions retain Portfolio and Market navigation', async ({page}) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/index.html');
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home).toBeVisible();
  await home.locator('[data-vestra-go="portfolio"]').first().click();
  await expect(page.locator('#viewAssets')).toBeVisible();
  await page.evaluate(() => window.setView('dashboard'));
  await expect(home).toBeVisible();
  await home.locator('[data-vestra-go="market"]').first().click();
  await expect(page.locator('#viewMarket')).toBeVisible();
  await page.evaluate(() => window.setView('dashboard'));
  await expect(home).toBeVisible();
  await home.locator('[data-vestra-go="dashboard"]').click();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeVisible();
  await expect(page.locator('#kpiNet')).toHaveCount(1);
  await expect(page.locator('#btnReturnIntelligence')).toBeVisible();
  await page.locator('#btnReturnIntelligence').click();
  await expect(home).toBeVisible();
  expect(errors).toEqual([]);
});


test('iPhone/WebKit: new editorial chapters keep real-data hosts and legacy escape', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home).toBeVisible();
  await expect(home.locator('.vi-chapter-index')).toHaveCount(3);
  await expect(home.locator('.vi-opening .vi-regime-grid')).toBeVisible();
  await expect(home.locator('.vi-action')).toHaveCount(3);
  await expect(home.locator('[data-vestra-portfolio-evidence]')).toBeAttached();
  await expect(home.locator('[data-vestra-decision-state]')).toBeAttached();
  await expect(home.locator('[data-vestra-coverage]')).toBeAttached();
  const layout = await home.locator('.vi-opening').evaluate(el => ({
    grid: getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean),
    viewport: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth
  }));
  expect(layout.grid).toHaveLength(1);
  expect(layout.scroll).toBeLessThanOrEqual(layout.viewport + 1);
  await home.locator('[data-vestra-go="dashboard"]').click();
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeVisible();
});


test('iPhone/WebKit: useful-first Home opens existing market barometer, news and calendar', async ({page}) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home.locator('.vi-daily-item')).toHaveCount(3);
  for (const id of ['vestraMarketSentimentCard','vestraDailyNewsCard','dashboardWeeklyEventsCard']) {
    await expect(page.locator('#'+id)).toBeAttached();
    await home.locator('[data-vestra-dashboard-section="'+id+'"]').click();
    await expect(page.locator('#'+id)).toBeVisible();
    await page.locator('#btnReturnIntelligence').click();
    await expect(home).toBeVisible();
    await expect(page.locator('#viewDashboard .v2-home-stage')).toBeHidden();
  }
});


test('iPhone/WebKit: Intelligence quick brief exposes real-data slots and honest fallbacks', async ({page}) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home).toBeVisible();
  for (const key of ['market', 'news', 'events']) {
    const brief = home.locator('[data-vi-brief="'+key+'"]');
    await expect(brief).toHaveCount(1);
    await expect(brief).not.toBeEmpty();
  }
  await home.locator('[data-vestra-dashboard-section="vestraDailyNewsCard"]').click();
  await expect(page.locator('#vestraDailyNewsCard')).toBeVisible();
  await page.locator('#btnReturnIntelligence').click();
  await expect(home).toBeVisible();
});
