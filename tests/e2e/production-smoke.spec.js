const { test, expect } = require('@playwright/test');

const PREFERRED_SENTINELS = [
  'MSFT', 'AAPL', 'NVDA', 'AMZN', 'META', 'GOOGL', 'JPM', 'XOM', 'TSLA', 'V'
];
const REQUIRED_STARTUP_FIELDS = ['ticker', 'name', 'score', 'currency', 'dossier_shard'];
const STARTUP_PAYLOAD_FILES = ['stocks-startup.json', 'stocks-index.json', 'stocks.json'];

function urlFromBase(base, relative) {
  return new URL(relative, base).toString();
}

async function isolateExternalSearch(page) {
  // Vestra's published compact universe + dossier shards are the primary path used
  // by this smoke. Yahoo's direct autocomplete endpoint rejects browser CORS in
  // WebKit, so isolate only that secondary external request. All Vestra pageerror
  // exceptions remain observable and still fail the smoke.
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ quotes: [], news: [], lists: [] })
    });
  });
}

test('GitHub Pages: compact startup data and five sentinel dossiers are usable on iPhone/WebKit', async ({ page, request, baseURL }) => {
  const pageErrors = [];
  const browserStartupRequests = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', req => {
    try {
      const pathname = new URL(req.url()).pathname;
      const filename = pathname.split('/').pop();
      if (STARTUP_PAYLOAD_FILES.includes(filename)) browserStartupRequests.push(filename);
    } catch (_) {}
  });

  const indexURL = urlFromBase(baseURL, 'index.html');
  const startupURL = urlFromBase(baseURL, 'data/stocks-startup.json');
  const manifestURL = urlFromBase(baseURL, 'data/dossiers-manifest.json');
  const marketURL = urlFromBase(baseURL, 'market.js');

  const [indexResponse, startupResponse, manifestResponse, marketResponse] = await Promise.all([
    request.get(indexURL, { failOnStatusCode: false }),
    request.get(startupURL, { failOnStatusCode: false }),
    request.get(manifestURL, { failOnStatusCode: false }),
    request.get(marketURL, { failOnStatusCode: false })
  ]);

  expect(indexResponse.ok(), `index.html returned ${indexResponse.status()}`).toBeTruthy();
  expect(startupResponse.ok(), `stocks-startup returned ${startupResponse.status()}`).toBeTruthy();
  expect(manifestResponse.ok(), `dossiers-manifest returned ${manifestResponse.status()}`).toBeTruthy();
  expect(marketResponse.ok(), `market.js returned ${marketResponse.status()}`).toBeTruthy();
  expect(await indexResponse.text()).toContain('<title>Vestra</title>');

  // Validate the payload the production loader prefers. This must fail closed:
  // a missing/malformed compact payload may still let the UI work via the legacy
  // index fallback, but that would silently lose the startup-performance rollout.
  const startup = await startupResponse.json();
  expect(startup?.layout).toBe('field_rows_v1');
  expect(Array.isArray(startup?.fields)).toBeTruthy();
  expect(Array.isArray(startup?.rows)).toBeTruthy();
  expect(startup.fields.length).toBeGreaterThan(5);
  expect(startup.rows.length).toBeGreaterThan(100);
  for (const field of REQUIRED_STARTUP_FIELDS) {
    expect(startup.fields, `stocks-startup missing required field ${field}`).toContain(field);
  }

  const manifest = await manifestResponse.json();
  const tickers = manifest?.tickers || {};
  const manifestTickerCount = Object.keys(tickers).length;
  expect(manifestTickerCount).toBeGreaterThan(100);
  expect(startup.rows.length, 'stocks-startup and dossier manifest cardinality diverged').toBe(manifestTickerCount);
  if (Number.isFinite(Number(manifest?.ticker_count))) {
    expect(Number(manifest.ticker_count)).toBe(manifestTickerCount);
  }

  const tickerFieldIndex = startup.fields.indexOf('ticker');
  const startupTickers = new Set(
    startup.rows
      .filter(Array.isArray)
      .map(values => String(values[tickerFieldIndex] || '').trim().toUpperCase())
      .filter(Boolean)
  );
  expect(startupTickers.size, 'stocks-startup contains missing/duplicate ticker identities').toBe(manifestTickerCount);

  const sentinels = PREFERRED_SENTINELS.filter(ticker => tickers[ticker]).slice(0, 5);
  expect(
    sentinels.length,
    `Expected at least five stable sentinels in published manifest; found: ${sentinels.join(', ')}`
  ).toBeGreaterThanOrEqual(5);
  for (const ticker of sentinels) {
    expect(startupTickers.has(ticker), `${ticker} missing from published stocks-startup`).toBeTruthy();
  }

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

  await isolateExternalSearch(page);
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
  for (const [index, ticker] of sentinels.entries()) {
    await search.fill(ticker);

    const row = page.locator(`.market-row[data-market-ticker="${ticker}"]`).first();
    await expect(row, `${ticker} missing from published market search`).toBeVisible({ timeout: 20_000 });

    if (index === 0) {
      expect(
        browserStartupRequests,
        `Expected browser to load stocks-startup.json; observed: ${browserStartupRequests.join(', ') || 'none'}`
      ).toContain('stocks-startup.json');
      expect(
        browserStartupRequests,
        `Production browser unexpectedly fell back to stocks-index.json; observed: ${browserStartupRequests.join(', ')}`
      ).not.toContain('stocks-index.json');
      expect(
        browserStartupRequests,
        `Production browser unexpectedly fell back to stocks.json; observed: ${browserStartupRequests.join(', ')}`
      ).not.toContain('stocks.json');
    }

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
