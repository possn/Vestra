'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('market-opportunities.js','utf8');
const start=source.indexOf('  function compareDiscoveryPriority(a,b){');
const end=source.indexOf('  function rankedCandidates(',start);
assert.ok(start>=0&&end>start,'canonical capped-score tiebreak is present');
const ctx={
  discoveryScore:s=>s.opportunity_score??null,
  n:v=>typeof v==='number'&&Number.isFinite(v)?v:null,
  t:v=>String(v??''),
};
vm.createContext(ctx);
vm.runInContext(source.slice(start,end),ctx);
const ordered=[
  {ticker:'LOW',opportunity_score:55,opportunity_score_raw:90},
  {ticker:'A',opportunity_score:59,opportunity_score_raw:62},
  {ticker:'B',opportunity_score:59,opportunity_score_raw:75},
  {ticker:'C',opportunity_score:59,opportunity_score_raw:68},
].sort(ctx.compareDiscoveryPriority);
assert.deepEqual(ordered.map(x=>x.ticker),['B','C','A','LOW'],
  'risk-adjusted rank remains primary; canonical raw breaks only cap ties');
const unknown=[{ticker:'Z',opportunity_score:59},{ticker:'A',opportunity_score:59}];
unknown.sort(ctx.compareDiscoveryPriority);
assert.deepEqual(unknown.map(x=>x.ticker),['A','Z'],
  'unavailable raw score must not be fabricated');
console.log('Market opportunity risk-cap tie-break passed');
