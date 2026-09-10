const { test, expect } = require('@playwright/test');

async function assertNoHorizontalOverflow(page) {
  const geometry = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));
  expect(geometry.scrollWidth, `document overflow at ${geometry.innerWidth}px`).toBeLessThanOrEqual(geometry.innerWidth + 1);
  expect(geometry.bodyScrollWidth, `body overflow at ${geometry.innerWidth}px`).toBeLessThanOrEqual(geometry.innerWidth + 1);
}

test('iPhone/WebKit: portrait -> landscape -> portrait keeps Market and dossier usable', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function' && !!window.VestraMobileUiRefresh);
  await page.evaluate(() => window.setView('market'));

  await expect(page.locator('#viewMarket')).toBeVisible();
  await expect(page.locator('#marketSearch')).toBeVisible();
  await assertNoHorizontalOverflow(page);

  // Exercise the portrait drawer before rotating, so a stale transform/backdrop
  // cannot survive the responsive transition.
  await page.locator('#btnSidebarToggle').click();
  await expect(page.locator('#sidebar')).toHaveClass(/sidebar--open/);
  await page.locator('#btnSidebarClose').click();
  await expect(page.locator('#sidebar')).not.toHaveClass(/sidebar--open/);

  const search = page.locator('#marketSearch');
  await search.fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', 'MSFT');

  await page.setViewportSize({ width: 852, height: 393 });
  await expect(page.locator('#viewMarket')).toBeVisible();
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('MSFT');
  await assertNoHorizontalOverflow(page);

  const valuationTab = sheet.locator('[data-detail-tab="valuation"]');
  await valuationTab.click();
  await expect(valuationTab).toHaveClass(/is-active/);
  await expect(sheet.locator('#marketDetailBody')).not.toBeEmpty();

  await page.setViewportSize({ width: 393, height: 852 });
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('MSFT');
  await expect(valuationTab).toHaveClass(/is-active/);
  await assertNoHorizontalOverflow(page);

  // Returning to portrait must restore a functional drawer and preserve the
  // dossier rather than resetting the Market view.
  await page.locator('#btnSidebarToggle').click();
  await expect(page.locator('#sidebar')).toHaveClass(/sidebar--open/);
  await expect(page.locator('#sidebarBackdrop')).toBeVisible();
  await page.locator('#btnSidebarClose').click();
  await expect(page.locator('#sidebar')).not.toHaveClass(/sidebar--open/);
  await expect(sheet).toBeVisible();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
