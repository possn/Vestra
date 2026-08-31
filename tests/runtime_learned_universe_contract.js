const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'market-global-search.js'), 'utf8');
const calls = [];

const document = {
  addEventListener() {},
  getElementById() { return null; },
  querySelector() { return null; },
  createElement() { return { id: '', textContent: '' }; },
  head: { appendChild() {} },
  documentElement: { classList: { add() {} } },
  body: { classList: { add() {} } },
};

const window = {
  state: { settings: { workerUrl: 'https://worker.example.test/' } },
  VestraLearnedUniverse: null,
};

async function fetchStub(url, options = {}) {
  calls.push({ url: String(url), options });
  return { ok: true, status: 200, async json() { return {}; } };
}

const sandbox = {
  window,
  document,
  fetch: fetchStub,
  Intl,
  Map,
  Set,
  String,
  Number,
  JSON,
  Math,
  Error,
  encodeURIComponent,
  setTimeout,
  clearTimeout,
  console,
};

vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: 'market-global-search.js' });

(async () => {
  const api = window.VestraGlobalMarketSearch;
  assert(api, 'VestraGlobalMarketSearch was not exported');

  const sent = await api.learnCentral({ ticker: ' zzpst ' });
  assert.strictEqual(sent, true, 'first valid learned ticker must be posted');
  assert.strictEqual(calls.length, 1, 'exactly one POST should be emitted');

  const call = calls[0];
  assert.strictEqual(call.url, 'https://worker.example.test/learned-universe');
  assert.strictEqual(call.options.method, 'POST');
  assert.strictEqual(call.options.cache, 'no-store');
  assert.strictEqual(call.options.headers['Content-Type'], 'application/json');
  assert.strictEqual(JSON.parse(call.options.body).ticker, 'ZZPST');

  const duplicate = await api.learnCentral({ ticker: 'ZZPST' });
  assert.strictEqual(duplicate, false, 'duplicate ticker must not be posted twice in one session');
  assert.strictEqual(calls.length, 1, 'dedupe must suppress a second POST');

  const invalid = await api.learnCentral({ ticker: 'bad ticker!' });
  assert.strictEqual(invalid, false, 'invalid ticker must not be posted');
  assert.strictEqual(calls.length, 1, 'invalid ticker must not reach fetch');

  console.log('learned-universe central POST contract: ok');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
