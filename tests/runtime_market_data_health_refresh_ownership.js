const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'market-data-health.js'), 'utf8');

let host = null;
let style = null;
const view = {
  prepend(node) { host = node; },
};
const document = {
  readyState: 'loading',
  hidden: false,
  addEventListener() {},
  getElementById(id) {
    if (id === 'viewMarket') return view;
    if (id === 'vestraDataHealth') return host;
    if (id === 'vestra-data-health-style') return style;
    return null;
  },
  createElement(tag) {
    if (tag === 'details') return { dataset: {}, innerHTML: '', id: '', className: '' };
    return { id: '', rel: '', href: '' };
  },
  head: {
    appendChild(node) { style = node; },
  },
};

const window = {
  state: { settings: {} },
  addEventListener() {},
};

const pending = [];
function deferredFetch(url) {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  pending.push({ url, resolve });
  return promise;
}

const sandbox = {
  window,
  document,
  fetch: deferredFetch,
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

function responseFor(url) {
  const body = url.includes('coverage_guard')
    ? { generated_at: new Date().toISOString(), ok: true, violation_count: 0, rows_checked: 1700 }
    : { count: 7, source: 'test' };
  return { ok: true, json: async () => body };
}

async function main() {
  window.state.settings = {
    lastQuoteRefresh: { updated: 1, failed: 0, ts: new Date().toISOString() },
  };
  const older = api.refresh();
  assert.strictEqual(pending.length, 2, 'first refresh must start two reference-data requests');

  window.state.settings = {
    lastQuoteRefresh: { updated: 22, failed: 0, ts: new Date().toISOString() },
  };
  const newer = api.refresh();
  assert.strictEqual(pending.length, 4, 'second refresh must run independently');

  for (const request of pending.slice(2)) request.resolve(responseFor(request.url));
  await newer;
  assert(host, 'newer refresh should render the health panel');
  assert(host.innerHTML.includes('22 atualizadas'), 'newer quote snapshot should own the rendered panel');

  for (const request of pending.slice(0, 2)) request.resolve(responseFor(request.url));
  await older;
  assert(host.innerHTML.includes('22 atualizadas'), 'older completion must not overwrite the newer quote snapshot');
  assert(!host.innerHTML.includes('1 atualizadas'), 'stale refresh must never regress the visible quote state');

  console.log('market data health refresh ownership: ok');
}

main().catch(err => {
  console.error(err);
  process.exitCode = 1;
});
