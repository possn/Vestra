const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('sw.js', 'utf8');
const uiCoreMentions = source.match(/app-ui-core\.js/g) || [];
assert(uiCoreMentions.length >= 2, 'app-ui-core must remain in both APP_SHELL and BOOTSTRAP_NETWORK_FIRST');
assert(!source.includes('app-update-manager.js'), 'removed update manager must not remain in the service-worker dependency graph');
assert(source.includes('"market-opportunities.js"'), 'opportunity engine must be network-first');
assert(source.includes('"market-opportunity-lenses.js"'), 'opportunity lenses must be network-first with the engine');
assert(source.includes('await cache.put(request, fresh.clone())'), 'network-first must persist a healthy response before returning it');
assert(source.includes('cache.match(request, { ignoreSearch: true })'), 'versioned requests must be able to reuse unversioned app-shell entries');
assert(source.includes('const NETWORK_TIMEOUT_MS = 5000;'), 'service-worker network waits must be bounded');
assert(source.includes('async function fetchWithTimeout('), 'bounded fetch ownership must be centralized');
assert(source.includes('async function precacheAsset('), 'install precache must use the bounded fetch path');
assert(source.includes('APP_SHELL.map(asset => precacheAsset(cache, asset))'), 'every app-shell asset must use bounded precache');
assert(!source.includes('cache.add(asset)'), 'install must not use unbounded cache.add fetches');
assert(source.includes('controller.abort()'), 'timed-out fetches must abort when AbortController is available');
for (const dependency of ['app-runtime-bridge.js', 'quote-canonical-repair.js', 'market-global-search.js', 'market-learned-universe.js']) {
  assert(source.includes(`"./${dependency}"`), `${dependency} must be precached because market-company-brief loads it dynamically`);
}

function buildRuntime({ freshResponse, fetchError, cachedResponse, versionlessCachedResponse, hangFetch = false, immediateTimeout = false }) {
  const puts = [];
  const matches = [];
  const listeners = {};
  let fetchCalls = 0;
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
    AbortController: global.AbortController,
    setTimeout: immediateTimeout ? (fn => { fn(); return 1; }) : setTimeout,
    clearTimeout: immediateTimeout ? (() => {}) : clearTimeout,
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
      fetchCalls += 1;
      if (hangFetch) return await new Promise(() => {});
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
  return { context, cache, listeners, puts, matches, getFetchCalls: () => fetchCalls };
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
    const { context, cache, puts, getFetchCalls } = buildRuntime({ hangFetch: true, immediateTimeout: true });
    await assert.rejects(context.precacheAsset(cache, './app.js'), /Network timeout/, 'hung install precache must reject after its deadline');
    assert.strictEqual(getFetchCalls(), 1, 'bounded precache must issue only one network request');
    assert.strictEqual(puts.length, 0, 'timed-out precache must not write a partial response');
  }

  {
    const fresh = response(200, 'precache-fresh');
    const { context, cache, puts } = buildRuntime({ freshResponse: fresh });
    await context.precacheAsset(cache, './app.js');
    assert.strictEqual(puts.length, 1, 'healthy precache response must be persisted');
    assert.strictEqual(puts[0].request, './app.js', 'precache must store the requested shell asset key');
  }

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
    const cached = response(200, 'cached-after-timeout');
    const { context, getFetchCalls } = buildRuntime({ hangFetch: true, immediateTimeout: true, cachedResponse: cached });
    const result = await context.networkFirst({ url: '/app.js?v=slow-network' });
    assert.strictEqual(result, cached, 'hung network-first request must converge to cache after its deadline');
    assert.strictEqual(getFetchCalls(), 1, 'timeout fallback must not create duplicate network requests');
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
    const result = await context.staleWhileRevalidate({ url: '/styles.css?v=20260920v1' });
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
