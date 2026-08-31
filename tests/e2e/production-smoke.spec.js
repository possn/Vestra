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
  await expect(page.locator('#marketSearch')).toBeVisible();

  // `openDossier` is installed early by the loader, but the real market opener and
  // the compact index finish wiring asynchronously. Wait for both so a successful
  // return value cannot mask a sheet that was not yet able to render.
  await page.waitForFunction(() => (
    typeof window.VestraMarket?.openTicker === 'function' &&
    window.VestraMarketData?.openDossier &&
    window.VestraMarket?.__lazyDossiersInstalled === true
  ));

  for (const ticker of sentinels) {
    await page.waitForFunction(tickerToResolve => {
      try {
        return !!window.VestraMarket?.resolvePortfolioStock?.({
          ticker: tickerToResolve,
          yahooTicker: tickerToResolve,
          symbol: tickerToResolve,
          class: 'Ações'
        });
      } catch (_) {
        return false;
      }
    }, ticker);

    const opened = await page.evaluate(async tickerToOpen => (
      window.VestraMarketData.openDossier(tickerToOpen, { origin: 'production-smoke' })
    ), ticker);
    expect(opened, `${ticker} dossier opener failed`).toBeTruthy();

    const sheet = page.locator('#marketSheet');
    await expect(sheet).toBeVisible();
    await expect(sheet).toHaveAttribute('data-ticker', ticker);
    await expect(sheet.locator('.market-detail-head h2')).toHaveText(ticker);
    await expect(sheet.locator('#marketDetailBody')).not.toBeEmpty();
    await expect(sheet.locator('.market-close-persistent')).toBeVisible();

    await page.locator('.market-close-persistent').click();
    await expect(sheet).toBeHidden();
  }

  expect(pageErrors, `Production browser errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
