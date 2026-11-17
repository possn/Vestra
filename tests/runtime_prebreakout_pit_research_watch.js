// Run with: node tests/runtime_prebreakout_pit_research_watch.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('market-opportunities.js', 'utf8');
const document = {readyState: 'loading', addEventListener() {}};
const window = {};
vm.runInNewContext(source, {document, window, console, Date});
const getRows = window.VestraMarketOpportunities.researchWatchRows;
const observed = {
  ticker: 'TEST', evaluable: true, last_session: new Date().toISOString().slice(0, 10),
  adjusted_close: 12.5, first_rejection: 'sequential_vcp_contractions',
  geometry_shadow: {research_only_not_eligibility: true,
    base_width_pass: true, contractions_pass: false, base_width_pct: 15},
  ma_failed_checks: []
};
const feed = rows => ({research_observations: {
  point_in_time_capture_not_historical_reconstruction: true, rows
}});
assert.equal(getRows(feed([observed])).length, 1);
assert.equal(getRows(feed([{...observed, evaluable: false}])).length, 0);
assert.equal(getRows(feed([{...observed, adjusted_close: null}])).length, 0);
assert.equal(getRows(feed([{...observed, geometry_shadow: {
  ...observed.geometry_shadow, base_width_pass: false}}])).length, 0);
assert.equal(getRows(feed([{...observed, first_rejection: 'passed_structural_gates'}])).length, 0);
assert.equal(getRows({research_observations: {rows: [observed]}}).length, 0);
assert.equal(getRows(feed([{...observed, last_session: '2020-01-01'}])).length, 0);
console.log('PIT pre-breakout watch: verified current partial geometry only');
