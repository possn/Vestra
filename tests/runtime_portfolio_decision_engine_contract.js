const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market.js', 'utf8');

function extractFunction(name){
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, `${name} must exist in market.js`);
  const open = source.indexOf('{', start);
  assert(open >= 0, `${name} opening brace missing`);
  let depth = 0;
  for(let i=open;i<source.length;i++){
    if(source[i]==='{') depth++;
    else if(source[i]==='}'){
      depth--;
      if(depth===0) return source.slice(start,i+1);
    }
  }
  throw new Error(`${name} closing brace missing`);
}

let targets = {
  maxPosition:10,
  maxSector:25,
  maxFactor:45,
  maxCurrency:70,
  maxRegion:70,
  overlap:'reduce',
  tilt:'balanced',
};

const context = {
  console,
  Math,
  loadPortfolioTargets: () => ({...targets}),
  riskBudgetPenalty: stock => Number(stock?._riskPenalty || 0),
  isFund: stock => ['ETF','FUND','MUTUALFUND'].includes(String(stock?.quote_type || '').toUpperCase()),
  n: value => {
    if(value===null || value===undefined || value==='') return null;
    const x = Number(value);
    return Number.isFinite(x) ? x : null;
  },
  txt: value => String(value ?? '').trim().toLowerCase(),
};
vm.createContext(context);
vm.runInContext(extractFunction('portfolioMoveEvidence'), context, {filename:'portfolioMoveEvidence'});
vm.runInContext(extractFunction('evaluatePortfolioMove'), context, {filename:'evaluatePortfolioMove'});

const evaluate = context.evaluatePortfolioMove;
assert.strictEqual(typeof evaluate, 'function');

const sourceStock = {ticker:'SRC', quote_type:'EQUITY', score:55, confidence_score:80};
const strong = {
  ticker:'DST', quote_type:'EQUITY', score:75, confidence_score:80,
  valuation_signal:'fair', estimate_signal:'stable', thesis_direction:'up', risk_gate:'clear',
};

function replacement(destination=strong, overrides={}){
  return evaluate({
    mode:'replace',
    sourceStock,
    destination,
    rows:[],
    amount:100,
    totalAfter:1000,
    sourceConv:50,
    destinationConv:60,
    positionPct:10,
    sectorPct:20,
    indirect:0,
    sourceIndirect:0,
    ...overrides,
  });
}

let result = replacement();
assert.strictEqual(result.autoEligible, true, 'robust positive replacement should be eligible');
assert.strictEqual(result.convictionGain, 10);
assert.strictEqual(result.convDelta, 1);

result = replacement({...strong, risk_gate:'watch'});
assert.strictEqual(result.autoEligible, false, 'Risk Gate watch must block automation');
assert(result.warnings.includes('Risk Gate watch'));

result = replacement(strong,{indirect:3,sourceIndirect:0});
assert.strictEqual(result.autoEligible, false, 'material overlap increase must block automation');
assert(result.warnings.includes('aumenta overlap'));

result = replacement({...strong,_riskPenalty:6});
assert.strictEqual(result.autoEligible, false, 'risk budget penalty must block automation');
assert(result.warnings.includes('pressiona orçamento de risco'));

result = evaluate({
  mode:'replace',
  sourceStock:{...sourceStock,quote_type:'ETF'},
  destination:strong,
  rows:[],
  amount:100,totalAfter:1000,sourceConv:50,destinationConv:60,
  positionPct:10,sectorPct:20,indirect:0,sourceIndirect:0,
});
assert.strictEqual(result.autoEligible, false, 'ETF source must stay manual in stock replacement engine');
assert(result.warnings.includes('origem apenas para análise manual'));

result = evaluate({
  mode:'alternative',
  sourceStock,
  destination:strong,
  rows:[],
  amount:100,totalAfter:1000,sourceConv:50,destinationConv:54,
  positionPct:10,sectorPct:20,indirect:1.4,sourceIndirect:0,
});
assert.strictEqual(result.autoEligible, false, 'alternative needs at least +5 conviction');

result = evaluate({
  mode:'alternative',
  sourceStock,
  destination:strong,
  rows:[],
  amount:100,totalAfter:1000,sourceConv:50,destinationConv:55,
  positionPct:10,sectorPct:20,indirect:1.4,sourceIndirect:0,
});
assert.strictEqual(result.autoEligible, true, 'alternative with +5 conviction and controlled risk should pass');

result = evaluate({
  mode:'fresh',
  destination:strong,
  rows:[],
  amount:100,totalAfter:1000,destinationConv:70,
  positionPct:11,sectorPct:20,indirect:0,sourceIndirect:0,
});
assert.strictEqual(result.autoEligible, false, 'fresh capital must respect max position');
assert(result.warnings.includes('excede objetivo por posição'));

result = evaluate({
  mode:'fresh',
  destination:strong,
  rows:[],
  amount:100,totalAfter:1000,destinationConv:70,
  positionPct:8,sectorPct:20,indirect:2.2,sourceIndirect:0,
});
assert.strictEqual(result.autoEligible, false, 'fresh capital must respect reduce-overlap target');
assert(result.warnings.includes('overlap elevado'));

result = evaluate({
  mode:'scenario',
  sourceStock,
  destination:strong,
  rows:[],
  amount:100,totalAfter:1000,sourceConv:60,destinationConv:59,
  positionPct:10,sectorPct:20,indirect:0,sourceIndirect:0,
});
assert.strictEqual(result.autoEligible, false, 'negative conviction scenario must not be eligible');

console.log('Portfolio decision engine runtime contract: ok');
