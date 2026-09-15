const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('sw.js', 'utf8');
const updateManagerMentions = source.match(/app-update-manager\.js/g) || [];
assert(updateManagerMentions.length >= 2, 'safe update manager must be in both APP_SHELL and BOOTSTRAP_NETWORK_FIRST');
assert(source.includes('"market-opportunities.js"'), 'opportunity engine must be network-first');
assert(source.includes('"market-opportunity-lenses.js"'), 'opportunity lenses must be network-first with the engine');
assert(source.includes('await cache.put(request, fresh.clone())'), 'network-first must persist a healthy response before returning it');
assert(source.includes('cache.match(request, { ignoreSearch: true })'), 'versioned requests must be able to reuse unversioned app-shell entries');

function buildRuntime({ freshResponse, fetchError, cachedResponse, versionlessCachedResponse }) {
  const puts = [];
  const matches = [];
  const listeners = {};
  const cache = {
    add: async () => {},
    put: async (request, response) => { puts.push({ request, response }); },
    match: async (request, options = {}) => {
      matches.push({ request, options });
      if (options.ignoreSearch) return versionlessCachedResponse || cachedResponse || null;
      return cachedResponse || null;
    },
  };

  const context = {
    console,
    URL,
    Set,
    Promise,
    Response: global.Response || class Response {
      constructor(body, init = {}) { this.body = body; this.status = init.status || 200; this.ok = this.status >= 200 && this.status < 300; }
      clone() { return this; }
    },
    caches: {
      open: async () => cache,
      keys: async () => [],
      delete: async () => true,
    },
    fetch: async () => {
      if (fetchError) throw fetchError;
      return freshResponse;
    },
    self: {
      location: { origin: 'https://example.test' },
      skipWaiting() {},
      clients: { claim: async () => {} },
      addEventListener(type, handler) { listeners[type] = handler; },
    },
  };

  vm.createContext(context);
  vm.runInContext(source, context, { filename: 'sw.js' });
  return { context, puts, matches };
}

function response(status, label) {
  return {
    status,
    ok: status >= 200 && status < 300,
    label,
    clone() { return this; },
  };
}

(async () => {
  {
    const fresh = response(200, 'fresh');
    const cached = response(200, 'cached');
    const { context, puts } = buildRuntime({ freshResponse: fresh, cachedResponse: cached });
    const result = await context.networkFirst({ url: '/app.js' });
    assert.strictEqual(result, fresh, 'healthy network response must win');
    assert.strictEqual(puts.length, 1, 'healthy network response must refresh cache');
  }

  {
    const fresh = response(503, 'server-error');
    const cached = response(200, 'cached');
    const { context, puts } = buildRuntime({ freshResponse: fresh, cachedResponse: cached });
    const result = await context.networkFirst({ url: '/app.js' });
    assert.strictEqual(result, cached, 'non-2xx network response must fall back to cached copy');
    assert.strictEqual(puts.length, 0, 'non-2xx network response must not poison cache');
  }

  {
    const cached = response(200, 'cached');
    const { context } = buildRuntime({ fetchError: new Error('offline'), cachedResponse: cached });
    const result = await context.networkFirst({ url: '/app.js' });
    assert.strictEqual(result, cached, 'network exception must fall back to cached copy');
  }

  {
    const versionless = response(200, 'precache-app-js');
    const { context, matches } = buildRuntime({ fetchError: new Error('offline'), versionlessCachedResponse: versionless });
    const result = await context.networkFirst({ url: '/app.js?v=20260827v21' });
    assert.strictEqual(result, versionless, 'network-first must reuse the unversioned precache for a versioned offline request');
    assert(matches.some(entry => entry.options.ignoreSearch === true), 'network-first must retry cache lookup ignoring the version query');
  }

  {
    const versionless = response(200, 'precache-icon');
    const { context } = buildRuntime({ fetchError: new Error('offline'), versionlessCachedResponse: versionless });
    const result = await context.cacheFirst({ url: '/icon192.png?v=1' });
    assert.strictEqual(result, versionless, 'cache-first must reuse the unversioned precache for a versioned request');
  }

  {
    const versionless = response(200, 'precache-style');
    const { context } = buildRuntime({ fetchError: new Error('offline'), versionlessCachedResponse: versionless });
    const result = await context.staleWhileRevalidate({ url: '/styles.css?v=20260827v8' });
    assert.strictEqual(result, versionless, 'stale-while-revalidate must reuse the unversioned precache for a versioned offline request');
  }

  {
    const fresh = response(404, 'missing');
    const { context } = buildRuntime({ freshResponse: fresh, cachedResponse: null });
    const result = await context.networkFirst({ url: '/missing.js' });
    assert.strictEqual(result, fresh, 'without cache, preserve the original non-2xx response');
  }

  console.log('runtime_service_worker_contract: ok');
})().catch(error => {
  console.error(error);
  process.exit(1);
});