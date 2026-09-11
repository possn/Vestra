const { test, expect } = require('@playwright/test');

async function openMarket(page) {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => window.VestraMarketAnalysisToolsRuntime && window.VestraMarketStaticUniverse);
  await page.evaluate(() => window.VestraMarket.ensureLoaded());
  await expect(page.locator('.market-analysis-tools')).toBeVisible({ timeout: 15_000 });
}

async function expectMobileSheetGeometry(page, tool) {
  const sheet = page.locator('#marketSheet');
  const panel = sheet.locator('.market-sheet__panel');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-tool', tool);
  await expect(page.locator('body')).toHaveClass(/modal-open/);

  const geometry = await sheet.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    const panel = el.querySelector('.market-sheet__panel');
    const panelRect = panel?.getBoundingClientRect();
    return {
      left: rect.left,
      right: rect.right,
      top: rect.top,
      bottom: rect.bottom,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      overflowY: getComputedStyle(el).overflowY,
      scrollHeight: el.scrollHeight,
      clientHeight: el.clientHeight,
      panelLeft: panelRect?.left ?? 0,
      panelRight: panelRect?.right ?? 0,
      bodyOverflow: document.body.scrollWidth - window.innerWidth,
      docOverflow: document.documentElement.scrollWidth - window.innerWidth,
    };
  });

  expect(geometry.left).toBeGreaterThanOrEqual(-1);
  expect(geometry.right).toBeLessThanOrEqual(geometry.viewportWidth + 1);
  expect(geometry.top).toBeGreaterThanOrEqual(-1);
  expect(geometry.bottom).toBeLessThanOrEqual(geometry.viewportHeight + 1);
  expect(['auto', 'scroll']).toContain(geometry.overflowY);
  expect(geometry.panelLeft).toBeGreaterThanOrEqual(-1);
  expect(geometry.panelRight).toBeLessThanOrEqual(geometry.viewportWidth + 1);
  expect(geometry.bodyOverflow).toBeLessThanOrEqual(1);
  expect(geometry.docOverflow).toBeLessThanOrEqual(1);

  await sheet.evaluate(el => { el.scrollTop = el.scrollHeight; });
  const afterScroll = await sheet.evaluate(el => ({ top: el.scrollTop, max: Math.max(0, el.scrollHeight - el.clientHeight) }));
  expect(afterScroll.top).toBeGreaterThanOrEqual(Math.max(0, afterScroll.max - 2));
}

async function closeTool(page) {
  const sheet = page.locator('#marketSheet');
  const close = sheet.locator('[data-market-close]');
  await expect(close).toHaveCount(1);
  await expect(close).toBeVisible();
  await close.click();
  await expect(sheet).toBeHidden();
  await expect(page.locator('body')).not.toHaveClass(/modal-open/);
  await expect(sheet).toHaveAttribute('data-tool', '');
}

test('iPhone/WebKit: consecutive market tools keep clean sheet, scroll and viewport state', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);

  const journeys = [
    ['compare', '#marketCompareSearch'],
    ['scanner', '.market-tool-runtime__chips'],
    ['theses', '.market-list'],
    ['news', '#marketNewsSearch'],
  ];

  for (const [tool, readySelector] of journeys) {
    await page.locator(`[data-market-tool="${tool}"]`).first().click();
    await expect(page.locator(`#marketSheet ${readySelector}`)).toBeVisible({ timeout: 15_000 });
    await expectMobileSheetGeometry(page, tool);
    await closeTool(page);
    await expect(page.locator('.market-analysis-tools')).toBeVisible();
  }

  const finalState = await page.evaluate(() => {
    const sheet = document.getElementById('marketSheet');
    return {
      hidden: Boolean(sheet?.hidden),
      tool: sheet?.dataset?.tool || '',
      ticker: sheet?.dataset?.ticker || '',
      modalOpen: document.body.classList.contains('modal-open'),
      horizontalOverflow: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) - window.innerWidth,
    };
  });

  expect(finalState.hidden).toBeTruthy();
  expect(finalState.tool).toBe('');
  expect(finalState.ticker).toBe('');
  expect(finalState.modalOpen).toBeFalsy();
  expect(finalState.horizontalOverflow).toBeLessThanOrEqual(1);

  // Opportunities already has dedicated WebKit lens/filter coverage. Verify that
  // cycling modal tools leaves the underlying Market surface usable afterwards.
  await expect(page.locator('#viewMarket')).toBeVisible();
  await expect(page.locator('.vestra-opportunity-lenses').first()).toBeVisible({ timeout: 15_000 });

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});