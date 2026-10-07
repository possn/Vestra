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
    if (v === null || v === undefined || v === '') return null;
    const x = Number(v);
    return Number.isFinite(x) ? x : null;
  },
  isFund: stock => stock?.kind === 'ETF' || stock?.asset_type === 'ETF',
  stockRiskTags: stock => stock?.riskTags ?? ['Core'],
  riskBudgetCoverage: () => ({ ready:true, researchCoverage:100, factorCoverage:100 }),
  loadPortfolioTargets: () => ({ ...targets }),
  riskBudgetPenalty: () => riskPenalty,
};
vm.createContext(context);
vm.runInContext(extractFunction('portfolioConviction'), context);
vm.runInContext(extractFunction('portfolioMoveEvidence'), context);
vm.runInContext(extractFunction('portfolioSourceEvidenceReady'), context);
vm.runInContext(extractFunction('evaluatePortfolioMove'), context);


let riskProfileValues = { factor:550, usd:800, northAmerica:750, total:1000 };
const riskContext = {
  n: context.n,
  loadPortfolioTargets: () => ({ maxFactor:45, maxCurrency:70, maxRegion:70 }),
  portfolioRiskProfile: (_rows,total) => ({
    factors:[{name:'Growth',value:riskProfileValues.factor,pct:riskProfileValues.factor/total*100}],
    currencies:[
      {name:'USD',value:riskProfileValues.usd,pct:riskProfileValues.usd/total*100},
      {name:'EUR',value:riskProfileValues.total-riskProfileValues.usd,pct:(riskProfileValues.total-riskProfileValues.usd)/total*100},
    ],
    regions:[
      {name:'Am. Norte',value:riskProfileValues.northAmerica,pct:riskProfileValues.northAmerica/total*100},
      {name:'Europa',value:riskProfileValues.total-riskProfileValues.northAmerica,pct:(riskProfileValues.total-riskProfileValues.northAmerica)/total*100},
    ],
  }),
  stockRiskTags: stock => stock?.tags || [],
  stockCurrency: stock => stock?.currency || 'USD',
  stockRegion: stock => stock?.region || 'Am. Norte',
};
vm.createContext(riskContext);
vm.runInContext(extractFunction('riskBudgetPenalty'), riskContext);
const riskBudget = (destination, source=null, amount=100, totalAfter=1000, totalBefore=null) =>
  riskContext.riskBudgetPenalty(destination, [], amount, totalAfter, source, totalBefore);

assert.strictEqual(
  riskBudget({tags:['Growth'],currency:'USD',region:'Am. Norte'},{tags:['Growth'],currency:'USD',region:'Am. Norte'}),
  0,
  'replacement with identical already-over-limit exposures must not pay inherited Risk Budget excess again'
);
assert.strictEqual(
  riskBudget({tags:[],currency:'EUR',region:'Europa'},{tags:['Growth'],currency:'USD',region:'Am. Norte'}),
  0,
  'move that reduces inherited concentration must not be penalised'
);
const worsened = riskBudget(
  {tags:['Growth'],currency:'USD',region:'Am. Norte'},
  {tags:[],currency:'EUR',region:'Europa'}
);
assert(Math.abs(worsened-(10*.65+10*.55+10*.45))<1e-9, 'replacement that worsens existing breaches must pay only the incremental excess');

riskProfileValues = { factor:440, usd:690, northAmerica:690, total:1000 };
const crossedLimit = riskBudget({tags:['Growth'],currency:'USD',region:'Am. Norte'},null,100,1100,1000);
const crossedExpected=((540/1100*100-45)*.65)+((790/1100*100-70)*.55)+((790/1100*100-70)*.45);
assert(
  Math.abs(crossedLimit-crossedExpected)<1e-9,
  'move from below the limit must pay only the newly-created excess above each Risk Budget limit'
);

