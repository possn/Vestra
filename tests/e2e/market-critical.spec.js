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

test('iPhone/WebKit: global ticker opens live and persists locally across reload', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  const ticker = 'ZZVST';

  await isolateExternalSearch(page);
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.waitForFunction(() => !!window.VestraLearnedUniverse && !!window.VestraGlobalMarketSearch);

  // The browser owns the user journey and IndexedDB persistence. The central
  // POST contract is covered deterministically by runtime_learned_universe_contract.js,
  // while the production verifier owns real Worker network/CORS behaviour.
  await page.evaluate(() => {
    const nativeFetch = window.fetch.bind(window);
    window.fetch = async (input, init = {}) => {
      const url = new URL(typeof input === 'string' ? input : input.url, window.location.href);
      if (!url.pathname.startsWith('/__worker_test__/')) return nativeFetch(input, init);
      const endpoint = url.pathname.replace('/__worker_test__', '');
      const json = payload => new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
      if (endpoint === '/quote') {
        return json({
          ticker: 'ZZVST', name: 'Vestra Synthetic Systems', exchange: 'NMS',
          quote_type: 'EQUITY', currency: 'USD', price: 42.5
        });
      }
      if (endpoint === '/market') {
        return json({
          ticker: 'ZZVST', name: 'Vestra Synthetic Systems', exchange: 'NMS',
          quote_type: 'EQUITY', currency: 'USD', current_price: 42.5,
          market_cap: 1200000000, forward_pe: 18.2, price_to_book: 3.1,
          roe: 0.18, fcf_yield: 0.052, revenue_growth: 0.14,
          earnings_growth: 0.17, operating_margin: 0.21, profit_margin: 0.16,
          debt_to_equity: 0.4, current_ratio: 1.8, fifty_two_week_high: 55,
          fifty_two_week_low: 38, sector: 'Technology', industry: 'Software',
          country: 'United States'
        });
      }
      if (endpoint === '/learned-universe') return json({ ok: true });
      return new Response('not found', { status: 404 });
    };
    window.state.settings.workerUrl = `${window.location.origin}/__worker_test__`;
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

  const learnedBeforeReload = await page.evaluate(async learnedTicker => {
    const rows = await window.VestraLearnedUniverse.list();
    return rows.find(row => row.ticker === learnedTicker) || null;
  }, ticker);
  expect(learnedBeforeReload).toBeTruthy();
  expect(learnedBeforeReload.ticker).toBe(ticker);
  expect(learnedBeforeReload.validation_count).toBeGreaterThanOrEqual(2);

  await page.reload();
  await page.waitForFunction(() => !!window.VestraLearnedUniverse);
  const learnedAfterReload = await page.evaluate(async learnedTicker => {
    const rows = await window.VestraLearnedUniverse.list();
    return rows.find(row => row.ticker === learnedTicker) || null;
  }, ticker);
  expect(learnedAfterReload).toBeTruthy();
  expect(learnedAfterReload.ticker).toBe(ticker);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
