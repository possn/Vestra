const { test, expect } = require('@playwright/test');

const PREFERRED_SENTINELS = [
  'MSFT', 'AAPL', 'NVDA', 'AMZN', 'META', 'GOOGL', 'JPM', 'XOM', 'TSLA', 'V'
];

function urlFromBase(base, relative) {
  return new URL(relative, base).toString();
}

test('GitHub Pages: published data and five sentinel dossiers are usable on iPhone/WebKit', async ({ page, request, baseURL }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  const indexURL = urlFromBase(baseURL, 'index.html');
  const manifestURL = urlFromBase(baseURL, 'data/dossiers-manifest.json');
  const marketURL = urlFromBase(baseURL, 'market.js');

  const [indexResponse, manifestResponse, marketResponse] = await Promise.all([
    request.get(indexURL, { failOnStatusCode: false }),
    request.get(manifestURL, { failOnStatusCode: false }),
    request.get(marketURL, { failOnStatusCode: false })
  ]);

  expect(indexResponse.ok(), `index.html returned ${indexResponse.status()}`).toBeTruthy();
  expect(manifestResponse.ok(), `dossiers-manifest returned ${manifestResponse.status()}`).toBeTruthy();
  expect(marketResponse.ok(), `market.js returned ${marketResponse.status()}`).toBeTruthy();
  expect(await indexResponse.text()).toContain('<title>Vestra</title>');

  const manifest = await manifestResponse.json();
  const tickers = manifest?.tickers || {};
  expect(Object.keys(tickers).length).toBeGreaterThan(100);

  const sentinels = PREFERRED_SENTINELS.filter(ticker => tickers[ticker]).slice(0, 5);
  expect(
    sentinels.length,
    `Expected at least five stable sentinels in published manifest; found: ${sentinels.join(', ')}`
  ).toBeGreaterThanOrEqual(5);

  // Verify the actual published dossier shard for every sentinel before opening UI.
  for (const ticker of sentinels) {
    const shard = tickers[ticker];
    const shardResponse = await request.get(
      urlFromBase(baseURL, `data/dossiers/${encodeURIComponent(shard)}.json`),
      { failOnStatusCode: false }
    );
    expect(shardResponse.ok(), `${ticker} shard ${shard} returned ${shardResponse.status()}`).toBeTruthy();
    const payload = await shardResponse.json();
    expect(payload?.stocks?.[ticker], `${ticker} missing from published shard ${shard}`).toBeTruthy();
  }

  await page.goto('index.html', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('#viewMarket')).toBeVisible();

  const search = page.locator('#marketSearch');
  await expect(search).toBeVisible();

  // Use the same public journey a user uses in production. Do not couple the smoke
  // to internal bootstrap helpers such as resolvePortfolioStock(): the published
  // contract is that a known ticker typed into Market becomes a clickable result
  // and opens a usable dossier.
  for (const ticker of sentinels) {
    await search.fill(ticker);

    const row = page.locator(`.market-row[data-market-ticker="${ticker}"]`).first();
    await expect(row, `${ticker} missing from published market search`).toBeVisible({ timeout: 20_000 });
    await row.click();

    const sheet = page.locator('#marketSheet');
    await expect(sheet, `${ticker} dossier did not open`).toBeVisible({ timeout: 15_000 });
    await expect(sheet).toHaveAttribute('data-ticker', ticker);
    await expect(sheet.locator('.market-detail-head h2')).toHaveText(ticker);
    await expect(sheet.locator('#marketDetailBody')).not.toBeEmpty();
    await expect(sheet.locator('.market-close-persistent')).toBeVisible();

    await page.locator('.market-close-persistent').click();
    await expect(sheet).toBeHidden();
  }

  expect(pageErrors, `Production browser errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
