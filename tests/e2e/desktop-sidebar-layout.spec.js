const { test, expect } = require('@playwright/test');

test('desktop: fixed sidebar reserves its own column without covering app content', async ({ page }) => {
  await page.setViewportSize({ width: 920, height: 820 });
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);

  const sidebar = page.locator('#sidebar');
  const main = page.locator('main.main');
  const topbar = page.locator('.topbar');
  const sidebarClose = page.locator('#btnSidebarClose');

  await expect(sidebar).toBeVisible();
  await expect(main).toBeVisible();
  await expect(topbar).toBeVisible();
  await expect(sidebarClose).toBeHidden();

  const [sidebarBox, mainBox, topbarBox] = await Promise.all([
    sidebar.boundingBox(),
    main.boundingBox(),
    topbar.boundingBox(),
  ]);

  expect(sidebarBox).toBeTruthy();
  expect(mainBox).toBeTruthy();
  expect(topbarBox).toBeTruthy();

  const sidebarRight = sidebarBox.x + sidebarBox.width;
  const mainRight = mainBox.x + mainBox.width;
  const topbarRight = topbarBox.x + topbarBox.width;

  expect(mainBox.x).toBeGreaterThanOrEqual(sidebarRight + 20);
  expect(mainRight).toBeLessThanOrEqual(920);
  expect(topbarBox.x).toBeGreaterThanOrEqual(sidebarRight);
  expect(topbarRight).toBeLessThanOrEqual(920);

  // Narrow desktop windows must shrink the content surface rather than crop it.
  expect(mainBox.width).toBeLessThan(680);
  expect(mainBox.width).toBeGreaterThan(500);
});
