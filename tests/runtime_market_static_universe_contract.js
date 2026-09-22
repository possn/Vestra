const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-static-universe.js', 'utf8');
const context = { window: {}, console, setTimeout, clearTimeout, AbortController };
vm.createContext(context);
vm.runInContext(source, context);

const api = context.window.VestraMarketStaticUniverse;
assert(api && api.version === '1.24');
assert.strictEqual(api.dataFetchTimeoutMs, 8000);
assert.strictEqual(api.etfIntelligenceLoadTimeoutMs, 8000);
assert.strictEqual(api.companionLoadTimeoutMs, 8000);
assert.strictEqual(typeof api.getStocks, 'function');
assert.strictEqual(typeof api.unpackStartupPayload, 'function');
assert.strictEqual(typeof api.ensureEtfIntelligence, 'function');
assert.strictEqual(typeof api.ensureScannerCompanion, 'function');
assert.strictEqual(typeof api.ensureAnalysisToolsRuntime, 'function');
assert.strictEqual(typeof api.ensureWeeklyEventsCompanion, 'function');
assert.strictEqual(typeof api.ensureWeeklyEventsNavigation, 'function');
assert.strictEqual(typeof api.ensureDashboardUiRefresh, 'function');
assert.strictEqual(typeof api.ensureDashboardDailyNews, 'function');
assert.strictEqual(typeof api.ensureDashboardMarketSentiment, 'function');
assert.strictEqual(typeof api.ensureDashboardPortfolioConcentration, 'function');
assert.strictEqual(typeof api.ensureMobileUiRefresh, 'function');
assert.strictEqual(typeof api.ensureMarketUiPolish, 'function');
assert.strictEqual(typeof api.ensureUiVisualPolish, 'function');
assert.strictEqual(typeof api.ensurePoliticiansCompanion, 'function');
assert.strictEqual(typeof api.ensureMetalsCompanion, 'function');
assert.strictEqual(typeof api.ensureOpportunitySuite, 'function');
assert.strictEqual(typeof api.ensurePortfolioSheetSuite, 'function');
assert.strictEqual(typeof api.ensureMarketCompanions, 'function');
assert(source.includes('market-etf-intelligence.js?v=1.2'));
assert(source.includes('market-scanner-data.js?v=1.3'));
assert(source.includes('market-analysis-tools-runtime.js?v=1.3'));
assert(source.includes('dashboard-weekly-events.js?v=2.4'));
assert(source.includes('dashboard-weekly-events-navigation.js?v=1.1'), 'weekly history navigation must be a reachable runtime companion');
assert(source.includes('dashboard-ui-refresh.js?v=1.6'));
assert(source.includes('dashboard-daily-news.js?v=1.7'), 'daily dashboard news must be a reachable runtime companion');
assert(source.includes('dashboard-market-sentiment.js?v=1.2'), 'market sentiment must be a reachable dashboard companion');
assert(source.includes('dashboard-portfolio-concentration.js?v=1.6'), 'portfolio concentration must be a reachable dashboard companion');
assert(source.includes('mobile-ui-refresh.js?v=1.4'));
assert(source.includes('market-ui-polish.js?v=1.3'));
assert(source.includes('ui-visual-polish.js?v=1.1'));
assert(source.includes('politicians.js?v=2.1'));
assert(source.includes('market-metals.js?v=1.2'));
assert(source.includes('market-opportunities.js?v=1.2'));
assert(source.includes('market-opportunity-lenses.js?v=3.1'));
assert(source.includes('vestra-portfolio-focus.js?v=1.1'));
assert(source.includes('vestra-swap-lab.js?v=1.1'));
assert(source.includes('vestra-portfolio-ui.js?v=1.2'));
assert(source.includes('portfolio-diagnostics.js?v=1.1'));
assert(source.includes('portfolio-dossier-routing.js?v=1.4'));
assert(source.includes('vestra-portfolio-hierarchy.js?v=1.6'));
assert(source.includes('vestra-ai-brief.js?v=1.2'));
assert(source.indexOf('VestraPortfolioFocus') < source.indexOf('VestraPortfolioHierarchy'));
assert(source.indexOf('VestraPortfolioUI') < source.indexOf('VestraPortfolioHierarchy'));
assert(source.indexOf('VestraPortfolioDiagnostics') < source.indexOf('VestraPortfolioHierarchy'));
assert(source.indexOf('VestraPortfolioDossierRouting') < source.indexOf('VestraPortfolioHierarchy'));
assert(!source.includes('vestraWeeklyEventsVisibilityGuard'));
const eagerTail = source.slice(source.indexOf('// Dashboard/mobile companions remain eager'));
assert(!eagerTail.includes('ensureEtfIntelligence();'));
assert(!eagerTail.includes('ensureScannerCompanion();'));
assert(!eagerTail.includes('ensureAnalysisToolsRuntime();'));
assert(!eagerTail.includes('ensureMarketUiPolish();'));
assert(!eagerTail.includes('ensurePoliticiansCompanion();'));
assert(!eagerTail.includes('ensureMetalsCompanion();'));
assert(!eagerTail.includes('ensureOpportunitySuite();'));
assert(!eagerTail.includes('ensurePortfolioSheetSuite();'));
assert(eagerTail.includes('ensureWeeklyEventsCompanion();'));
assert(eagerTail.includes('ensureDashboardDailyNews();'));
assert(eagerTail.includes('ensureDashboardMarketSentiment();'));
assert(eagerTail.includes('ensureDashboardPortfolioConcentration();'));
assert(source.includes('const etfReady = ensureMarketCompanions();'));
assert(source.includes('await etfReady;'));
assert.deepStrictEqual(Array.from(api.getStocks()), []);
assert(!source.includes("['data/stocks.json'"));

