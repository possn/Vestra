const { test, expect } = require('@playwright/test');

// Geometry tests must exercise the CSS from this checkout, not a previously
// controlled shell cache. Service-worker cache behaviour has its own contracts.
test.use({ serviceWorkers: 'block' });

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

  // Search belongs to the desktop content column, never underneath the sidebar.
  await page.locator('#btnSearchToggle').click();
  const searchBar = page.locator('#searchBar');
  await expect(searchBar).toBeVisible();
  const searchBox = await searchBar.boundingBox();
  expect(searchBox.x).toBeGreaterThanOrEqual(sidebarRight);
  expect(searchBox.x + searchBox.width).toBeLessThanOrEqual(920);

  // Modal panels and transient toast use the same content-column centre.
  await page.evaluate(() => {
    document.getElementById('modalItem')?.setAttribute('aria-hidden', 'false');
    let toast = document.getElementById('toastEl');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toastEl';
      document.body.appendChild(toast);
    }
    toast.textContent = 'Teste';
    toast.classList.add('toast--show');
  });

  const modal = page.locator('#modalItem .modal__panel');
  const toast = page.locator('#toastEl');
  await expect(modal).toBeVisible();
  const [modalBox, toastBox] = await Promise.all([
    modal.boundingBox(),
    toast.boundingBox(),
  ]);

  expect(modalBox.x).toBeGreaterThanOrEqual(sidebarRight + 20);
  expect(modalBox.x + modalBox.width).toBeLessThanOrEqual(920);
  expect(toastBox.x).toBeGreaterThanOrEqual(sidebarRight);
  expect(toastBox.x + toastBox.width).toBeLessThanOrEqual(920);
});
