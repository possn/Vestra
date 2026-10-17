const { test, expect } = require('@playwright/test');

// Compare computed foreground with the actual opaque card it belongs to.
function contrast(text, background) {
  const rgb = value => (value.match(/rgba?\(([^)]+)\)/)?.[1] || '').split(',').slice(0, 3).map(Number);
  const light = channels => channels.map(n => n / 255).map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4)
    .reduce((sum, n, index) => sum + n * [.2126, .7152, .0722][index], 0);
  const a = light(rgb(text)), b = light(rgb(background));
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
}

test('iPhone/WebKit: portfolio summary foreground remains readable on both surface types', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('assets'));
  await expect(page.locator('#viewAssets .portfolio-glance')).toBeVisible();
  const colors = await page.evaluate(() => {
    const css = selector => getComputedStyle(document.querySelector(selector));
    return {
      mainText: css('#viewAssets .portfolio-glance__main strong').color,
      // The main card is a gradient; its dark endpoint is the contrast reference.
      mainCard: 'rgb(20, 79, 79)',
      statText: css('#viewAssets .portfolio-glance__stat strong').color,
      // Semi-transparent tiles paint over a pale summary card.
      statCard: 'rgb(239, 242, 236)',
      incomeText: css('#viewAssets .portfolio-income-strip small').color,
      incomeCard: 'rgb(239, 242, 236)',
    };
  });
  expect(contrast(colors.mainText, colors.mainCard), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(colors.statText, colors.statCard), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(colors.incomeText, colors.incomeCard), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
});

test('iPhone/WebKit: Market analysis panel title has readable ink on light card', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  const panel = page.locator('#viewMarket .market-analysis-tools');
  await expect(panel).toBeVisible({ timeout: 15000 });
  const colors = await page.evaluate(() => {
    const panel = document.querySelector('#viewMarket .market-analysis-tools');
    return {
      title: getComputedStyle(panel.querySelector('.market-analysis-tools__head strong')).color,
      card: getComputedStyle(panel).backgroundColor,
    };
  });
  expect(contrast(colors.title, colors.card), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
});

test('iPhone/WebKit: privacy controls use one shared state across both Homes', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.toggleDashboardPrivacy === 'function');
  const legacy = page.locator('#btnDashboardPrivacy');
  const editorial = page.locator('[data-vi-privacy]');
  await expect(legacy).toHaveAttribute('aria-pressed', /^(true|false)$/);
  await expect(editorial).toHaveAttribute('aria-pressed', /^(true|false)$/);
  const before = await legacy.getAttribute('aria-pressed');
  await page.evaluate(() => window.toggleDashboardPrivacy());
  const after = before === 'true' ? 'false' : 'true';
  await expect(legacy).toHaveAttribute('aria-pressed', after);
  await expect(editorial).toHaveAttribute('aria-pressed', after);
  await expect(page.locator('#viewDashboard')).toHaveAttribute('data-values-hidden', after);
  if (after === 'true') {
    await expect(page.locator('[data-vi-wealth]')).toContainText('•••');
    await expect(page.locator('[data-vi-assets]')).toHaveText('Valores ocultos');
  }
  await page.evaluate(() => window.toggleDashboardPrivacy());
  await expect(legacy).toHaveAttribute('aria-pressed', before);
  await expect(editorial).toHaveAttribute('aria-pressed', before);
});

test('iPhone/WebKit: totals cache updates after a price revaluation without changing asset count', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true && typeof window.VestraFinancialTotals === 'function');
  const outcome = await page.evaluate(() => {
    const original = state.assets;
    try {
      state.assets = [{ id: 'valuation-regression', value: 100, name: 'Test asset' }];
      invalidateRenderCache();
      const first = window.VestraFinancialTotals();
      state.assets[0].value = 175;
      const second = window.VestraFinancialTotals();
      return { initialAssets: first.assetsTotal, updatedAssets: second.assetsTotal,
        initialNet: first.net, updatedNet: second.net };
    } finally {
      state.assets = original;
      invalidateRenderCache();
    }
  });
  expect(outcome.updatedAssets - outcome.initialAssets).toBe(75);
  expect(outcome.updatedNet - outcome.initialNet).toBe(75);
});

test('iPhone/WebKit: editorial wealth equals native Dashboard after hydration', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true && typeof window.VestraFinancialTotals === 'function');
  await page.evaluate(() => {
    if (typeof window.setView === 'function') window.setView('dashboard');
    if (typeof window.renderDashboard === 'function') window.renderDashboard();
  });
  // Compare financial values rather than formatting details; both surfaces must
  // display the exact canonical totals when privacy is off.
  await page.evaluate(() => {
    if (document.getElementById('btnDashboardPrivacy')?.getAttribute('aria-pressed') === 'true') {
      window.toggleDashboardPrivacy();
    }
    window.dispatchEvent(new Event('focus'));
  });
  const expected = await page.evaluate(() => {
    const t = window.VestraFinancialTotals();
    return new Intl.NumberFormat('pt-PT', {style:'currency',currency:'EUR',maximumFractionDigits:0}).format(t.net);
  });
  await expect(page.locator('[data-vi-wealth]')).toHaveText(expected);
  await expect(page.locator('#kpiNet')).toHaveText(expected);
});
