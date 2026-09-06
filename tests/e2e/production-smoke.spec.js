const { test, expect } = require('@playwright/test');

const PREFERRED_SENTINELS = [
  'MSFT', 'AAPL', 'NVDA', 'AMZN', 'META', 'GOOGL', 'JPM', 'XOM', 'TSLA', 'V'
];
const REQUIRED_STARTUP_FIELDS = ['ticker', 'name', 'score', 'currency', 'quote_type', 'dossier_shard'];
const STARTUP_PAYLOAD_FILES = ['stocks-startup.json', 'stocks-index.json', 'stocks.json'];

function urlFromBase(base, relative) {
  return new URL(relative, base).toString();
}

function unpackStartupRow(fields, values) {
  const out = {};
  if (!Array.isArray(values)) return out;
  for (let i = 0; i < values.length && i < fields.length; i += 1) {
    out[fields[i]] = values[i];
  }
  return out;
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

test('GitHub Pages: compact startup data and representative market dossiers are usable on iPhone/WebKit', async ({ page, request, baseURL }) => {
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

  const startupRows = startup.rows
    .filter(Array.isArray)
    .map(values => unpackStartupRow(startup.fields, values));
  const startupTickers = new Set(
    startupRows
      .map(row => String(row.ticker || '').trim().toUpperCase())
      .filter(Boolean)
  );
  expect(startupTickers.size, 'stocks-startup contains missing/duplicate ticker identities').toBe(manifestTickerCount);

  const sentinels = PREFERRED_SENTINELS.filter(ticker => tickers[ticker]).slice(0, 5);
  expect(
    sentinels.length,
    `Expected at least five stable sentinels in published manifest; found: ${sentinels.join(', ')}`
  ).toBeGreaterThanOrEqual(5);

  // Market breadth is a production contract too. Select live representatives
  // dynamically so the smoke covers London identity/hydration and an ETF without
  // coupling the test to one specific fund or FTSE constituent forever.
  const ukEquity = startupRows.find(row => {
    const ticker = String(row.ticker || '').toUpperCase();
    return ticker.endsWith('.L') && String(row.quote_type || '').toUpperCase() !== 'ETF' && tickers[ticker];
  });
  const etf = startupRows.find(row => {
    const ticker = String(row.ticker || '').toUpperCase();
    return String(row.quote_type || '').toUpperCase() === 'ETF' && tickers[ticker];
  });
  expect(ukEquity?.ticker, 'Expected at least one London-listed equity in published startup data').toBeTruthy();
  expect(etf?.ticker, 'Expected at least one ETF in published startup data').toBeTruthy();

  const etfTicker = String(etf.ticker).toUpperCase();
  const journeyTickers = Array.from(new Set([
    ...sentinels,
    String(ukEquity.ticker).toUpperCase(),
    etfTicker,
  ]));
  for (const ticker of journeyTickers) {
    expect(startupTickers.has(ticker), `${ticker} missing from published stocks-startup`).toBeTruthy();
  }

  // Verify the actual published dossier shard for every representative before
  // opening UI. This catches a manifest/index publication that points at a stale
  // or missing shard even when the initial market list itself still renders.
  for (const ticker of journeyTickers) {
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

  // Equities appear in the Discover result list. Funds intentionally remain in
  // their own Discover mode, but the global search suggestions include both
  // equities and ETFs and must open an exact ETF dossier from the same search box.
  for (const [index, ticker] of journeyTickers.entries()) {
    await search.fill(ticker);

    if (ticker === etfTicker) {
      const suggestion = page.locator(`#marketSuggestions [data-market-ticker="${ticker}"]`).first();
      await expect(suggestion, `${ticker} missing from global market suggestions`).toBeVisible({ timeout: 20_000 });
      await expect(suggestion.locator('.market-suggestion__type')).toContainText('ETF');
      await suggestion.click();
    } else {
      const row = page.locator(`.market-row[data-market-ticker="${ticker}"]`).first();
      await expect(row, `${ticker} missing from published market search`).toBeVisible({ timeout: 20_000 });
      await row.click();
    }

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
