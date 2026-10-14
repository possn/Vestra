const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('market-opportunities.js','utf8');
const start=source.indexOf('  function credibleDominantSleeve(s){');
const end=source.indexOf('  function discoveryCaps(s){',start);
assert(start>=0&&end>start,'canonical sleeve selector missing');
const context={
 dominantSleeve:s=>s.leader||null,
 sleeveCoverage:s=>s.opportunity_sleeve_coverage_pct||{}
};
vm.createContext(context);
vm.runInContext(source.slice(start,end),context);
const pick=context.credibleDominantSleeve;
assert.equal(pick({leader:'strength',opportunity_sleeves:{strength:92}}),null,'missing published coverage cannot imply credibility');
assert.equal(pick({leader:'strength',opportunity_sleeves:{strength:92},opportunity_sleeve_coverage_pct:{strength:40}}),null);
assert.equal(pick({leader:'strength',opportunity_sleeves:{strength:92},opportunity_sleeve_coverage_pct:{strength:70}}),'strength');
assert.equal(pick({leader:'strength',opportunity_sleeves:{strength:92},opportunity_sleeve_coverage_pct:{strength:95}}),'strength');
assert.equal(pick({leader:'strength'}),'strength','legacy fallback remains unchanged');
console.log('Opportunity sleeve evidence coverage contract passed');
