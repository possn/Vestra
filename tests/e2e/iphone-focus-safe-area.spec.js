const { test, expect } = require('@playwright/test');

async function isolateExternalSearch(page) {
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ quotes: [], news: [], lists: [] }),
    });
  });
}

async function assertNoHorizontalOverflow(page) {
  const geometry = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    doc: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(geometry.doc).toBeLessThanOrEqual(geometry.innerWidth + 1);
  expect(geometry.body).toBeLessThanOrEqual(geometry.innerWidth + 1);
}

test('iPhone/WebKit: focus, constrained viewport and safe-area chrome stay usable', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await isolateExternalSearch(page);

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function' && !!window.VestraMobileUiRefresh);

  // Guard the source-level iPhone contracts. Desktop WebKit does not emulate a
  // physical notch or the software keyboard, so these assertions complement the
  // runtime geometry checks below rather than pretending to reproduce real iOS.
  const safeAreaContracts = await page.evaluate(async () => {
    const [index, styles, market] = await Promise.all([
      fetch('/index.html').then(r => r.text()),
      fetch('/styles.css').then(r => r.text()),
      fetch('/market.css').then(r => r.text()),
    ]);
    return {
      viewportFitCover: /viewport-fit=cover/.test(index),
      mainBottomInset: /\.main\s*\{[^}]*safe-area-inset-bottom/s.test(styles),
      bottomNavInset: /\.bottomnav\s*\{[^}]*safe-area-inset-bottom/s.test(styles),
      passiveBarInset: /\.passivebar\s*\{[^}]*safe-area-inset-bottom/s.test(styles),
      sidebarTopInset: /\.sidebar\s*\{[^}]*safe-area-inset-top/s.test(styles),
      modalInsets: /\.modal__box[^}]*safe-area-inset-top[^}]*safe-area-inset-bottom/s.test(styles),
      marketSheetBottomInset: /\.market-sheet__panel\s*\{[^}]*safe-area-inset-bottom/s.test(market),
    };
  });
  expect(safeAreaContracts).toEqual({
    viewportFitCover: true,
    mainBottomInset: true,
    bottomNavInset: true,
    passiveBarInset: true,
    sidebarTopInset: true,
    modalInsets: true,
    marketSheetBottomInset: true,
  });

  await page.evaluate(() => window.setView('market'));
  const search = page.locator('#marketSearch');
  await expect(search).toBeVisible();
  await search.focus();
  await expect(search).toBeFocused();

  // Approximate the geometry pressure created by the iOS keyboard by reducing
  // the visible viewport while the field is focused. This is intentionally not
  // described as software-keyboard emulation.
  await page.setViewportSize({ width: 393, height: 430 });
  await search.evaluate(el => el.scrollIntoView({ block: 'center' }));

  const focusedGeometry = await search.evaluate(el => {
    const r = el.getBoundingClientRect();
    return { top: r.top, bottom: r.bottom, innerHeight: window.innerHeight };
  });
  expect(focusedGeometry.top).toBeGreaterThanOrEqual(0);
  expect(focusedGeometry.bottom).toBeLessThanOrEqual(focusedGeometry.innerHeight);
  await assertNoHorizontalOverflow(page);

  const fixedChrome = await page.evaluate(() => {
    const nav = document.querySelector('.bottomnav');
    const navRect = nav?.getBoundingClientRect();
    return {
      navVisible: !!nav && getComputedStyle(nav).display !== 'none',
      navLeft: navRect?.left ?? 0,
      navRight: navRect?.right ?? 0,
      innerWidth: window.innerWidth,
    };
  });
  expect(fixedChrome.navVisible).toBe(true);
  expect(fixedChrome.navLeft).toBeGreaterThanOrEqual(-1);
  expect(fixedChrome.navRight).toBeLessThanOrEqual(fixedChrome.innerWidth + 1);

  // Restore full portrait height and verify normal Market interaction survived
  // the constrained viewport/focus cycle.
  await page.setViewportSize({ width: 393, height: 852 });
  await search.fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  const panelGeometry = await sheet.locator('.market-sheet__panel').evaluate(el => {
    const r = el.getBoundingClientRect();
    return { top: r.top, bottom: r.bottom, innerHeight: window.innerHeight };
  });
  expect(panelGeometry.top).toBeGreaterThanOrEqual(-1);
  expect(panelGeometry.bottom).toBeLessThanOrEqual(panelGeometry.innerHeight + 1);
  await assertNoHorizontalOverflow(page);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
