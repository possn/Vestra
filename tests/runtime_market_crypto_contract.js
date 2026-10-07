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
assert(worker.includes('source: globalData?.data ? "CoinGecko" : null'),'missing global source must stay null instead of fabricated');
