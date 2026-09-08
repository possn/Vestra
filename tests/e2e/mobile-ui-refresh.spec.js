const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: portrait topbar exposes the sidebar and More keeps key shortcuts', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraMobileUiRefresh));

  await expect(page.locator('#btnSidebarToggle')).toBeVisible();
  await expect(page.locator('#btnSettingsNav')).toBeHidden();
  await expect(page.locator('#btnSearchToggle')).toBeVisible();
  await expect(page.locator('#btnFab')).toBeVisible();
  await expect(page.locator('.topbar .brand')).toBeVisible();

  await page.locator('#btnSidebarToggle').click();
  await expect(page.locator('#sidebar')).toHaveClass(/sidebar--open/);
  await expect(page.locator('#btnSidebarToggle')).toHaveAttribute('aria-expanded', 'true');
  await page.locator('#btnSidebarClose').click();
  await expect(page.locator('#sidebar')).not.toHaveClass(/sidebar--open/);

  await page.locator('#navSettings').click();
  const shortcuts = page.locator('#vestraMoreShortcuts');
  await expect(shortcuts).toBeVisible();
  for (const label of ['Dividendos', 'Análise', 'Importar', 'Backup']) {
    await expect(shortcuts).toContainText(label);
  }

  await shortcuts.locator('[data-ui-shortcut="dividends"]').click();
  await expect(page.locator('#viewDividends')).toBeVisible();

  await page.locator('#navSettings').click();
  await page.waitForTimeout(50);
  await page.locator('#vestraMoreShortcuts [data-ui-shortcut="analysis"]').click();
  await expect(page.locator('#viewAnalysis')).toBeVisible();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
