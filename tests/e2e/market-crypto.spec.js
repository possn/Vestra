const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: Crypto tab renders barometer, live rows, search and dedicated dossier', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  const fixture = {
    'BTC-USD': { ticker:'BTC-USD', provider_symbol:'BTC-USD', price:100000, currency:'USD', change_pct:3.2, market_cap:2000000000000, fifty_two_week_high:110000, fifty_two_week_low:50000 },
    'ETH-USD': { ticker:'ETH-USD', provider_symbol:'ETH-USD', price:4000, currency:'USD', change_pct:2.1, market_cap:480000000000, fifty_two_week_high:4800, fifty_two_week_low:1800 },
    'BNB-USD': { ticker:'BNB-USD', provider_symbol:'BNB-USD', price:800, currency:'USD', change_pct:-1.2, market_cap:110000000000, fifty_two_week_high:900, fifty_two_week_low:300 },
    'SOL-USD': { ticker:'SOL-USD', provider_symbol:'SOL-USD', price:220, currency:'USD', change_pct:5.4, market_cap:100000000000, fifty_two_week_high:260, fifty_two_week_low:80 },
    'XRP-USD': { ticker:'XRP-USD', provider_symbol:'XRP-USD', price:3.1, currency:'USD', change_pct:1.4, market_cap:90000000000, fifty_two_week_high:3.8, fifty_two_week_low:0.5 },
    'ADA-USD': { ticker:'ADA-USD', provider_symbol:'ADA-USD', price:1.2, currency:'USD', change_pct:-0.8, market_cap:45000000000, fifty_two_week_high:1.5, fifty_two_week_low:0.3 },
    'DOGE-USD': { ticker:'DOGE-USD', provider_symbol:'DOGE-USD', price:0.4, currency:'USD', change_pct:0.7, market_cap:40000000000, fifty_two_week_high:0.55, fifty_two_week_low:0.08 },
    'AVAX-USD': { ticker:'AVAX-USD', provider_symbol:'AVAX-USD', price:55, currency:'USD', change_pct:-2.4, market_cap:22000000000, fifty_two_week_high:70, fifty_two_week_low:18 },
    'LINK-USD': { ticker:'LINK-USD', provider_symbol:'LINK-USD', price:35, currency:'USD', change_pct:4.2, market_cap:21000000000, fifty_two_week_high:42, fifty_two_week_low:9 },
    'DOT-USD': { ticker:'DOT-USD', provider_symbol:'DOT-USD', price:12, currency:'USD', change_pct:-1.7, market_cap:18000000000, fifty_two_week_high:16, fifty_two_week_low:4 },
    'BCH-USD': { ticker:'BCH-USD', provider_symbol:'BCH-USD', price:700, currency:'USD', change_pct:1.0, market_cap:14000000000, fifty_two_week_high:800, fifty_two_week_low:250 },
    'LTC-USD': { ticker:'LTC-USD', provider_symbol:'LTC-USD', price:160, currency:'USD', change_pct:-0.4, market_cap:12000000000, fifty_two_week_high:190, fifty_two_week_low:60 },
    'XLM-USD': { ticker:'XLM-USD', provider_symbol:'XLM-USD', price:0.6, currency:'USD', change_pct:2.5, market_cap:10000000000, fifty_two_week_high:0.75, fifty_two_week_low:0.1 },
    'SUI-USD': { ticker:'SUI-USD', provider_symbol:'SUI-USD', price:7, currency:'USD', change_pct:6.0, market_cap:9000000000, fifty_two_week_high:8, fifty_two_week_low:0.8 },
  };

  await page.route(/\/quotes\?tickers=/, async route => {
    await route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify(fixture) });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await expect(page.locator('[data-market-mode="crypto"]')).toBeVisible();
  await page.locator('[data-market-mode="crypto"]').click();

  await expect(page.locator('.market-crypto-barometer')).toBeVisible({ timeout:15_000 });
  await expect(page.locator('.market-crypto-row[data-crypto-symbol="BTC"]')).toBeVisible();
  await expect(page.locator('.market-crypto-barometer')).toContainText('CRYPTO BARÓMETRO');
  await expect(page.locator('.market-crypto-barometer')).toContainText('Breadth 24h');

  const search = page.locator('#marketSearch');
  await search.fill('Solana');
  await expect(page.locator('.market-crypto-row[data-crypto-symbol="SOL"]')).toBeVisible({ timeout:5_000 });
  await expect(page.locator('.market-crypto-row[data-crypto-symbol="BTC"]')).toHaveCount(0);

  await search.fill('');
  const btc = page.locator('.market-crypto-row[data-crypto-symbol="BTC"]').first();
  await expect(btc).toBeVisible();
  await btc.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute('data-tool','crypto');
  await expect(sheet).toHaveAttribute('data-crypto','BTC');
  await expect(sheet.locator('.market-kicker')).toContainText('CRYPTO DOSSIER');
  await expect(sheet).toContainText('Market cap');
  await expect(sheet).toContainText('Posição 52s');
  await expect(sheet).not.toContainText('Vestra Score');

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
