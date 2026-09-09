const { test, expect } = require('@playwright/test');

async function openMarket(page) {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => window.VestraMarketAnalysisToolsRuntime && window.VestraMarketStaticUniverse);
  await page.evaluate(() => window.VestraMarket.ensureLoaded());
  await expect(page.locator('.market-analysis-tools')).toBeVisible({ timeout: 15000 });
}

test('iPhone/WebKit: Compare searches companies by name and produces a table', async ({ page }) => {
  await openMarket(page);
  const companies = await page.evaluate(() => (window.VestraMarketStaticUniverse.getStocks() || [])
    .filter(s => String(s?.quote_type || '').toUpperCase() !== 'ETF' && String(s?.name || '').length >= 5)
    .slice(0, 20)
    .map(s => ({ ticker: String(s.ticker || ''), name: String(s.name || '') })));
  expect(companies.length).toBeGreaterThanOrEqual(2);

  await page.locator('[data-market-tool="compare"]').first().click();
  await expect(page.locator('#marketCompareSearch')).toBeVisible();

  for (const company of companies.slice(0, 2)) {
    const input = page.locator('#marketCompareSearch');
    await input.fill(company.name.slice(0, Math.min(7, company.name.length)));
    const suggestion = page.locator(`[data-compare-add="${company.ticker.replace(/"/g, '\\"')}"]`).first();
    await expect(suggestion).toBeVisible({ timeout: 5000 });
    await suggestion.click();
  }

  await expect(page.locator('#marketCompareRuntimeGo')).toBeEnabled();
  await page.locator('#marketCompareRuntimeGo').click();
  await expect(page.locator('#marketCompareRuntimeResult table')).toBeVisible();
  await expect(page.locator('#marketCompareRuntimeResult th')).toHaveCount(3);
});

test('iPhone/WebKit: Scanner hydrates lazy payload, renders repaired strategy tabs and remains scrollable', async ({ page }) => {
  await openMarket(page);
  await page.locator('[data-market-tool="scanner"]').first().click();
  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(page.locator('.market-tool-runtime__chips')).toBeVisible({ timeout: 15000 });
  const overflow = await page.locator('#marketSheet .market-sheet__panel').evaluate(el => getComputedStyle(el).overflowY);
  expect(['auto','scroll']).toContain(overflow);

  const strategies = [
    ['quality_at_fair_price', 'Qualidade + preço'],
    ['growth_at_reasonable_price', 'Growth'],
    ['deep_value', 'Value'],
    ['low_52w', 'Mínimos 52s'],
  ];

  for (const [key, label] of strategies) {
    const chip = page.locator(`[data-tool-scanner-strategy="${key}"]`);
    await expect(chip, `${label} chip missing`).toBeVisible();
    await chip.click();
    await expect(chip, `${label} should become active`).toHaveClass(/is-active/);
    const rows = page.locator('#marketScannerRuntimeRows .market-tool-runtime__row');
    await expect.poll(() => rows.count(), { message: `${label} should render scanner candidates` }).toBeGreaterThan(0);
    await expect(page.locator('#marketScannerRuntimeRows .market-empty'), `${label} must not fall back to an empty state`).toHaveCount(0);
  }
});

test('iPhone/WebKit: News searches the full universe and opens the dossier News tab', async ({ page }) => {
  await openMarket(page);
  const company = await page.evaluate(() => (window.VestraMarketStaticUniverse.getStocks() || [])
    .find(s => String(s?.quote_type || '').toUpperCase() !== 'ETF' && String(s?.name || '').length >= 5));
  expect(company).toBeTruthy();

  await page.locator('[data-market-tool="news"]').first().click();
  const input = page.locator('#marketNewsSearch');
  await expect(input).toBeVisible();
  await input.fill(String(company.name).slice(0, Math.min(7, String(company.name).length)));
  const suggestion = page.locator(`[data-news-open="${String(company.ticker).replace(/"/g, '\\"')}"]`).first();
  await expect(suggestion).toBeVisible({ timeout: 5000 });
  await suggestion.click();
  await expect(page.locator('#marketSheet [data-detail-tab="news"]')).toBeVisible({ timeout: 10000 });
  await expect(page.locator('#marketDetailBody')).not.toBeEmpty({ timeout: 10000 });
});

test('iPhone/WebKit: Theses tool opens and closes without trapping the sheet', async ({ page }) => {
  await openMarket(page);
  await page.locator('[data-market-tool="theses"]').first().click();
  await expect(page.locator('#marketSheet')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'O que está a mudar' })).toBeVisible();
  await page.locator('[data-tool-runtime-close]').click();
  await expect(page.locator('#marketSheet')).toBeHidden();
});
