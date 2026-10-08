const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market.js','utf8');

function extractFunction(name){
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, `${name} must exist in market.js`);
  const brace = source.indexOf('{', start);
  let depth = 0, quote = null, escape = false;
  for(let i=brace;i<source.length;i++){
    const ch=source[i];
    if(quote){
      if(escape){escape=false;continue;}
      if(ch==='\\'){escape=true;continue;}
      if(ch===quote)quote=null;
      continue;
    }
    if(ch==="'"||ch==='""'||ch==='\`'){quote=ch;continue;}
    if(ch==='{')depth++;
    else if(ch==='}'&&--depth===0)return source.slice(start,i+1);
  }
  throw new Error(`Could not extract ${name}`);
}

const ctx = {
  n: v => {
    if(v===null||v===undefined||v==='') return null;
    const x=Number(v); return Number.isFinite(x)?x:null;
  }
};
vm.createContext(ctx);
vm.runInContext(extractFunction('cryptoBarometer'),ctx);
vm.runInContext(extractFunction('cryptoRegime'),ctx);
vm.runInContext(extractFunction('cryptoDispersion'),ctx);
vm.runInContext(extractFunction('cryptoFundingLabel'),ctx);
vm.runInContext(extractFunction('cryptoSigned'),ctx);
vm.runInContext(extractFunction('cryptoRegimeChange'),ctx);

const neutral = ctx.cryptoBarometer([
  {symbol:'BTC',change_pct:0,fifty_two_week_high:100,price:80},
  {symbol:'ETH',change_pct:0,fifty_two_week_high:100,price:80},
  {symbol:'SOL',change_pct:0,fifty_two_week_high:100,price:80},
  {symbol:'XRP',change_pct:0,fifty_two_week_high:100,price:80},
]);
assert(neutral.score >= 0 && neutral.score <= 100,'Crypto barometer must stay bounded 0..100');
assert.strictEqual(neutral.breadth,0,'zero changes are not positive breadth');

const strong = ctx.cryptoBarometer([
  {symbol:'BTC',change_pct:4,fifty_two_week_high:100,price:95},
  {symbol:'ETH',change_pct:5,fifty_two_week_high:100,price:92},
  {symbol:'SOL',change_pct:7,fifty_two_week_high:100,price:90},
  {symbol:'XRP',change_pct:3,fifty_two_week_high:100,price:88},
]);
assert(strong.score > neutral.score,'broad positive crypto momentum must improve the transparent barometer');

const stressed = ctx.cryptoBarometer([
  {symbol:'BTC',change_pct:-6,fifty_two_week_high:100,price:55},
  {symbol:'ETH',change_pct:-7,fifty_two_week_high:100,price:50},
  {symbol:'SOL',change_pct:-8,fifty_two_week_high:100,price:45},
  {symbol:'XRP',change_pct:-4,fifty_two_week_high:100,price:60},
]);
assert(stressed.score < neutral.score,'broad negative crypto momentum must reduce the barometer');

assert(source.includes("M.mode==='crypto'?renderCrypto()"),'Crypto must be a first-class Market mode');
assert(source.includes("data-crypto-symbol"),'Crypto rows must open their own dossier');
assert(!source.includes("portfolioConviction(row)"),'Crypto market rows must not enter equity Conviction');
assert(source.includes("Esta posição continua separada do motor fundamental, Conviction e Risk Gate de equities."),'Crypto dossier must explicitly preserve equity-engine separation');

console.log('crypto market deterministic contract: ok');


const regimeAlt = ctx.cryptoRegime([
  {symbol:'BTC',change_pct:1},
  {symbol:'ETH',change_pct:4},
  {symbol:'SOL',change_pct:5},
  {symbol:'XRP',change_pct:3}
], {global:{btc_dominance_pct:52}});
assert.strictEqual(regimeAlt.label,'Altcoins a liderar');
assert.strictEqual(regimeAlt.dominance,52);

const regimeBtc = ctx.cryptoRegime([
  {symbol:'BTC',change_pct:5},
  {symbol:'ETH',change_pct:1},
  {symbol:'SOL',change_pct:0},
  {symbol:'XRP',change_pct:1}
], {});
assert.strictEqual(regimeBtc.label,'Bitcoin a liderar');

assert(ctx.cryptoDispersion([{change_pct:-2},{change_pct:0},{change_pct:2}]) > 0,'cross-sectional crypto dispersion must be measurable');
assert.strictEqual(ctx.cryptoFundingLabel(null),'—','missing funding must stay unavailable, never neutral');
assert.strictEqual(ctx.cryptoFundingLabel(0.06),'Longs muito carregados');
assert.strictEqual(ctx.cryptoFundingLabel(-0.06),'Shorts muito carregados');