riskProfileValues = { factor:550, usd:800, northAmerica:750, total:1000 };
const freshIntoInheritedBreach = riskBudget({tags:['Growth'],currency:'USD',region:'Am. Norte'},null,100,1100,1000);
const inheritedExpected=
  (((650/1100*100-45)-(55-45))*.65)+
  (((900/1100*100-70)-(80-70))*.55)+
  (((850/1100*100-70)-(75-70))*.45);
assert(
  Math.abs(freshIntoInheritedBreach-inheritedExpected)<1e-9,
  'fresh capital must compare after-trade excess with the true pre-trade portfolio, not a diluted totalAfter baseline'
);

const conviction = stock => context.portfolioConviction(stock);
assert(Math.abs(conviction({ score: 80, score_raw: 80, estimate_momentum_score: 70, valuation_signal: 'fair', thesis_direction: 'flat' }) - 76.1) < 1e-9, 'conviction must keep fixed 70/12/18 weights');
assert.strictEqual(conviction({ score: 59, score_raw: 80, thesis_direction: 'flat' }), 71, 'Conviction must use raw fundamental attractiveness, not the confidence-capped public Score');
assert.strictEqual(conviction({ score: null, score_raw: 80, estimate_momentum_score: 90, valuation_signal: 'undervalued' }), 82.1, 'suppressed public Score must not erase Conviction when raw factor evidence exists');
assert.strictEqual(conviction({ score: null, score_raw: null, estimate_momentum_score: 90, valuation_signal: 'undervalued' }), null, 'Conviction still requires a fundamental factor score');
assert.strictEqual(
  conviction({ score: 80, estimate_momentum_score: 30, valuation_signal: 'fair', estimate_signal: 'deteriorating', thesis_direction: 'flat' }),
  conviction({ score: 80, estimate_momentum_score: 30, valuation_signal: 'fair', estimate_signal: 'stable', thesis_direction: 'flat' }),
  'estimate_signal must not add a second momentum penalty outside estimate_momentum_score'
);
assert(!source.includes('||b.valuationRank-a.valuationRank'), 'portfolio ranking must not re-score valuation after Conviction');
assert(!source.includes('if(!decision.autoEligible||scoreDelta<3)'), 'alternative selection must not add a second Score gate after canonical move eligibility');
assert(!source.includes("||thesis==='down'||estimates==='deteriorating'||(conviction!=null&&conviction<50)"), 'Portfolio Action must not re-apply thesis/estimate signals after Conviction');
const evidenceBlock = source.split('function portfolioMoveEvidence(stock, conviction=null){', 2)[1]?.split('\n  function evaluatePortfolioMove', 1)[0] || '';
assert(!evidenceBlock.includes('valuation_signal'), 'Evidence gate must not re-apply valuation after Conviction');
assert(!evidenceBlock.includes('estimate_signal'), 'Evidence gate must not re-apply estimate momentum after Conviction');
assert(!evidenceBlock.includes('thesis_direction'), 'Evidence gate must not re-apply thesis direction after Conviction');
assert(!source.includes('||Number(y.thesisDown)-Number(x.thesisDown)'), 'research review ordering must not reweight thesis direction after Conviction');
assert(!source.includes('||Number(y.estimatesDown)-Number(x.estimatesDown)'), 'research review ordering must not reweight estimate direction after Conviction');
const multiMoveBlock = source.split('function buildMultiMovePlan(){', 2)[1]?.split('\n  function renderMultiMovePlan', 1)[0] || '';
assert(!multiMoveBlock.includes('thesisDown'), 'multi-move source selection must not re-apply thesis direction after Conviction');
assert(!multiMoveBlock.includes('estimatesDown'), 'multi-move source selection must not re-apply estimate direction after Conviction');

