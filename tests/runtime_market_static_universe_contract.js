const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-static-universe.js', 'utf8');
const context = { window: {}, console };
vm.createContext(context);
vm.runInContext(source, context);

const api = context.window.VestraMarketStaticUniverse;
assert(api && api.version === '1.0');

(async () => {
  const calls = [];
  const events = [];
  const state = { loaded:false, loading:null, data:null, stocks:[], byTicker:new Map() };
  const responses = [
    { ok:false, status:404, json:async()=>({}) },
    { ok:true, status:200, json:async()=>({ generated_at:'2026-09-01T07:00:00Z', stocks:[{ticker:'msft'},{ticker:'AIR.PA'}] }) },
  ];
  const loader = api.create({
    state,
    text:v=>String(v ?? '').trim(),
    fetchImpl:async (url, init)=>{ calls.push([url, init]); return responses.shift(); },
    beforeReady:()=>events.push(['before', state.loaded, state.stocks.length]),
    onReady:()=>events.push(['ready', state.loaded, state.byTicker.has('MSFT')]),
    onError:err=>events.push(['error', err.message]),
  });

  const p1 = loader.ensureLoaded();
  const p2 = loader.ensureLoaded();
  await Promise.all([p1,p2]);
  assert.deepStrictEqual(calls.map(x=>x[0]), ['data/stocks-index.json','data/stocks.json'], 'concurrent loads must share one fetch sequence');
  assert(calls.every(x=>x[1] && x[1].cache === 'no-store'));
  assert.strictEqual(state.loaded, true);
  assert.strictEqual(state.stocks.length, 2);
  assert.strictEqual(state.byTicker.get('MSFT').ticker, 'msft');
  assert.strictEqual(state.byTicker.get('AIR.PA').ticker, 'AIR.PA');
  assert.deepStrictEqual(events, [['before', false, 2], ['ready', true, true]]);
  assert.strictEqual(state.loading, null);

  const callCount = calls.length;
  await loader.ensureLoaded();
  assert.strictEqual(calls.length, callCount, 'loaded universe must not refetch');

  const failedState = { loaded:false, loading:null, data:null, stocks:[], byTicker:new Map() };
  let errorMessage = '';
  const failed = api.create({
    state: failedState,
    fetchImpl: async () => ({ ok:false, status:503, json:async()=>({}) }),
    onError: err => { errorMessage = err.message; },
  });
  await failed.ensureLoaded();
  assert.strictEqual(errorMessage, 'market data 503');
  assert.strictEqual(failedState.loaded, false);
  assert.strictEqual(failedState.loading, null);

  console.log('market static universe runtime contract: ok');
})().catch(err => { console.error(err); process.exit(1); });
