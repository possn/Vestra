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
