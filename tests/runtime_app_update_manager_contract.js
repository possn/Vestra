const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('app-update-manager.js', 'utf8');

assert(source.includes("version: '1.4'"), 'safe update manager version must be 1.4');
assert(source.includes('getRegistration()'), 'safe update path must update the existing service worker registration');
assert(!source.includes('getRegistrations()'), 'safe update path must not enumerate registrations for removal');
assert(!source.includes('.unregister('), 'safe update path must never unregister service workers');
assert(!source.includes('caches.delete'), 'safe update path must never delete application caches');
assert(source.includes("addEventListener('DOMContentLoaded', reclaimAfterAppSetup"), 'manager must reclaim ownership after DOM setup');
assert(source.includes("addEventListener('vestra:app-ready', reclaimAfterAppSetup"), 'manager must reclaim ownership after the app-ready lifecycle');
assert(source.includes("document.addEventListener('click'"), 'manager must install a document-level click guard');
assert(source.includes("}, true);"), 'update click guard must run in capture phase');
assert(source.includes('stopImmediatePropagation()'), 'capture guard must block legacy target listeners');

function makeButton(owner = false) {
  const listeners = [];
  const button = {
    id: 'btnForceUpdate',
    dataset: owner ? { vestraSafeUpdateOwner: '1' } : {},
    listeners,
    cloneNode() { return makeButton(owner); },
    addEventListener(type, handler) { listeners.push({ type, handler }); },
    replaceWith(next) { runtime.currentButton = next; },
    closest(selector) { return selector === '#btnForceUpdate' ? this : null; },
  };
  return button;
}

const runtime = {
  currentButton: makeButton(false),
  timers: [],
  registrationChecks: 0,
  registrationsEnumerated: 0,
  cacheDeletes: 0,
  replacedUrl: '',
};
const windowListeners = [];
const documentListeners = [];
const context = {
  console,
  URL,
  Date,
  confirm: () => true,
  setTimeout(fn) { runtime.timers.push(fn); return runtime.timers.length; },
  caches: {
    async delete() { runtime.cacheDeletes += 1; throw new Error('safe update must not delete caches'); },
  },
  navigator: {
    serviceWorker: {
      async getRegistration() {
        runtime.registrationChecks += 1;
        return { update: async () => {} };
      },
      async getRegistrations() {
        runtime.registrationsEnumerated += 1;
        throw new Error('safe update must not enumerate registrations');
      },
    },
  },
  document: {
    readyState: 'loading',
    getElementById(id) { return id === 'btnForceUpdate' ? runtime.currentButton : null; },
    addEventListener(type, handler, options) { documentListeners.push({ type, handler, options }); },
  },
  window: {
    location: {
      href: 'https://example.test/Vestra/',
      replace(url) { runtime.replacedUrl = url; },
    },
    addEventListener(type, handler, options) { windowListeners.push({ type, handler, options }); },
  },
};
context.window.window = context.window;
vm.createContext(context);
vm.runInContext(source, context, { filename: 'app-update-manager.js' });

assert.strictEqual(runtime.currentButton.dataset.vestraSafeUpdateOwner, '1', 'initial install must own update button');
assert(documentListeners.some(x => x.type === 'DOMContentLoaded'), 'DOMContentLoaded reclaim must be registered');
assert(windowListeners.some(x => x.type === 'vestra:app-ready'), 'app-ready reclaim must be registered');

const guard = documentListeners.find(x => x.type === 'click');
assert(guard, 'capture click guard must be registered');
assert.strictEqual(guard.options, true, 'capture click guard must use capture phase');

const firstOwned = runtime.currentButton;
let legacyRan = false;
firstOwned.addEventListener('click', () => { legacyRan = true; });

// Simulate DOM event order: document capture first, then target only if the
// capture guard did not stop propagation. This mirrors the historical app.js
// listener being attached after the safe manager.
const event = {
  target: firstOwned,
  defaultPrevented: false,
  stopped: false,
  preventDefault() { this.defaultPrevented = true; },
  stopImmediatePropagation() { this.stopped = true; },
};
guard.handler(event);
if (!event.stopped) {
  firstOwned.listeners.filter(x => x.type === 'click').forEach(x => x.handler(event));
}

assert.strictEqual(event.defaultPrevented, true, 'safe guard must prevent the legacy button action');
assert.strictEqual(event.stopped, true, 'safe guard must stop propagation before target listeners');
assert.strictEqual(legacyRan, false, 'legacy destructive target listener must be unreachable');
assert.strictEqual(runtime.registrationChecks, 1, 'safe click must check only the existing registration');
assert.strictEqual(runtime.registrationsEnumerated, 0, 'safe click must never enumerate registrations');
assert.strictEqual(runtime.cacheDeletes, 0, 'safe click must never delete caches');

// DOMContentLoaded reclaim must still replace a node contaminated by a late
// target listener, providing a second independent containment layer.
documentListeners.find(x => x.type === 'DOMContentLoaded').handler();
while (runtime.timers.length) runtime.timers.shift()();
assert.notStrictEqual(runtime.currentButton, firstOwned, 'post-setup reclaim must replace the contaminated node');
assert.strictEqual(runtime.currentButton.dataset.vestraSafeUpdateOwner, '1', 'reclaimed button must remain safe-owned');
assert(runtime.replacedUrl.includes('_v='), 'safe update must finish with a cache-busted navigation');

console.log('runtime_app_update_manager_contract: ok');
