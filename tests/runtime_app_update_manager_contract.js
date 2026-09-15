const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('app-update-manager.js', 'utf8');
const indexSource = fs.readFileSync('index.html', 'utf8');

assert(source.includes("version: '1.6'"), 'safe update manager version must be 1.6');
assert(!source.includes('serviceWorker'), 'safe update manager must not own the service-worker lifecycle');
assert(!source.includes('getRegistration()'), 'safe update manager must not trigger a parallel registration update');
assert(!source.includes('getRegistrations()'), 'safe update path must not enumerate registrations for removal');
assert(!source.includes('.unregister('), 'safe update path must never unregister service workers');
assert(!source.includes('caches.delete'), 'safe update path must never delete application caches');
assert(source.includes("addEventListener('DOMContentLoaded', reclaimAfterAppSetup"), 'manager must retry ownership after DOM setup');
assert(source.includes("addEventListener('vestra:app-ready', reclaimAfterAppSetup"), 'manager must retry ownership after the app-ready lifecycle');
assert(source.includes("document.addEventListener('click'"), 'manager must install a document-level click guard');
assert(source.includes("}, true);"), 'update click guard must run in capture phase');
assert(source.includes('stopImmediatePropagation()'), 'capture guard must block legacy target listeners');
assert(!source.includes('install(true)'), 'owned update button must never be force-replaced on lifecycle retries');
assert(!source.includes('}, 40);'), 'safe update navigation must not be deferred outside the user gesture');
assert(indexSource.includes('navigator.serviceWorker.getRegistration().then(reg => { if (reg) reg.update(); });'), 'index bootstrap must remain the canonical update checker');
assert(indexSource.includes("navigator.serviceWorker.addEventListener('controllerchange'"), 'index bootstrap must remain the canonical controllerchange owner');

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
  navigator: {},
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
assert(documentListeners.some(x => x.type === 'DOMContentLoaded'), 'DOMContentLoaded ownership retry must be registered');
assert(windowListeners.some(x => x.type === 'vestra:app-ready'), 'app-ready ownership retry must be registered');

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
assert(runtime.replacedUrl.includes('_v='), 'safe update must navigate synchronously with a cache-busted URL');

// Lifecycle retries must be idempotent once ownership is established. The
// capture guard already contains any late target listener, so replacing the
// button again would only discard legitimate state/listeners.
documentListeners.find(x => x.type === 'DOMContentLoaded').handler();
while (runtime.timers.length) runtime.timers.shift()();
assert.strictEqual(runtime.currentButton, firstOwned, 'DOMContentLoaded retry must preserve an already-owned button');
assert.strictEqual(runtime.currentButton.dataset.vestraSafeUpdateOwner, '1', 'owned button must remain safe-owned');

windowListeners.find(x => x.type === 'vestra:app-ready').handler();
while (runtime.timers.length) runtime.timers.shift()();
assert.strictEqual(runtime.currentButton, firstOwned, 'app-ready retry must preserve an already-owned button');
assert.strictEqual(firstOwned.listeners.length, 1, 'late target listener state must not be discarded by forced cloning');

console.log('runtime_app_update_manager_contract: ok');
