const { test, expect } = require('@playwright/test');

async function openMarket(page) {
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ quotes: [], news: [], lists: [] })
    });
  });
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('#viewMarket')).toBeVisible();
  await expect(page.locator('.market-portfolio-access')).toBeVisible({ timeout: 15_000 });
}

test('iPhone/WebKit: carteira -> sectores -> posição -> dossier', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openMarket(page);

  await page.evaluate(() => {
    const fixture = {
      settings: { workerUrl: 'https://example.invalid' },
      assets: [
        { id:'a1', class:'Ações', name:'Microsoft', ticker:'MSFT', yahooTicker:'MSFT', qty:10, costBasis:1000, value:1400, isin:'US5949181045' },
        { id:'a2', class:'Ações', name:'Apple', ticker:'AAPL', yahooTicker:'AAPL', qty:5, costBasis:500, value:450, isin:'US0378331005' },
        { id:'a3', class:'Ações', name:'Pfizer', ticker:'PFE', yahooTicker:'PFE', qty:8, costBasis:300, value:320, isin:'US7170811035' },
      ],
      brokerData: {
        events: [
          { type:'BUY', ticker:'MSFT', isin:'US5949181045', date:'2024-01-15' },
          { type:'BUY', ticker:'MSFT', isin:'US5949181045', date:'2024-03-20' },
          { type:'BUY', ticker:'AAPL', isin:'US0378331005', date:'2025-02-10' },
          { type:'BUY', ticker:'PFE', isin:'US7170811035', date:'2023-11-05' },
        ]
      }
    };
    Object.defineProperty(window, 'VestraRuntimeBridge', {
      configurable: true,
      value: { getState: () => fixture }
    });
    const realResolve = window.VestraMarket.resolvePortfolioStock.bind(window.VestraMarket);
    window.__e2eRealResolvePortfolioStock = realResolve;
    window.VestraMarket.resolvePortfolioStock = asset => {
      const ticker = String(asset?.yahooTicker || asset?.ticker || '').toUpperCase();
      const known = {
        MSFT:{ticker:'MSFT',name:'Microsoft Corporation',sector:'Technology',quote_type:'EQUITY'},
        AAPL:{ticker:'AAPL',name:'Apple Inc.',sector:'Technology',quote_type:'EQUITY'},
        PFE:{ticker:'PFE',name:'Pfizer Inc.',sector:'Healthcare',quote_type:'EQUITY'},
      };
      return known[ticker] || realResolve(asset);
    };
  });

  await page.locator('.market-portfolio-access').click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible({ timeout: 15_000 });
  await expect(sheet).toHaveAttribute('data-tool', 'portfolio');

  const sectorBox = page.locator('.vpse');
  await expect(sectorBox).toBeVisible({ timeout: 15_000 });
  await expect(sectorBox).toContainText('As tuas ações por sector');
  await expect(sectorBox.locator('[data-vpse-sector="Technology"]')).toBeVisible();
  await expect(sectorBox.locator('[data-vpse-sector="Healthcare"]')).toBeVisible();

  await sectorBox.locator('[data-vpse-sector="Technology"]').click();
  const msft = sectorBox.locator('.vpse-position[data-market-ticker="MSFT"]');
  const aapl = sectorBox.locator('.vpse-position[data-market-ticker="AAPL"]');
  await expect(msft).toBeVisible();
  await expect(aapl).toBeVisible();

  await expect(msft).toContainText('15/01/2024');
  await expect(msft).toContainText('100,00');
  await expect(msft).toContainText('1 000');
  await expect(msft).toContainText('1 400');
  await expect(msft).toContainText('40,0%');

  await expect(aapl).toContainText('10/02/2025');
  await expect(aapl).toContainText('-50');
  await expect(aapl).toContainText('-10,0%');

  await page.evaluate(() => {
    window.VestraMarket.resolvePortfolioStock = window.__e2eRealResolvePortfolioStock;
  });
  await msft.click();

  await expect(sheet).toHaveAttribute('data-ticker', 'MSFT');
  await expect(sheet.locator('.market-detail-head h2')).toHaveText('MSFT');
  await expect(sheet).toHaveAttribute('data-return-view', 'portfolio');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
