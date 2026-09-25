const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market.js', 'utf8');

function extractFunction(name) {
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, `${name} must exist in market.js`);
  const paramsStart = source.indexOf('(', start);
  let parens = 0, quote = null, escape = false, paramsEnd = -1;
  for (let i = paramsStart; i < source.length; i++) {
    const ch = source[i];
    if (quote) {
      if (escape) { escape = false; continue; }
      if (ch === '\\') { escape = true; continue; }
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === '`') { quote = ch; continue; }
    if (ch === '(') parens++;
    else if (ch === ')' && --parens === 0) { paramsEnd = i; break; }
  }
  assert(paramsEnd >= 0, `${name} parameters must close`);
  const brace = source.indexOf('{', paramsEnd);
  assert(brace >= 0, `${name} must have a body`);
  let depth = 0; quote = null; escape = false;
  for (let i = brace; i < source.length; i++) {
    const ch = source[i];
    if (quote) {
      if (escape) { escape = false; continue; }
      if (ch === '\\') { escape = true; continue; }
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === '`') { quote = ch; continue; }
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) return source.slice(start, i + 1);
    }
  }
  throw new Error(`Could not extract ${name}`);
}

let riskPenalty = 0;
const targets = {
  maxPosition: 10,
  maxSector: 25,
  overlap: 'reduce',
  maxFactor: 45,
  maxCurrency: 70,
  maxRegion: 70,
};

const context = {
  console,
  txt: v => String(v ?? '').trim(),
  n: v => {
    const x = Number(v);
    return Number.isFinite(x) ? x : null;
  },
  isFund: stock => stock?.kind === 'ETF' || stock?.asset_type === 'ETF',
  loadPortfolioTargets: () => ({ ...targets }),
  riskBudgetPenalty: () => riskPenalty,
};
vm.createContext(context);
vm.runInContext(extractFunction('portfolioMoveEvidence'), context);
vm.runInContext(extractFunction('evaluatePortfolioMove'), context);

const evaluate = args => context.evaluatePortfolioMove(args);
const stock = overrides => ({
  ticker: 'DEST',
  score: 82,
  confidence_score: 80,
  valuation_signal: 'fair',
  estimate_signal: 'stable',
  thesis_direction: 'flat',
  risk_gate: 'clear',
  ...overrides,
});
const sourceStock = overrides => stock({ ticker: 'SRC', score: 64, confidence_score: 75, ...overrides });
const base = {
  sourceStock: sourceStock(),
  destination: stock(),
  rows: [],
  amount: 100,
  totalAfter: 1000,
  sourceConv: 55,
  destinationConv: 70,
  positionPct: 8,
  sectorPct: 20,
  indirect: 0.5,
  sourceIndirect: 0.5,
};

riskPenalty = 0;
let r = evaluate({ mode: 'replace', ...base });
assert.strictEqual(r.autoEligible, true, 'robust replacement should be auto-eligible');
assert(r.convictionGain >= 2);
assert(r.convDelta > 0);

r = evaluate({ mode: 'replace', ...base, destination: stock({ risk_gate: 'watch' }) });
assert.strictEqual(r.autoEligible, false, 'Risk Gate watch must block automatic action');
assert(r.warnings.includes('Risk Gate watch'));

riskPenalty = 6;
r = evaluate({ mode: 'replace', ...base });
assert.strictEqual(r.autoEligible, false, 'risk-budget penalty >=5 must block automatic action');
assert(r.warnings.includes('pressiona orçamento de risco'));

riskPenalty = 0;
r = evaluate({ mode: 'alternative', ...base, indirect: 2.0, sourceIndirect: 0.5 });
assert.strictEqual(r.autoEligible, false, 'alternative overlap increase >=1.5pp must be rejected');
assert(r.warnings.includes('aumenta overlap'));

r = evaluate({ mode: 'alternative', ...base, destinationConv: 59 });
assert.strictEqual(r.autoEligible, false, 'alternative conviction gain below 5 must be rejected');
assert(r.warnings.includes('melhoria de convicção insuficiente'));

r = evaluate({ mode: 'replace', ...base, sourceStock: sourceStock({ kind: 'ETF' }) });
assert.strictEqual(r.autoEligible, false, 'ETF source must not be auto-replaced by stock logic');
assert(r.warnings.includes('origem apenas para análise manual'));

r = evaluate({
  mode: 'fresh',
  destination: stock(),
  rows: [],
  amount: 100,
  totalAfter: 1100,
  destinationConv: 70,
  positionPct: 10.1,
  sectorPct: 20,
  indirect: 0.5,
});
assert.strictEqual(r.autoEligible, false, 'fresh capital must respect max-position target');
assert(r.warnings.includes('excede objetivo por posição'));

r = evaluate({
  mode: 'fresh',
  destination: stock(),
  rows: [],
  amount: 100,
  totalAfter: 1100,
  destinationConv: 70,
  positionPct: 8,
  sectorPct: 25.1,
  indirect: 0.5,
});
assert.strictEqual(r.autoEligible, false, 'fresh capital must respect max-sector target');
assert(r.warnings.includes('excede objetivo setorial'));

riskPenalty = 6;
r = evaluate({ mode: 'scenario', ...base });
assert.strictEqual(r.autoEligible, false, 'scenario with positive conviction but excessive risk budget must not be eligible');

riskPenalty = 0;
r = evaluate({ mode: 'scenario', ...base, destinationConv: 50 });
assert.strictEqual(r.autoEligible, false, 'scenario with negative conviction delta must not be eligible');

r = evaluate({ mode: 'fresh', ...base, sourceStock: null, indirect: 2.1, positionPct: 8, sectorPct: 20 });
assert.strictEqual(r.autoEligible, false, 'fresh capital must respect reduce-overlap target');
assert(r.warnings.includes('overlap elevado'));

console.log('portfolio decision engine deterministic contract: ok');
