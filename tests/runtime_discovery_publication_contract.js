const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const [full, compact, decoded] = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = {
  window: {},
  document: { readyState: 'loading', addEventListener() {} }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('market-opportunities.js', 'utf8'), context);
const api = context.window.VestraMarketOpportunities;
const inspect = row => JSON.stringify({
  eligible: api.eligible(row), score: api.discoveryScore(row),
  sleeves: api.sleeveScores(row), coverage: api.sleeveCoverage(row),
  leader: api.credibleDominantSleeve(row), caps: api.capSummary(row)
});
for (const rows of [compact, decoded]) {
  rows.forEach((row, i) => assert.equal(inspect(row), inspect(full[i])));
}
assert.equal(api.eligible(decoded[0]), false, 'explicit rejection overrides legacy threshold');
assert.equal(api.credibleDominantSleeve(decoded[0]), null, 'limited evidence cannot imply leadership');
assert.equal(api.eligible(decoded[1]), true);
assert.equal(api.credibleDominantSleeve(decoded[1]), 'asymmetry');
console.log('Discovery publication parity passed');
