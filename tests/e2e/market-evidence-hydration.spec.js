const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: hydrated dossier exposes evidence quality without startup payload cost', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  // Local canonical index + dossier shards own this journey. Keep Yahoo's
  // secondary autocomplete endpoint deterministic under the CI localhost origin.
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ quotes: [], news: [], lists: [] })
    });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function' && !!window.VestraMarket?.__lazyDossiersInstalled);
  await page.evaluate(() => window.setView('market'));

  const search = page.locator('#marketSearch');
  await expect(search).toBeVisible();
  await search.fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', 'MSFT');

  // The startup row intentionally has no full data_provenance. This assertion
  // therefore proves the dossier shard completed, merged and re-rendered the
  // active overview tab in WebKit rather than merely testing the panel helper.
  const evidence = sheet.locator('.market-evidence-quality');
  await expect(evidence).toBeVisible({ timeout: 15_000 });
  await expect(evidence).toContainText('QUALIDADE DA EVIDÊNCIA');
  await expect(evidence).toContainText('Fontes fundamentais');
  await expect(evidence).toContainText('Confiança dos dados');
  await expect(evidence).toContainText('não altera o Score Vestra');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