const packed = {
  schema_version: 521, generated_at: '2026-09-05T11:24:25Z', layout: 'field_rows_v1',
  fields: ['ticker','name','score','currency'], rows: [['msft','Microsoft',88,'USD'],['AIR.PA','Airbus',79,'EUR']],
};
const unpacked = api.unpackStartupPayload(packed);
assert.strictEqual(unpacked.layout, undefined);
assert.strictEqual(unpacked.fields, undefined);
assert.strictEqual(unpacked.rows, undefined);
assert.strictEqual(unpacked.stocks[0].ticker, 'msft');
assert.strictEqual(unpacked.stocks[0].score, 88);
assert.strictEqual(unpacked.stocks[1].currency, 'EUR');
assert.strictEqual(api.unpackStartupPayload({layout:'unknown', fields:[], rows:[]}), null);

(async () => {
  const calls = []; const events = [];
  const state = { loaded:false, loading:null,data:null,stocks:[],byTicker:new Map() };
  const loader = api.create({
    state, text:v=>String(v ?? '').trim(),
    fetchImpl:async (url, init)=>{ calls.push([url, init]); return {ok:true,status:200,json:async()=>packed}; },
    beforeReady:()=>events.push(['before',state.loaded,state.stocks.length]),
    onReady:()=>events.push(['ready',state.loaded,state.byTicker.has('MSFT')]),
    onError:err=>events.push(['error',err.message]),
  });
  const p1=loader.ensureLoaded(); const p2=loader.ensureLoaded(); await Promise.all([p1,p2]);
  assert.deepStrictEqual(calls.map(x=>x[0]), ['data/stocks-startup.json']);
  assert(calls.every(x=>x[1] && x[1].cache === 'no-store'));
  assert.strictEqual(state.loaded,true); assert.strictEqual(state.stocks.length,2);
  assert.strictEqual(state.byTicker.get('MSFT').ticker,'msft');
  assert.strictEqual(state.byTicker.get('AIR.PA').ticker,'AIR.PA');
  assert.deepStrictEqual(events,[['before',false,2],['ready',true,true]]);
  assert.strictEqual(state.loading,null); assert.strictEqual(api.getStocks(),state.stocks);
  const callCount=calls.length; await loader.ensureLoaded(); assert.strictEqual(calls.length,callCount);

  const fallbackCalls=[]; const fallbackState={loaded:false,loading:null,data:null,stocks:[],byTicker:new Map()};
  const fallbackResponses=[{ok:false,status:404,json:async()=>({})},{ok:true,status:200,json:async()=>({stocks:[{ticker:'AAPL'}]})}];
  const fallback=api.create({state:fallbackState,fetchImpl:async url=>{fallbackCalls.push(url);return fallbackResponses.shift();}});
  await fallback.ensureLoaded();
  assert.deepStrictEqual(fallbackCalls,['data/stocks-startup.json','data/stocks-index.json']);
  assert.strictEqual(fallbackState.loaded,true); assert.strictEqual(fallbackState.stocks[0].ticker,'AAPL');

  const networkCalls=[]; const networkState={loaded:false,loading:null,data:null,stocks:[],byTicker:new Map()};
  const networkFallback=api.create({
    state:networkState,
    fetchImpl:async url=>{
      networkCalls.push(url);
      if(url==='data/stocks-startup.json') throw new Error('offline');
      return {ok:true,status:200,json:async()=>({stocks:[{ticker:'NVDA'}]})};
    },
  });
  await networkFallback.ensureLoaded();
  assert.deepStrictEqual(networkCalls,['data/stocks-startup.json','data/stocks-index.json']);
  assert.strictEqual(networkState.loaded,true); assert.strictEqual(networkState.stocks[0].ticker,'NVDA');

  const timeoutCalls=[]; const timeoutState={loaded:false,loading:null,data:null,stocks:[],byTicker:new Map()};
  const timeoutFallback=api.create({
    state:timeoutState,
    fetchTimeoutMs:10,
    fetchImpl:async url=>{
      timeoutCalls.push(url);
      if(url==='data/stocks-startup.json') return new Promise(()=>{});
      return {ok:true,status:200,json:async()=>({stocks:[{ticker:'ASML'}]})};
    },
  });
  await timeoutFallback.ensureLoaded();
  assert.deepStrictEqual(timeoutCalls,['data/stocks-startup.json','data/stocks-index.json']);
  assert.strictEqual(timeoutState.loaded,true); assert.strictEqual(timeoutState.stocks[0].ticker,'ASML');
  assert.strictEqual(timeoutState.loading,null);

  const invalidCalls=[]; const invalidState={loaded:false,loading:null,data:null,stocks:[],byTicker:new Map()};
  const invalidResponses=[{ok:true,status:200,json:async()=>({layout:'wrong',fields:[],rows:[]})},{ok:false,status:404,json:async()=>({})}];
  let invalidError='';
  const invalid=api.create({state:invalidState,fetchImpl:async url=>{invalidCalls.push(url);return invalidResponses.shift();},onError:err=>{invalidError=err.message;}});
  await invalid.ensureLoaded(); assert.deepStrictEqual(invalidCalls,['data/stocks-startup.json','data/stocks-index.json']);
  assert.strictEqual(invalidState.loaded,false); assert.strictEqual(invalidError,'market data 404');

  const failedState={loaded:false,loading:null,data:null,stocks:[],byTicker:new Map()}; let errorMessage='';
  const failed=api.create({state:failedState,fetchImpl:async()=>({ok:false,status:503,json:async()=>({})}),onError:err=>{errorMessage=err.message;}});
  await failed.ensureLoaded(); assert.strictEqual(errorMessage,'market data 503');
  assert.strictEqual(failedState.loaded,false); assert.strictEqual(failedState.loading,null);
  assert.strictEqual(api.getStocks(),timeoutState.stocks);
  console.log('market static universe runtime contract: ok');
})().catch(err=>{console.error(err);process.exit(1);});
