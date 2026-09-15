const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('sw.js', 'utf8');

assert(source.includes('const NETWORK_TIMEOUT_MS = 5000;'), 'service worker must expose a bounded network deadline');
assert(source.includes('async function fetchWithTimeout('), 'service worker must centralize bounded fetches');
assert(source.includes('controller.abort()'), 'bounded fetch must abort the underlying request when possible');
assert(source.includes('fetchWithTimeout(request, { cache: "no-store" })'), 'network-first and revalidation paths must use bounded fetches');

const listeners = {};
const cached = { ok: true, status: 200, label: 'cached', clone() { return this; } };
const cache = {
  add: async () => {},
  put: async () => {},
  match: async () => cached,
};
let abortObserved = false;

class FakeAbortController {
  constructor() {
    const listeners = [];
    this.signal = {
      addEventListener(type, handler) {
        if (type === 'abort') listeners.push(handler);
      },
    };
    this._listeners = listeners;
  }
  abort() {
    abortObserved = true;
    for (const handler of this._listeners) handler();
  }
}

const context = {
  console,
  URL,
  Set,
  Promise,
  AbortController: FakeAbortController,
  Response: global.Response || class Response {
    constructor(body, init = {}) { this.body = body; this.status = init.status || 200; this.ok = this.status >= 200 && this.status < 300; }
    clone() { return this; }
  },
  caches: {
    open: async () => cache,
    keys: async () => [],
    delete: async () => true,
  },
  fetch: (_request, options = {}) => new Promise((resolve, reject) => {
    options.signal?.addEventListener?.('abort', () => {
      const error = new Error('aborted');
      error.name = 'AbortError';
      reject(error);
    });
  }),
  setTimeout(fn) { fn(); return 1; },
  clearTimeout() {},
  self: {
    location: { origin: 'https://example.test' },
    skipWaiting() {},
    clients: { claim: async () => {} },
    addEventListener(type, handler) { listeners[type] = handler; },
  },
};

vm.createContext(context);
vm.runInContext(source, context, { filename: 'sw.js' });

(async () => {
  const request = { url: 'https://example.test/app.js?v=1' };
  const result = await context.networkFirst(request);
  assert.strictEqual(result, cached, 'timed-out network-first request must fall back to cache');
  assert.strictEqual(abortObserved, true, 'timed-out request must abort the underlying fetch');
  console.log('runtime_service_worker_timeout_contract: ok');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
