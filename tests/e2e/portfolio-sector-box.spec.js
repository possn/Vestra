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
        { id:'a4', class:'Fundos', name:'Health Care Select Sector SPDR Fund', ticker:'XLV', yahooTicker:'XLV', value:600, costBasis:550, yieldType:'none', yieldValue:0, meta:{ quoteType:'ETF', sector:'Healthcare' } },
        { id:'a5', class:'Obrigações', name:'Certificados aforro', value:98748, yieldType:'yield_pct', yieldValue:2.5 },
        { id:'a6', class:'Fundos', name:'Revolut', value:40000, yieldType:'none', yieldValue:0 },
        { id:'a7', class:'Liquidez', name:'Dinheiro', value:12000, yieldType:'none', yieldValue:0 },
        { id:'a8', class:'Cripto', name:'Bitcoin', ticker:'BTC-USD', yahooTicker:'BTC-USD', value:9000, meta:{ quoteType:'CRYPTOCURRENCY' } },
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
  await expect(card.locator('.portfolio-sector-group')).toHaveCount(3);
  await expect(card).toContainText('Tecnologia');
  await expect(card).toContainText('Energia');
  await expect(card).toContainText('Saúde');
  await expect(card).toContainText('Apple');
  await expect(card).toContainText('Microsoft');
  await expect(card).toContainText('Exxon Mobil');
  await expect(card).toContainText('Health Care Select Sector SPDR Fund');
  await expect(card).not.toContainText('Certificados aforro');
  await expect(card).not.toContainText('Revolut');
  await expect(card).not.toContainText('Dinheiro');
  await expect(card).not.toContainText('Bitcoin');
  await expect(card).toContainText('ações + ETFs');

  const first = card.locator('.portfolio-sector-group').first();
  await expect(first).toHaveAttribute('open', '');
  await expect(first.locator('.portfolio-sector-asset')).toHaveCount(2);

  await page.locator('#segLiabs').tap();
  await expect(card).toBeHidden();

  await page.locator('#segAssets').tap();
  await expect(card).toBeVisible();
});
