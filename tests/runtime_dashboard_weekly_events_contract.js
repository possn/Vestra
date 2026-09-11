const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('dashboard-weekly-events.js', 'utf8');
const document = { readyState:'loading', addEventListener:()=>{}, getElementById:()=>null, head:{appendChild:()=>{}} };
const windowObj = { addEventListener:()=>{}, VestraMarketStaticUniverse:{getStocks:()=>[]} };
const context = { window:windowObj, document, console, Date, Intl, Set, Promise, URL, fetch:async()=>({ok:false}), setTimeout:()=>0, clearTimeout:()=>{} };
vm.createContext(context);
vm.runInContext(source, context);

const api = context.window.VestraWeeklyEvents;
assert(api && api.version === '1.6');
assert.strictEqual(typeof api.collectEvents, 'function');
assert.strictEqual(typeof api.collectMacroEvents, 'function');
assert.strictEqual(typeof api.selectEvents, 'function');
assert.strictEqual(typeof api.loadMacroEvents, 'function');
assert.strictEqual(typeof api.parseCalendarDate, 'function');
assert.strictEqual(typeof api.tickerMatchesPortfolio, 'function');
assert.strictEqual(typeof api.officialSourceUrl, 'function');
assert.strictEqual(typeof api.hasMacroResult, 'function');
assert.strictEqual(typeof api.hasMacroPublication, 'function');
assert.strictEqual(typeof api.formatResultValue, 'function');
assert.strictEqual(typeof api.formatEPS, 'function');
assert.strictEqual(typeof api.formatSurprise, 'function');
assert.strictEqual(typeof api.openDetail, 'function');
assert.strictEqual(typeof api.render, 'function');

const now = new Date(2026,8,6,9,0,0);
const stocks = [
  {ticker:'NVDA',name:'NVIDIA',quote_type:'EQUITY',market_cap:4e12,analyst_next_earnings_date:'2026-09-08',analyst_eps_next_q:1.25},
  {ticker:'AAPL',name:'Apple',quote_type:'EQUITY',market_cap:3.5e12,analyst_next_earnings_date:'2026-09-09'},
  {ticker:'SMALL',name:'Small Holding',quote_type:'EQUITY',market_cap:1e7,analyst_next_earnings_date:'2026-09-12'},
  {ticker:'REPORTED',name:'Reported Co',quote_type:'EQUITY',market_cap:12e6,analyst_latest_earnings_date:'2026-09-07',analyst_latest_eps_estimate:.5,analyst_latest_eps_actual:.62,analyst_latest_eps_surprise_pct:.24},
  {ticker:'OLD',name:'Old event',quote_type:'EQUITY',market_cap:9e9,analyst_next_earnings_date:'2026-09-05'},
  {ticker:'LATE',name:'Too late',quote_type:'EQUITY',market_cap:9e9,analyst_next_earnings_date:'2026-09-13'},
  {ticker:'ETF1',name:'Fund',quote_type:'ETF',market_cap:8e9,analyst_next_earnings_date:'2026-09-07'},
];
const macro={events:[
  {date:'2026-09-10',short_title:'PPI EUA',title:'PPI EUA · agosto',category:'inflation',region:'EUA',importance:'high',source:'bls',source_url:'https://www.bls.gov/news.release/ppi.nr0.htm',actual:'0.3',consensus:'0.2',previous:'0.1',unit:'%'},
  {date:'2026-09-11',short_title:'CPI EUA',title:'CPI EUA · agosto',category:'inflation',region:'EUA',importance:'high',source:'bls',source_url:'https://evil.example/fake-cpi'},
  {date:'2026-09-15',short_title:'FOMC',title:'FOMC',category:'central_bank',region:'EUA',importance:'critical',source:'fed'},
]};
const portfolio=new Set(['SMALL']);
const collected=api.collectEvents(stocks,portfolio,now);
assert.deepStrictEqual(Array.from(collected,x=>x.ticker),['NVDA','AAPL','SMALL','REPORTED']);
assert.strictEqual(collected.find(x=>x.ticker==='SMALL').inPortfolio,true);
const reported=collected.find(x=>x.ticker==='REPORTED');
assert.strictEqual(reported.reported,true); assert.strictEqual(reported.epsActual,.62); assert.strictEqual(api.formatEPS(.62),'0,62');
const macroCollected=api.collectMacroEvents(macro,now);
assert.deepStrictEqual(Array.from(macroCollected,x=>x.shortTitle),['PPI EUA','CPI EUA']);
const ppi=macroCollected[0], cpi=macroCollected[1];
assert.strictEqual(api.hasMacroResult(ppi),true); assert.strictEqual(api.hasMacroResult(cpi),false);
assert.strictEqual(ppi.sourceUrl,'https://www.bls.gov/news.release/ppi.nr0.htm');
assert.strictEqual(cpi.sourceUrl,'https://www.bls.gov/bls/newsrels.htm');
assert.strictEqual(api.formatResultValue(ppi.actual,ppi.unit),'0.3 %');
const selected=api.selectEvents(stocks,portfolio,now,4,macro);
assert.deepStrictEqual(Array.from(selected,x=>x.kind==='macro'?x.shortTitle:x.ticker),['NVDA','PPI EUA','CPI EUA','SMALL']);
assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA',new Set(['AIR'])),false);
assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA',new Set(['AIR.PA'])),true);
assert.strictEqual(api.parseCalendarDate(''),null);
assert(source.includes('Resultado ainda não publicado'));
assert(source.includes('Ver publicação oficial'));
assert(source.includes('EPS actual'));
console.log('dashboard weekly events runtime contract: ok');
