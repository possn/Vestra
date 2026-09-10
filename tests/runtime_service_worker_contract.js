const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('sw.js', 'utf8');

function buildRuntime({ freshResponse, fetchError, cachedResponse }) {
  const puts = [];
  const listeners = {};
  const cache = {
    add: async () => {},
    put: async (request, response) => { puts.push({ request, response }); },
    match: async () => cachedResponse || null,
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
  return { context, puts };
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
