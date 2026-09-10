const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'market-data-health.js'), 'utf8');
const document = {
  readyState: 'loading',
  hidden: false,
  addEventListener() {},
  getElementById() { return null; },
  createElement() { return {}; },
  head: { appendChild() {} },
};
const window = { addEventListener() {} };
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
assert.strictEqual(api.version, '1.2');
assert.strictEqual(api.quoteStaleMs, 60 * 1000);

const now = new Date('2026-08-31T18:30:00Z');
const guard = { generated_at: '2026-08-31T17:30:00Z', ok: true, violation_count: 0, rows_checked: 1699 };
const learned = { count: 5, source: 'snapshot+worker' };

const fresh = api.model(
  guard,
  learned,
  now,
  { updated: 12, failed: 0, ts: '2026-08-31T18:29:40Z', durationMs: 1200 },
  Date.parse('2026-08-31T18:29:40Z')
);
assert.strictEqual(fresh.state.key, 'ok');
assert.strictEqual(fresh.state.label, 'Dados de referência atualizados');
assert.strictEqual(fresh.quoteState.key, 'ok');
assert.strictEqual(fresh.quoteState.label, 'Cotações atualizadas');
assert.strictEqual(fresh.overallState.key, 'ok');
assert.strictEqual(fresh.overallState.label, 'Mercado atualizado');
assert.strictEqual(fresh.quoteAge, 'agora');
assert.strictEqual(fresh.quoteUpdated, 12);
assert.strictEqual(fresh.quoteFailed, 0);
assert.strictEqual(fresh.quoteDurationMs, 1200);
assert.strictEqual(fresh.rows, 1699);
assert.strictEqual(fresh.learnedCount, 5);
assert.strictEqual(fresh.learnedSource, 'snapshot+worker');
assert.strictEqual(fresh.age, 'há 1 h');

const staleQuote = api.model(
  guard,
  learned,
  now,
  { updated: 12, failed: 0, ts: '2026-08-31T18:28:00Z' },
  Date.parse('2026-08-31T18:28:00Z')
);
assert.strictEqual(staleQuote.quoteState.key, 'stale');
assert.strictEqual(staleQuote.quoteState.label, 'Cotações a atualizar');
assert.strictEqual(staleQuote.overallState.key, 'stale');
assert.strictEqual(staleQuote.overallState.label, 'Atualização pendente');

const partialQuote = api.model(
  guard,
  learned,
  now,
  { updated: 10, failed: 2, ts: '2026-08-31T18:29:50Z' },
  Date.parse('2026-08-31T18:29:50Z')
);
assert.strictEqual(partialQuote.quoteState.key, 'partial');
assert.strictEqual(partialQuote.quoteState.label, 'Cotações parciais');
assert.strictEqual(partialQuote.overallState.key, 'stale');
assert.strictEqual(partialQuote.overallState.label, 'Cotações parcialmente atualizadas');

const badQuote = api.model(
  guard,
  learned,
  now,
  { updated: 0, failed: 2, ts: '2026-08-31T18:29:50Z' },
  Date.parse('2026-08-31T18:29:50Z')
);
assert.strictEqual(badQuote.quoteState.key, 'bad');
assert.strictEqual(badQuote.overallState.key, 'bad');
assert.strictEqual(badQuote.overallState.label, 'Atenção ao mercado');

const noQuote = api.model(guard, learned, now);
assert.strictEqual(noQuote.quoteState.key, 'unknown');
assert.strictEqual(noQuote.quoteState.label, 'Cotações ainda não atualizadas');
assert.strictEqual(noQuote.overallState.key, 'ok');
assert.strictEqual(noQuote.overallState.label, 'Dados de referência atualizados');

const staleReference = api.model({ generated_at: '2026-08-31T12:00:00Z', ok: true, violation_count: 0, rows_checked: 1699 }, { rows: [] }, now);
assert.strictEqual(staleReference.state.key, 'stale');
assert.strictEqual(staleReference.state.label, 'Dados de referência antigos');

const badReference = api.model({ generated_at: '2026-08-31T18:20:00Z', ok: false, violation_count: 2 }, { count: 5 }, now);
assert.strictEqual(badReference.state.key, 'bad');
assert.strictEqual(badReference.state.label, 'Atenção aos dados');

const unknown = api.model(null, null, now);
assert.strictEqual(unknown.state.key, 'unknown');
assert.strictEqual(unknown.overallState.key, 'unknown');
assert.strictEqual(unknown.age, 'idade desconhecida');

assert(source.includes("document.addEventListener('quotesUpdated', refresh)"), 'health UI must react immediately after a quote refresh');
assert(source.includes('lastQuoteRefreshTs'), 'health UI must use the persisted quote timestamp');
assert(source.includes('window.VestraStorage'), 'health UI must recover freshness after reload from persisted state');
assert(!source.includes('Dados · ${data.state.label}'), 'summary must not duplicate the word Dados');

console.log('market data health contract: ok');
