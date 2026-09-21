const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('market-global-search.js', 'utf8');
const listeners = {};
const document = {
  addEventListener(type, handler) { listeners[type] = handler; },
  getElementById() { return null; },
  querySelector() { return null; },
  createElement() { return { dataset: {} }; },
  head: { appendChild() {} },
};
const context = vm.createContext({
  console,
  document,
  window: { state: { settings: { workerUrl: 'https://example.test' } } },
  setTimeout,
  clearTimeout,
  AbortController,
  fetch: async () => { throw new Error('network is not used by alias contract'); },
});

vm.runInContext(source, context, { filename: 'market-global-search.js' });
const api = context.window.VestraGlobalMarketSearch;
assert.ok(api, 'global market search API must be exported');
assert.strictEqual(api.version, '2.1');

for (const query of ['HHPD', 'HHPD.IL', 'Hon Hai', 'Foxconn']) {
  const rows = api.brokerAliasSearch(query);
  assert.strictEqual(rows.length, 1, `${query} must resolve one broker alias`);
  assert.strictEqual(rows[0].ticker, 'HHPD.IL');
  assert.strictEqual(rows[0].provider_symbol, 'HHPD.IL');
  assert.strictEqual(rows[0].identity_verified, false, 'suggestions must not bypass live identity validation');
}

assert.strictEqual(api.brokerAliasSearch('unrelated company').length, 0);
assert.strictEqual(api.exactProviderIdentity('HHPD.IL', {
  ticker: 'HHPD.IL', provider_symbol: 'HHPD.IL', retrieval_ticker: 'HHPD.IL',
}), true);
assert.strictEqual(api.exactProviderIdentity('HHPD.IL', {
  ticker: 'HHPD.IL', provider_symbol: 'HHPD', retrieval_ticker: 'HHPD.IL',
}), false, 'broker alias must never weaken exact provider identity');

console.log('runtime global market search contract: ok');
