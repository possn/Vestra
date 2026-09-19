const { test, expect } = require('@playwright/test');

test.use({ serviceWorkers: 'block' });

test('iPhone/WebKit: main portfolio restores sectors with holdings and hides them for liabilities', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('PF_STATE_V6', JSON.stringify({
      settings: { currency: 'EUR', autoRefreshQuotes: false },
      assets: [
        { id:'a1', class:'Ações/ETFs', name:'Apple', ticker:'AAPL', yahooTicker:'AAPL', value:1200, costBasis:1000, yieldType:'none', yieldValue:0 },
        { id:'a2', class:'Ações/ETFs', name:'Microsoft', ticker:'MSFT', yahooTicker:'MSFT', value:800, costBasis:700, yieldType:'none', yieldValue:0 },
        { id:'a3', class:'Ações/ETFs', name:'Exxon Mobil', ticker:'XOM', yahooTicker:'XOM', value:1000, costBasis:900, yieldType:'none', yieldValue:0 },
      ],
      liabilities: [{ id:'l1', class:'Crédito', name:'Teste', value:500 }],
      transactions: [], bankTransactions: [], dividends: [], divSummaries: [],
      history: [], brokerData: { files: [], events: [], positions: [] },
      priceHistory: {}, fxHistory: {},
    }));
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);
  await page.evaluate(() => setView('assets'));

  const card = page.locator('#portfolioSectorCard');
  await expect(card).toBeVisible();
  await expect(card).toContainText('Sectores da carteira');
  await expect(card.locator('.portfolio-sector-group')).toHaveCount(2);
  await expect(card).toContainText('Tecnologia');
  await expect(card).toContainText('Energia');
  await expect(card).toContainText('Apple');
  await expect(card).toContainText('Microsoft');
  await expect(card).toContainText('Exxon Mobil');

  const first = card.locator('.portfolio-sector-group').first();
  await expect(first).toHaveAttribute('open', '');
  await expect(first.locator('.portfolio-sector-asset')).toHaveCount(2);

  await page.locator('#segLiabs').tap();
  await expect(card).toBeHidden();

  await page.locator('#segAssets').tap();
  await expect(card).toBeVisible();
});
