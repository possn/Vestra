#!/usr/bin/env node
// Functional migration checks against the actual app.js function, not a mock copy.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const src = fs.readFileSync('app.js', 'utf8');
const start = src.indexOf('function migrateLegacyTrading212Events(');
const end = src.indexOf('async function importBrokerFiles(', start);
assert(start >= 0 && end > start);
const brokerEventKey = e => e.extId ? e.broker + '|' + e.type + '|' + e.extId
  : [e.type, e.dateTime, e.ticker, e.totalEUR].join('|');
const migrate = vm.runInNewContext(src.slice(start, end) + '\n migrateLegacyTrading212Events;', {brokerEventKey});
const base = {broker:'Trading 212', type:'BUY', dateTime:'2025-01-02 10:00', ticker:'ABC', totalEUR:25};
const old = {...base, key:brokerEventKey(base)};
const incoming = {...base, extId:'official-1'};
const unrelated = {...base, dateTime:'2025-01-03'};
const xtb = {...base, broker:'XTB'};
const existing = {...base, extId:'official-2'};
const bd = {events:[old, unrelated, xtb, existing]};
assert.equal(migrate(bd, [incoming]), 1, 'replace exactly the matching legacy fingerprint');
assert.equal(bd.events.length, 3);
assert(bd.events.includes(unrelated) && bd.events.includes(xtb) && bd.events.includes(existing));
assert.equal(migrate(bd, [incoming]), 0, 'second import is idempotent');
assert.equal(migrate(bd, [{...base}]), 0, 'no-ID incoming row does not trigger legacy migration');
const bd2 = {events:[old]};
assert.equal(migrate(bd2, [{...incoming, broker:'XTB'}]), 0, 'XTB cannot migrate T212');
// Two broker-issued IDs can share the same economic fingerprint. The old
// fingerprint-only row must be removed without collapsing either official ID.
const twinA = {...incoming, extId:'official-twin-A'};
const twinB = {...incoming, extId:'official-twin-B'};
const twins = {events:[{...old}]};
assert.equal(migrate(twins, [twinA, twinB]), 1);
const keys = new Set(twins.events.map(brokerEventKey));
for (const e of [twinA, twinB]) {
  const key = brokerEventKey(e);
  if (!keys.has(key)) { twins.events.push(e); keys.add(key); }
}
assert.equal(twins.events.length, 2, 'both official transactions survive');
assert.equal(migrate(twins, [twinA, twinB]), 0, 'reimport keeps ID-bearing events');
assert.equal(new Set(twins.events.map(brokerEventKey)).size, 2);
console.log('Trading 212 legacy migration functional checks passed');