const worker = fs.readFileSync('worker.js','utf8');
assert(worker.includes('"/crypto-intelligence"'),'Worker must expose the Crypto intelligence endpoint');
assert(worker.includes('https://api.alternative.me/fng/'),'Fear & Greed source must remain explicit');
assert(worker.includes('https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT'),'BTC funding must use a public derivatives endpoint');
assert(worker.includes('https://api.coingecko.com/api/v3/global'),'global dominance/market-cap source must remain explicit');
assert(worker.includes('source: globalData?.data ? "CoinGecko"'),'global source attribution must remain explicit and fail closed');


const improving = ctx.cryptoRegimeChange(
  {change_7d:12,change_30d:20},
  {btc:{open_interest_change_7d_pct:8,funding_rate_pct:0.02,funding_avg_30d_pct:0.01}}
);
assert.strictEqual(improving.label,'Apetite e alavancagem a subir');
assert(improving.parts.some(x=>x.includes('sentimento 7d +12 pts')));

const deleveraging = ctx.cryptoRegimeChange(
  {change_7d:-15,change_30d:-22},
  {btc:{open_interest_change_7d_pct:-9,funding_rate_pct:-0.01,funding_avg_30d_pct:0.01}}
);
assert.strictEqual(deleveraging.label,'Desalavancagem defensiva');

assert(worker.includes('limit=31&format=json'),'Fear & Greed history must request enough observations for 30-day context');
assert(worker.includes('fundingRate?symbol=BTCUSDT&limit=100'),'BTC funding history must cover roughly 30 days');
assert(worker.includes('period=1d&limit=30'),'open-interest history must use daily observations for the 30-day window');
assert(worker.includes('history_30d: fngHistory'),'Worker must expose the Fear & Greed time series');
assert(worker.includes('open_interest_change_7d_pct'),'Worker must expose 7-day open-interest change');
assert(worker.includes('funding_avg_30d_pct'),'Worker must expose 30-day funding baseline');
assert(!worker.includes('btc_dominance_history'),'Dominance history must not be fabricated without persistent storage or a verified source');


const indexHtml = fs.readFileSync('index.html','utf8');
const runtimeLoader = fs.readFileSync('market-runtime-loader.js','utf8');
const serviceWorker = fs.readFileSync('sw.js','utf8');

assert(indexHtml.includes('data-market-mode="crypto"'),'Crypto tab button must ship in the app shell');
assert(indexHtml.includes('market-runtime-loader.js?v=2.3'),'index must request the Crypto-aware Market loader generation');
assert(runtimeLoader.includes("const SRC = 'market.js?v=20261007crypto1';"),'Market core URL must change when the Crypto generation ships');
assert(runtimeLoader.includes("script.src = 'market.js?v=20261007crypto1';"),'Market loader must expose a literal versioned core URL so the reachability audit can follow it');
assert(serviceWorker.includes('const CACHE_NAME = "vestra-cache-v239";'),'service worker cache generation must advance with the Crypto release');
assert(/BOOTSTRAP_NETWORK_FIRST[\s\S]*"market\.js"/.test(serviceWorker),'installed PWA must fetch market.js network-first instead of serving a stale exact cache entry');


const router = fs.readFileSync('worker-router.js','utf8');
assert(router.includes('?interval=1d&range=1y'),'Crypto quote fallback must fetch enough history for 52-week range');
assert(router.includes('const highs = Array.isArray(quote.high)'),'chart fallback must derive 52-week highs');
assert(router.includes('const lows = Array.isArray(quote.low)'),'chart fallback must derive 52-week lows');
assert(router.includes('closes.length>=2 ? closes.at(-2) : null'),'chart fallback must derive previous close when Yahoo meta omits it');
assert(router.includes('fifty_two_week_high:high52'),'chart fallback must expose the 52-week high');
assert(router.includes('fifty_two_week_low:low52'),'chart fallback must expose the 52-week low');

assert(worker.includes('https://api.coinpaprika.com/v1/global'),'global Crypto intelligence must retain CoinPaprika redundancy');
assert(worker.includes('https://api.coinlore.net/api/global/'),'global Crypto intelligence must have a third independent public source');
assert(worker.includes('"CoinLore"'),'global source attribution must expose CoinLore fallback');
assert(worker.includes('https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP'),'derivatives must have an OKX public funding fallback');
assert(worker.includes('https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history?instId=BTC-USDT-SWAP&period=1D&limit=30'),'derivatives must have OKX 30-day open-interest history');
assert(worker.includes('"OKX"'),'derivatives source attribution must expose OKX fallback');
assert(!worker.includes('api.bybit.com/v5/market'),'known-unreliable Bybit fallback must not remain on the critical production path');
assert(worker.includes('crypto-intelligence-v3'),'Crypto intelligence cache key must advance so stale partial payloads are not reused');
