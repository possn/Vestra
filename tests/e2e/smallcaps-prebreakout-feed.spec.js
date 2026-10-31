const {test,expect}=require('@playwright/test');
const fs=require('fs');
const path=require('path');

test('iPhone: verified independent small-cap setup appears in the existing opportunity card',async({page})=>{
  const index=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data/stocks-index.json'),'utf8'));
  const stock=index.stocks.find(s=>Number(s.market_cap)>=100000000&&Number(s.market_cap)<500000000&&
    !['ETF','FUND','MUTUALFUND','CRYPTO'].includes(String(s.quote_type||'').toUpperCase()));
  expect(stock).toBeTruthy();
  const stamp=new Date().toISOString(),date=stamp.slice(0,10);
  const signal={ticker:stock.ticker,date,stage:'pré-breakout',score:73,widthPct:9.5,
    priorWidthPct:21.2,distancePct:2.1,resistance:12.5,volumeConfirmed:false,
    volumeDry:true,vcpConfirmed:true,goldenCrossRecent:false,
    source:'yahoo:smallcap_daily_ohlcv',currencyVerified:'USD',
    marketCapUSD:stock.market_cap,spreadVerified:false,earningsRiskGate:'unknown'};
  await page.route('**/data/breakout-lab-smallcap-ohlcv-research.json',route=>route.fulfill({
    status:200,contentType:'application/json',body:JSON.stringify({
      schema:'vestra_breakout_lab_smallcap_ohlcv_research_v1',generated_at:stamp,
      status:'observed_research_only_not_breakout_signals',
      signals:[signal]})
  }));
  await page.goto('/index.html');
  await page.waitForFunction(()=>typeof window.setView==='function');
  await page.evaluate(()=>window.setView('market'));
  const chip=page.locator('#viewMarket [data-smallcap-prebreakout-lens]');
  await expect(chip).toBeVisible({timeout:20000});
  await chip.click();
  const rows=page.locator('#marketPrimary .market-row[data-market-ticker]');
  await expect(rows).toHaveCount(1,{timeout:20000});
  await expect(rows.first()).toContainText(stock.ticker);
  await expect(rows.first()).toContainText('Spread/gap por validar');
  await expect(page.locator('#viewMarket [data-market-mode="smallcaps"]')).toHaveCount(0);
});