const coverageContext = {
  n: context.n,
  stockRiskTags: stock => stock?.riskTags || [],
};
vm.createContext(coverageContext);
vm.runInContext(extractFunction('riskBudgetCoverage'), coverageContext);
let coverageState = coverageContext.riskBudgetCoverage([
  { value: 20, stock:{riskTags:['Growth']} },
  { value: 10, stock:{riskTags:[]} },
], 100);
assert.strictEqual(coverageState.ready, false, 'Risk Budget must fail closed when portfolio research/factor coverage is below 35%');
assert.strictEqual(coverageState.researchCoverage, 30);
assert.strictEqual(coverageState.factorCoverage, 20);
coverageState = coverageContext.riskBudgetCoverage([
  { value: 30, stock:{riskTags:['Growth']} },
  { value: 10, stock:{riskTags:[]} },
], 100);
assert.strictEqual(coverageState.ready, false, 'research coverage alone is insufficient when factor coverage is below 35%');
coverageState = coverageContext.riskBudgetCoverage([
  { value: 40, stock:{riskTags:['Growth']} },
], 100);
assert.strictEqual(coverageState.ready, true, 'portfolio Risk Budget becomes ready once both research and factor coverage reach the existing 35% threshold');

const evaluate = args => context.evaluatePortfolioMove(args);
const stock = overrides => ({
  ticker: 'DEST',
  score: 82,
  confidence_score: 80,
  valuation_signal: 'fair',
  estimate_signal: 'stable',
  thesis_direction: 'flat',
  risk_gate: 'clear',
  score_reliability: 'robust',
  data_coverage_pct: 82,
  critical_metric_coverage_pct: 75,
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

r = evaluate({ mode: 'replace', ...base, destination: stock({ score: null }), destinationConv: 70 });
assert.strictEqual(r.autoEligible, false, 'missing destination Score must block automatic action even if a caller injects Conviction');
assert.strictEqual(r.evidence.strict, false, 'missing destination Score must never be strict evidence');
assert.strictEqual(r.evidence.acceptable, false, 'missing destination Score must not be ranked as acceptable evidence');
assert(r.warnings.includes('Vestra Score indisponível'));

r = evaluate({ mode: 'replace', ...base, destination: stock({ confidence_score: null }) });
assert.strictEqual(r.autoEligible, false, 'missing destination Confidence must block automatic action');
assert.strictEqual(r.evidence.tier, 'research', 'missing Confidence must not be promoted to acceptable manual evidence');
assert(r.warnings.includes('confiança sem score'));

r = evaluate({ mode: 'replace', ...base, destination: stock({ risk_gate: null }) });
assert.strictEqual(r.autoEligible, false, 'missing destination Risk Gate must block automatic action');
assert.strictEqual(r.evidence.tier, 'research', 'missing Risk Gate must not be promoted to acceptable manual evidence');
assert(r.warnings.includes('Risk Gate não classificado'));

r = evaluate({ mode: 'replace', ...base, destination: stock({ score_reliability: '' }) });
assert.strictEqual(r.autoEligible, false, 'missing Score Reliability must block automatic action');
assert.strictEqual(r.evidence.tier, 'research', 'missing Score Reliability must remain research-only');
assert(r.warnings.includes('fiabilidade do Score não classificada'));

r = evaluate({ mode: 'replace', ...base, destination: stock({ score_reliability: 'limited_evidence' }) });
assert.strictEqual(r.autoEligible, false, 'limited evidence must block automatic action');
assert(r.warnings.some(w => w.includes('fiabilidade')));

r = evaluate({ mode: 'replace', ...base, destination: stock({ data_coverage_pct: 60 }) });
assert.strictEqual(r.autoEligible, false, 'low fundamental coverage must block automatic action');
assert(r.warnings.includes('cobertura fundamental insuficiente'));

r = evaluate({ mode: 'replace', ...base, destination: stock({ critical_metric_coverage_pct: 45 }) });
assert.strictEqual(r.autoEligible, false, 'low critical coverage must block automatic action');
assert(r.warnings.includes('cobertura crítica insuficiente'));

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

r = evaluate({ mode: 'replace', ...base, sourceStock: sourceStock({ score_reliability: 'limited_evidence' }) });
assert.strictEqual(r.autoEligible, false, 'source with limited evidence must remain manual-only');
assert(r.warnings.includes('origem apenas para análise manual'));

r = evaluate({ mode: 'replace', ...base, sourceStock: sourceStock({ data_coverage_pct: 50 }) });
assert.strictEqual(r.autoEligible, false, 'source with low fundamental coverage must remain manual-only');

r = evaluate({ mode: 'replace', ...base, sourceStock: sourceStock({ critical_metric_coverage_pct: 40 }) });
assert.strictEqual(r.autoEligible, false, 'source with low critical coverage must remain manual-only');

r = evaluate({ mode: 'replace', ...base, sourceStock: sourceStock({ risk_gate: null }) });
assert.strictEqual(r.autoEligible, false, 'source with unclassified Risk Gate must remain manual-only');

r = evaluate({ mode: 'replace', ...base, sourceStock: sourceStock({ risk_gate: 'severe' }) });
assert.strictEqual(r.autoEligible, true, 'a severe source Risk Gate must not block replacement when source evidence itself is reliable');

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

r = evaluate({ mode: 'fresh', ...base, sourceStock: null, destinationConv: 70, indirect: 0.5, positionPct: 8, sectorPct: 20 });
assert.strictEqual(r.autoEligible, true, 'fresh capital should accept the canonical reinforce gate');

r = evaluate({ mode: 'fresh', ...base, sourceStock: null, destination: stock({ riskTags: [] }), destinationConv: 80, indirect: 0.5, positionPct: 8, sectorPct: 20 });
assert.strictEqual(r.autoEligible, false, 'missing factor classification must fail closed for automatic moves');
assert.strictEqual(r.riskBudgetReady, false, 'missing factor classification must be explicit in canonical decision output');
assert(r.warnings.includes('Risk Budget sem classificação de fatores'));

context.riskBudgetCoverage = () => ({ ready:false, researchCoverage:30, factorCoverage:20 });
r = evaluate({ mode: 'fresh', ...base, sourceStock: null, destinationConv: 80, indirect: 0.5, positionPct: 8, sectorPct: 20 });
assert.strictEqual(r.autoEligible, false, 'incomplete portfolio Risk Budget coverage must fail closed for automatic moves');
assert.strictEqual(r.riskBudgetReady, false);
assert(r.warnings.includes('Risk Budget da carteira com cobertura insuficiente'));
context.riskBudgetCoverage = () => ({ ready:true, researchCoverage:100, factorCoverage:100 });



r = evaluate({ mode: 'fresh', ...base, sourceStock: null, destinationConv: 69, indirect: 0.5, positionPct: 8, sectorPct: 20 });
assert.strictEqual(r.autoEligible, false, 'fresh capital must not allocate below canonical reinforce conviction');

r = evaluate({
  mode: 'fresh',
  ...base,
  sourceStock: null,
  destination: stock({ valuation_signal: 'uncertain', estimate_signal: 'deteriorating', thesis_direction: 'down' }),
  destinationConv: 75,
  indirect: 0.5,
  positionPct: 8,
  sectorPct: 20,
});
assert.strictEqual(r.autoEligible, true, 'valuation, estimates and thesis must affect auto-allocation only through canonical Conviction, not a second evidence gate');
assert.strictEqual(r.evidence.tier, 'preferred', 'strong evidence must stay preferred regardless of signals already owned by Conviction');
assert(!r.warnings.some(w => /valuation|expectativas|tese/.test(w)), 'evidence warnings must not duplicate Conviction inputs');

r = evaluate({ mode: 'fresh', ...base, sourceStock: null, indirect: 2.1, positionPct: 8, sectorPct: 20 });
assert.strictEqual(r.autoEligible, false, 'fresh capital must respect reduce-overlap target');
assert(r.warnings.includes('overlap elevado'));

console.log('portfolio decision engine deterministic contract: ok');
