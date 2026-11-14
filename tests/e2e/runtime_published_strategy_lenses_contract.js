// Exercise the production selection logic against the actual canonical index.
// A green fixture test alone cannot prove a nonempty published lens.
const fs=require('fs');
const vm=require('vm');
const assert=require('assert');
const index=JSON.parse(fs.readFileSync('data/stocks-index.json','utf8'));
const stocks=index.stocks;
assert(Array.isArray(stocks)&&stocks.length>0,'Canonical index must have equities');
const context={
  window:{VestraMarketStaticUniverse:{getStocks:()=>stocks}},
  document:{readyState:'loading',addEventListener(){},getElementById(){return null;},
    querySelectorAll(){return [];},head:{appendChild(){}},createElement(){return {dataset:{},style:{},appendChild(){},setAttribute(){}};}},
  console,CSS:{escape:x=>String(x)},requestAnimationFrame:fn=>fn(),
  MutationObserver:function(){this.observe=()=>{};},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('market-opportunities.js','utf8'),context);
const api=context.window.VestraMarketOpportunities;
assert(api,'Published strategy lens API required');

function assertLens(lens,expected){
  const eligible=stocks.filter(s=>api.lensEligible(s,lens));
  const ranked=api.rankLens(stocks,lens,{limit:12,sector:'all'});
  const selected=Array.from(ranked,s=>String(s.ticker));
  assert.strictEqual(new Set(selected).size,selected.length,`${lens}: duplicate ticker in shortlist`);
  assert.strictEqual(selected.length,Math.min(12,eligible.length),
    `${lens}: published eligible names unexpectedly disappeared from shortlist`);
  for(const stock of ranked)assert(api.lensEligible(stock,lens),`${lens}: ineligible published candidate`);
  assert(selected.every(t=>eligible.some(s=>s.ticker===t)),`${lens}: fabricated ticker`);
  console.log(JSON.stringify({lens,backend_status_count:expected,ui_eligible:eligible.length,
    ui_shortlist:ranked.length,example_tickers:selected.slice(0,5)}));
}
const recovery=stocks.filter(s=>['confirmed','recovering'].includes(s.recovery_status));
const low52=stocks.filter(s=>['opportunity','watch'].includes(s.low52_status));
assertLens('recovery',recovery.length);
assertLens('low52',low52.length);
// Backend strategies are distinct from final actionability; these counts must
// never be presented as success probabilities or guaranteed recommendations.
