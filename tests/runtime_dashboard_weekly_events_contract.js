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
assert(api && api.version === '1.1');
assert.strictEqual(typeof api.collectEvents, 'function');
assert.strictEqual(typeof api.collectMacroEvents, 'function');
assert.strictEqual(typeof api.selectEvents, 'function');
assert.strictEqual(typeof api.loadMacroEvents, 'function');
assert.strictEqual(typeof api.parseCalendarDate, 'function');
assert.strictEqual(typeof api.tickerMatchesPortfolio, 'function');

const now = new Date(2026, 8, 6, 9, 0, 0);
const stocks = [
  { ticker:'NVDA', name:'NVIDIA', quote_type:'EQUITY', market_cap:4_000_000_000_000, analyst_next_earnings_date:'2026-09-08' },
  { ticker:'AAPL', name:'Apple', quote_type:'EQUITY', market_cap:3_500_000_000_000, analyst_next_earnings_date:'2026-09-09' },
  { ticker:'SMALL', name:'Small Holding', quote_type:'EQUITY', market_cap:10_000_000, analyst_next_earnings_date:'2026-09-12' },
  { ticker:'OLD', name:'Old event', quote_type:'EQUITY', market_cap:9_000_000_000, analyst_next_earnings_date:'2026-09-05' },
  { ticker:'LATE', name:'Too late', quote_type:'EQUITY', market_cap:9_000_000_000, analyst_next_earnings_date:'2026-09-13' },
  { ticker:'ETF1', name:'Fund', quote_type:'ETF', market_cap:8_000_000_000, analyst_next_earnings_date:'2026-09-07' },
];
const macro = { events:[
  { date:'2026-09-10', short_title:'PPI EUA', title:'PPI EUA · agosto', category:'inflation', region:'EUA', importance:'high', source:'bls' },
  { date:'2026-09-11', short_title:'CPI EUA', title:'CPI EUA · agosto', category:'inflation', region:'EUA', importance:'high', source:'bls' },
  { date:'2026-09-15', short_title:'FOMC', title:'FOMC', category:'central_bank', region:'EUA', importance:'critical', source:'fed' },
] };

const portfolio = new Set(['SMALL']);
const collected = api.collectEvents(stocks, portfolio, now);
assert.deepStrictEqual(Array.from(collected, x => x.ticker), ['NVDA','AAPL','SMALL']);
assert.strictEqual(collected.find(x => x.ticker === 'SMALL').inPortfolio, true);
const macroCollected = api.collectMacroEvents(macro, now);
assert.deepStrictEqual(Array.from(macroCollected, x => x.shortTitle), ['PPI EUA','CPI EUA']);
assert.strictEqual(macroCollected.some(x => x.shortTitle === 'FOMC'), false, 'outside rolling 7-day window');

const selected = api.selectEvents(stocks, portfolio, now, 4, macro);
assert.deepStrictEqual(Array.from(selected, x => x.kind === 'macro' ? x.shortTitle : x.ticker), ['NVDA','PPI EUA','CPI EUA','SMALL']);
assert.strictEqual(selected.find(x => x.ticker === 'SMALL').inPortfolio, true, 'portfolio earnings reserve a slot after macro events');
assert.strictEqual(selected.some(x => x.ticker === 'AAPL'), false, 'large-cap filler yields to macro + portfolio when capped');

assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AIR'])), true);
assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AIR.PA'])), true);
assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AAPL'])), false);
const plain = api.parseCalendarDate('2026-09-08');
assert.strictEqual(plain.getFullYear(), 2026); assert.strictEqual(plain.getMonth(), 8); assert.strictEqual(plain.getDate(), 8);
assert.strictEqual(api.parseCalendarDate(''), null); assert.strictEqual(api.parseCalendarDate('not-a-date'), null);

console.log('dashboard weekly events runtime contract: ok');
