const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'market-data-health.js'), 'utf8');
const document = {
  readyState: 'loading',
  addEventListener() {},
  getElementById() { return null; },
  createElement() { return {}; },
  head: { appendChild() {} },
};
const window = {};
const sandbox = {
  window,
  document,
  fetch: async () => ({ ok: false }),
  Date,
  Intl,
  Number,
  String,
  Math,
  JSON,
  Object,
  Promise,
  console,
};

vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: 'market-data-health.js' });

const api = window.VestraMarketDataHealth;
assert(api, 'VestraMarketDataHealth was not exported');
assert.strictEqual(api.version, '1.1');

const now = new Date('2026-08-31T18:30:00Z');
const fresh = api.model({ generated_at: '2026-08-31T17:30:00Z', ok: true, violation_count: 0, rows_checked: 1699 }, { count: 5, source: 'snapshot+worker' }, now);
assert.strictEqual(fresh.state.key, 'ok');
assert.strictEqual(fresh.state.label, 'Dados atualizados');
assert.strictEqual(fresh.rows, 1699);
assert.strictEqual(fresh.learnedCount, 5);
assert.strictEqual(fresh.learnedSource, 'snapshot+worker');
assert.strictEqual(fresh.age, 'há 1 h');

const stale = api.model({ generated_at: '2026-08-31T12:00:00Z', ok: true, violation_count: 0, rows_checked: 1699 }, { rows: [] }, now);
assert.strictEqual(stale.state.key, 'stale');
assert.strictEqual(stale.state.label, 'Dados antigos');

const bad = api.model({ generated_at: '2026-08-31T18:20:00Z', ok: false, violation_count: 2 }, { count: 5 }, now);
assert.strictEqual(bad.state.key, 'bad');
assert.strictEqual(bad.state.label, 'Atenção aos dados');

const unknown = api.model(null, null, now);
assert.strictEqual(unknown.state.key, 'unknown');
assert.strictEqual(unknown.state.label, 'Estado dos dados indisponível');
assert.strictEqual(unknown.age, 'idade desconhecida');
assert(!source.includes('Dados · ${data.state.label}'), 'summary must not duplicate the word Dados');

console.log('market data health contract: ok');
