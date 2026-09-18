const { test, expect } = require('@playwright/test');

test('desktop: fixed sidebar reserves its own column without covering app content', async ({ page }) => {
  await page.setViewportSize({ width: 920, height: 820 });
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);

  const sidebar = page.locator('#sidebar');
  const main = page.locator('main.main');
  const topbar = page.locator('.topbar');
  const sidebarClose = page.locator('#btnSidebarClose');
  const searchToggle = page.locator('#btnSearchToggle');
  const searchBar = page.locator('#searchBar');

  await expect(sidebar).toBeVisible();
  await expect(main).toBeVisible();
  await expect(topbar).toBeVisible();
  await expect(sidebarClose).toBeHidden();

  await searchToggle.click();
  await expect(searchBar).toBeVisible();

  const [sidebarBox, mainBox, topbarBox, searchBarBox] = await Promise.all([
    sidebar.boundingBox(),
    main.boundingBox(),
    topbar.boundingBox(),
    searchBar.boundingBox(),
  ]);

  expect(sidebarBox).toBeTruthy();
  expect(mainBox).toBeTruthy();
  expect(topbarBox).toBeTruthy();
  expect(searchBarBox).toBeTruthy();

  const sidebarRight = sidebarBox.x + sidebarBox.width;
  const mainRight = mainBox.x + mainBox.width;
  const topbarRight = topbarBox.x + topbarBox.width;
  const searchBarRight = searchBarBox.x + searchBarBox.width;

  expect(mainBox.x).toBeGreaterThanOrEqual(sidebarRight + 20);
  expect(mainRight).toBeLessThanOrEqual(920);
  expect(topbarBox.x).toBeGreaterThanOrEqual(sidebarRight);
  expect(topbarRight).toBeLessThanOrEqual(920);
  expect(searchBarBox.x).toBeGreaterThanOrEqual(sidebarRight);
  expect(searchBarRight).toBeLessThanOrEqual(920);

  // Narrow desktop windows must shrink the content surface rather than crop it.
  expect(mainBox.width).toBeLessThan(680);
  expect(mainBox.width).toBeGreaterThan(500);
});
