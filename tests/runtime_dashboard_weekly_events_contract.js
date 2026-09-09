const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('dashboard-weekly-events.js', 'utf8');
const document = { readyState:'loading', addEventListener:()=>{}, getElementById:()=>null, head:{appendChild:()=>{}} };
const windowObj = { addEventListener:()=>{}, VestraMarketStaticUniverse:{getStocks:()=>[]} };
const context = { window:windowObj, document, console, Date, Intl, Set, Promise, fetch:async()=>({ok:false}), setTimeout:()=>0, clearTimeout:()=>{} };
vm.createContext(context);
vm.runInContext(source, context);

const api = context.window.VestraWeeklyEvents;
assert(api && api.version === '1.3');
assert.strictEqual(typeof api.collectEvents, 'function');
assert.strictEqual(typeof api.collectMacroEvents, 'function');
assert.strictEqual(typeof api.selectEvents, 'function');
assert.strictEqual(typeof api.loadMacroEvents, 'function');
assert.strictEqual(typeof api.parseCalendarDate, 'function');
assert.strictEqual(typeof api.tickerMatchesPortfolio, 'function');
assert.strictEqual(typeof api.hasMacroResult, 'function');
assert.strictEqual(typeof api.formatResultValue, 'function');
assert.strictEqual(typeof api.formatEPS, 'function');
assert.strictEqual(typeof api.formatSurprise, 'function');
assert.strictEqual(typeof api.openDetail, 'function');

const now = new Date(2026, 8, 6, 9, 0, 0);
const stocks = [
  { ticker:'NVDA', name:'NVIDIA', quote_type:'EQUITY', market_cap:4_000_000_000_000, analyst_next_earnings_date:'2026-09-08', analyst_eps_next_q:1.25 },
  { ticker:'AAPL', name:'Apple', quote_type:'EQUITY', market_cap:3_500_000_000_000, analyst_next_earnings_date:'2026-09-09' },
  { ticker:'SMALL', name:'Small Holding', quote_type:'EQUITY', market_cap:10_000_000, analyst_next_earnings_date:'2026-09-12' },
  { ticker:'REPORTED', name:'Reported Co', quote_type:'EQUITY', market_cap:12_000_000, analyst_latest_earnings_date:'2026-09-07', analyst_latest_eps_estimate:0.50, analyst_latest_eps_actual:0.62, analyst_latest_eps_surprise_pct:0.24 },
  { ticker:'OLD', name:'Old event', quote_type:'EQUITY', market_cap:9_000_000_000, analyst_next_earnings_date:'2026-09-05' },
  { ticker:'LATE', name:'Too late', quote_type:'EQUITY', market_cap:9_000_000_000, analyst_next_earnings_date:'2026-09-13' },
  { ticker:'ETF1', name:'Fund', quote_type:'ETF', market_cap:8_000_000_000, analyst_next_earnings_date:'2026-09-07' },
];
const macro = { events:[
  { date:'2026-09-10', short_title:'PPI EUA', title:'PPI EUA · agosto', category:'inflation', region:'EUA', importance:'high', source:'bls', actual:'0.3', consensus:'0.2', previous:'0.1', unit:'%' },
  { date:'2026-09-11', short_title:'CPI EUA', title:'CPI EUA · agosto', category:'inflation', region:'EUA', importance:'high', source:'bls' },
  { date:'2026-09-15', short_title:'FOMC', title:'FOMC', category:'central_bank', region:'EUA', importance:'critical', source:'fed' },
] };

const portfolio = new Set(['SMALL']);
const collected = api.collectEvents(stocks, portfolio, now);
assert.deepStrictEqual(Array.from(collected, x => x.ticker), ['NVDA','AAPL','SMALL','REPORTED']);
assert.strictEqual(collected.find(x => x.ticker === 'SMALL').inPortfolio, true);
const reported = collected.find(x => x.ticker === 'REPORTED');
assert.strictEqual(reported.reported, true);
assert.strictEqual(reported.epsEstimate, 0.50);
assert.strictEqual(reported.epsActual, 0.62);
assert.strictEqual(reported.epsSurprisePct, 0.24);
assert.strictEqual(api.formatEPS(reported.epsActual), '0,62');
assert.strictEqual(api.formatSurprise(reported.epsSurprisePct), '24,0%');
const nvda = collected.find(x => x.ticker === 'NVDA');
assert.strictEqual(nvda.reported, false);
assert.strictEqual(nvda.epsEstimate, 1.25);
assert.strictEqual(nvda.epsActual, null, 'future earnings actual must remain missing');

const macroCollected = api.collectMacroEvents(macro, now);
assert.deepStrictEqual(Array.from(macroCollected, x => x.shortTitle), ['PPI EUA','CPI EUA']);
assert.strictEqual(macroCollected.some(x => x.shortTitle === 'FOMC'), false, 'outside rolling 7-day window');
const ppi = macroCollected.find(x => x.shortTitle === 'PPI EUA');
const cpi = macroCollected.find(x => x.shortTitle === 'CPI EUA');
assert.strictEqual(ppi.actual, '0.3');
assert.strictEqual(ppi.consensus, '0.2');
assert.strictEqual(ppi.previous, '0.1');
assert.strictEqual(api.hasMacroResult(ppi), true);
assert.strictEqual(api.hasMacroResult(cpi), false, 'missing result must stay missing');
assert.strictEqual(api.formatResultValue(ppi.actual, ppi.unit), '0.3 %');
assert.strictEqual(api.formatResultValue(null, '%'), '—');

const selected = api.selectEvents(stocks, portfolio, now, 4, macro);
assert.deepStrictEqual(Array.from(selected, x => x.kind === 'macro' ? x.shortTitle : x.ticker), ['NVDA','PPI EUA','CPI EUA','SMALL']);
assert.strictEqual(selected.find(x => x.ticker === 'SMALL').inPortfolio, true, 'portfolio earnings reserve a slot after macro events');
assert.strictEqual(selected.some(x => x.ticker === 'AAPL'), false, 'large-cap filler yields to macro + portfolio when capped');

assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AIR'])), false, 'portfolio identity must be exact');
assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AIR.PA'])), true);
assert.strictEqual(api.tickerMatchesPortfolio('ADM.L', new Set(['ADM'])), false, 'exchange suffix collision must not mark a different company as owned');
const plain = api.parseCalendarDate('2026-09-08');
assert.strictEqual(plain.getFullYear(), 2026); assert.strictEqual(plain.getMonth(), 8); assert.strictEqual(plain.getDate(), 8);
assert.strictEqual(api.parseCalendarDate(''), null); assert.strictEqual(api.parseCalendarDate('not-a-date'), null);

assert(source.includes("dataset.weeklyEventIndex"), 'all weekly event cards expose the tappable detail contract');
assert(source.includes("data-weekly-detail-ticker") || source.includes("dataset.weeklyDetailTicker"), 'earnings detail keeps dossier handoff');
assert(source.includes('Actual') && source.includes('Consenso') && source.includes('Anterior'), 'macro detail exposes result triplet');
assert(source.includes('EPS actual') && source.includes('Estimativa') && source.includes('Surpresa'), 'earnings detail exposes reported result triplet');
assert(source.includes('Resultado ainda não publicado'), 'future/missing macro values are explicit rather than fabricated');
assert(source.includes('Resultados ainda não publicados'), 'future earnings values are explicit rather than fabricated');

console.log('dashboard weekly events runtime contract: ok');