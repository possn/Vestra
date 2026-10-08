const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Intelligence 2.0 editorial preview preserves evidence and existing dashboard', async ({page}) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/index.html?vestra2=1');
  // Wait for initial app navigation/hydration rather than racing setView().
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home).toBeVisible();
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

test('iPhone/WebKit: legacy dashboard remains the default without preview flag', async ({page}) => {
  await page.goto('/index.html');
  // Wait for initial app navigation/hydration rather than racing setView().
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  await expect(page.locator('#vestraIntelligenceHome')).toBeHidden();
  await page.waitForFunction(() => document.getElementById('viewDashboard')?.hidden === false);
  const entry = page.locator('.vi-entry-link a');
  await expect(entry).toBeVisible();
  await expect(entry).toHaveAttribute('href', '?vestra2=1');
  await expect(page.locator('#viewDashboard .v2-home-stage')).toBeVisible();
});
