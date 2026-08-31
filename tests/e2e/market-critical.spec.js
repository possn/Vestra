const { test, expect } = require('@playwright/test');

async function isolateExternalSearch(page) {
  // The critical journey uses Vestra's local canonical market index and dossier
  // shards. A direct Yahoo search request is only a secondary autocomplete path
  // and is CORS-blocked from the local CI origin in WebKit. Fulfil only that
  // external search endpoint deterministically so real Vestra JS exceptions
  // remain visible through `pageerror`.
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ quotes: [], news: [], lists: [] })
    });
  });
}

async function openMarket(page) {
  await isolateExternalSearch(page);
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('#viewMarket')).toBeVisible();
  await expect(page.locator('#marketSearch')).toBeVisible();
}

async function openTicker(page, ticker) {
  const search = page.locator('#marketSearch');
  await search.fill(ticker);
  const row = page.locator(`.market-row[data-market-ticker="${ticker}"]`).first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();
  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', ticker);
  return sheet;
}

test('iPhone/WebKit: pesquisa -> dossier -> métricas -> tabs -> fechar -> reabrir', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);
  const sheet = await openTicker(page, 'MSFT');

  await expect(sheet.locator('.market-detail-head h2')).toHaveText('MSFT');
  await expect(sheet.locator('[data-live-field="current_price"]')).toBeVisible();
  await expect(sheet.locator('[data-live-field="forward_pe"]')).toBeVisible();
  await expect(sheet.locator('.market-tabs')).toBeVisible();

  await expect(sheet.locator('#marketSheetContent svg').first()).toBeVisible();

  const valuationTab = sheet.locator('[data-detail-tab="valuation"]');
  await valuationTab.click();
  await expect(valuationTab).toHaveClass(/is-active/);
  await expect(sheet.locator('#marketDetailBody')).not.toBeEmpty();

  const financialTab = sheet.locator('[data-detail-tab="financials"]');
  await financialTab.click();
  await expect(financialTab).toHaveClass(/is-active/);
  await expect(sheet.locator('#marketDetailBody')).not.toBeEmpty();

  await sheet.locator('.market-sheet__panel').evaluate(el => { el.scrollTop = el.scrollHeight; });
  const persistentClose = page.locator('.market-close-persistent');
  await expect(persistentClose).toBeVisible();
  await persistentClose.click();
  await expect(sheet).toBeHidden();

  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await row.click();
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('MSFT');
  await expect(sheet.locator('#marketDetailBody')).not.toBeEmpty();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: ETF discovery opens a usable fund dossier', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);
  await page.locator('[data-market-mode="funds"]').click();

  const firstFund = page.locator('#marketPrimary .market-row[data-market-ticker]').first();
  await expect(firstFund).toBeVisible({ timeout: 15_000 });
  const ticker = await firstFund.getAttribute('data-market-ticker');
  expect(ticker).toBeTruthy();

  await firstFund.click();
  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', ticker);
  await expect(sheet.locator('.market-kicker').first()).toHaveText('ETF / Fundo');
  await expect(sheet.locator('[data-detail-tab="overview"]')).toHaveClass(/is-active/);
  await expect(sheet.locator('#marketDetailBody')).not.toBeEmpty();

  await page.locator('.market-close-persistent').click();
  await expect(sheet).toBeHidden();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: global ticker is learned centrally and persists locally across reload', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  const ticker = 'ZZVST';
  let centralPosts = 0;
  let learnedPreflights = 0;

  await isolateExternalSearch(page);
  await page.route('https://worker.test/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const origin = request.headers().origin || '*';
    const cors = {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400'
    };

    if (request.method() === 'OPTIONS') {
      if (url.pathname === '/learned-universe') learnedPreflights += 1;
      return route.fulfill({ status: 204, headers: cors, body: '' });
    }
    if (url.pathname === '/quote') {
      return route.fulfill({
        status: 200,
        headers: { ...cors, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker,
          name: 'Vestra Synthetic Systems',
          exchange: 'NMS',
          quote_type: 'EQUITY',
          currency: 'USD',
          price: 42.5
        })
      });
    }
    if (url.pathname === '/market') {
      return route.fulfill({
        status: 200,
        headers: { ...cors, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker,
          name: 'Vestra Synthetic Systems',
          exchange: 'NMS',
          quote_type: 'EQUITY',
          currency: 'USD',
          current_price: 42.5,
          market_cap: 1200000000,
          forward_pe: 18.2,
          price_to_book: 3.1,
          roe: 0.18,
          fcf_yield: 0.052,
          revenue_growth: 0.14,
          earnings_growth: 0.17,
          operating_margin: 0.21,
          profit_margin: 0.16,
          debt_to_equity: 0.4,
          current_ratio: 1.8,
          fifty_two_week_high: 55,
          fifty_two_week_low: 38,
          sector: 'Technology',
          industry: 'Software',
          country: 'United States'
        })
      });
    }
    if (url.pathname === '/learned-universe' && request.method() === 'POST') {
      centralPosts += 1;
      expect(JSON.parse(request.postData() || '{}').ticker).toBe(ticker);
      return route.fulfill({
        status: 200,
        headers: { ...cors, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ok: true })
      });
    }
    return route.fulfill({ status: 404, headers: cors, body: 'not found' });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.waitForFunction(() => !!window.VestraLearnedUniverse && !!window.VestraGlobalMarketSearch);
  await page.evaluate(() => {
    window.state.settings.workerUrl = 'https://worker.test';
    window.setView('market');
  });

  const search = page.locator('#marketSearch');
  await expect(search).toBeVisible();
  await search.fill(ticker);

  const globalRow = page.locator(`[data-vestra-global-ticker="${ticker}"]`).first();
  await expect(globalRow).toBeVisible({ timeout: 15_000 });
  await globalRow.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-ticker', ticker);
  await expect(sheet.locator('.market-kicker').first()).toHaveText('DOSSIER GLOBAL · LIVE');
  await expect(sheet.locator('.market-detail-head h2')).toHaveText(ticker);
  await expect.poll(() => centralPosts).toBe(1);
  expect(learnedPreflights).toBeGreaterThanOrEqual(1);

  const learnedBeforeReload = await page.evaluate(async learnedTicker => {
    const rows = await window.VestraLearnedUniverse.list();
    return rows.find(row => row.ticker === learnedTicker) || null;
  }, ticker);
  expect(learnedBeforeReload).toBeTruthy();
  expect(learnedBeforeReload.name).toBe('Vestra Synthetic Systems');
  expect(learnedBeforeReload.validation_count).toBeGreaterThanOrEqual(2);

  await page.reload();
  await page.waitForFunction(() => !!window.VestraLearnedUniverse);
  const learnedAfterReload = await page.evaluate(async learnedTicker => {
    const rows = await window.VestraLearnedUniverse.list();
    return rows.find(row => row.ticker === learnedTicker) || null;
  }, ticker);
  expect(learnedAfterReload).toBeTruthy();
  expect(learnedAfterReload.ticker).toBe(ticker);
  expect(centralPosts).toBe(1);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
