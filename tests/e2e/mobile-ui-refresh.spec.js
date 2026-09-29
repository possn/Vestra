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


test('iPhone/WebKit: fixed navigation uses the low-compositing fast path and switches view synchronously', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');

  const chrome = await page.evaluate(() => {
    const top = getComputedStyle(document.querySelector('.topbar'));
    const bottom = getComputedStyle(document.querySelector('.bottomnav'));
    return {
      topBackdrop: top.webkitBackdropFilter || top.backdropFilter || 'none',
      bottomBackdrop: bottom.webkitBackdropFilter || bottom.backdropFilter || 'none',
    };
  });
  expect(chrome.topBackdrop).toBe('none');
  expect(chrome.bottomBackdrop).toBe('none');

  const timings = await page.evaluate(() => {
    const run = id => {
      const button = document.getElementById(id);
      const before = performance.now();
      button.click();
      const after = performance.now();
      return { elapsed: after - before, view: document.body.dataset.view };
    };
    return {
      assets: run('navAssets'),
      home: run('navDashboard'),
      more: run('navSettings'),
    };
  });
  expect(timings.assets.view).toBe('assets');
  expect(timings.home.view).toBe('dashboard');
  expect(timings.more.view).toBe('settings');
  expect(Math.max(timings.assets.elapsed, timings.home.elapsed, timings.more.elapsed)).toBeLessThan(50);

  await page.locator('#btnSearchToggle').click();
  await expect(page.locator('#searchBar')).toBeVisible();
  await page.locator('#btnSidebarToggle').click();
  await expect(page.locator('#sidebar')).toHaveClass(/sidebar--open/);
});
