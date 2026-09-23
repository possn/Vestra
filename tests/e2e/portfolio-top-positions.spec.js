const { test, expect } = require('@playwright/test');

test.use({ serviceWorkers: 'block' });

test('iPhone/WebKit: portfolio shows top five positions then expands to all', async ({ page }) => {
  const assets = Array.from({ length: 8 }, (_, i) => ({
    id: 'p' + (i + 1),
    class: 'Ações/ETFs',
    name: 'Position ' + (i + 1),
    ticker: 'P' + (i + 1),
    yahooTicker: 'P' + (i + 1),
    value: 8000 - i * 500,
    yieldType: 'none',
    yieldValue: 0,
  }));
  await page.addInitScript(state => {
    localStorage.setItem('PF_STATE_V6', JSON.stringify({
      settings: { currency: 'EUR', autoRefreshQuotes: false },
      assets: state,
      liabilities: [], transactions: [], bankTransactions: [], dividends: [], divSummaries: [],
      history: [], brokerData: { files: [], events: [], positions: [] },
      priceHistory: {}, fxHistory: {},
    }));
  }, assets);

  await page.goto('/index.html');
  await page.waitForFunction(() => window.__vestraAppHydrated === true);
  await page.evaluate(() => setView('assets'));

  const list = page.locator('#itemsList .item');
  const toggle = page.locator('#btnItemsToggle');
  await expect(page.locator('#itemsTitle')).toHaveText('Posições principais');
  await expect(page.locator('#itemsSub')).toContainText('Top 5 por valor');
  await expect(list).toHaveCount(5);
  await expect(toggle).toHaveText('Ver todas (8)');

  await toggle.tap();
  await expect(list).toHaveCount(8);
  await expect(toggle).toHaveText('Mostrar menos');

  await toggle.tap();
  await expect(list).toHaveCount(5);
  await expect(toggle).toHaveText('Ver todas (8)');
});
