const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('app-ui-core.js', 'utf8');
const indexSource = fs.readFileSync('index.html', 'utf8');
const swSource = fs.readFileSync('sw.js', 'utf8');

assert(source.includes('function installSafeUpdateGuard()'), 'app-ui-core must own the safe update guard');
assert(source.includes('function forceFreshReload()'), 'app-ui-core must own the safe update navigation');
assert(source.includes("button.addEventListener('click'"), 'safe update guard must be scoped to the update button');
assert(source.includes('stopImmediatePropagation()'), 'capture guard must block the legacy destructive target handler');
assert(!source.includes('getRegistrations()'), 'safe update path must not enumerate registrations for removal');
assert(!source.includes('.unregister('), 'safe update path must never unregister service workers');
assert(!source.includes('caches.delete'), 'safe update path must never delete application caches');

const uiCorePos = indexSource.indexOf('src="app-ui-core.js');
const appPos = indexSource.indexOf('src="app.js');
assert(uiCorePos >= 0, 'index must load app-ui-core');
assert(appPos >= 0, 'index must load app.js');
assert(uiCorePos < appPos, 'app-ui-core must load before app.js so the capture guard wins');
assert(indexSource.includes('navigator.serviceWorker.getRegistration().then(reg => { if (reg) reg.update(); });'), 'index bootstrap must remain the canonical update checker');
assert(indexSource.includes("navigator.serviceWorker.addEventListener('controllerchange'"), 'index bootstrap must remain the canonical controllerchange owner');
assert(indexSource.includes("window.__vestraServiceWorkerUpdated = true"), 'controllerchange must record the worker takeover');
assert(indexSource.includes("vestra:service-worker-updated"), 'controllerchange must publish the worker update event');
assert(!indexSource.includes("window.__vestraSwReloadScheduled"), 'worker takeover must not schedule a hidden hard reload');
assert(!indexSource.includes("window.location.replace(url.toString())"), 'worker takeover must not restart an active session');
assert(!indexSource.includes('app-update-manager.js'), 'orphaned update manager must not be loaded by index');
assert(!swSource.includes('app-update-manager.js'), 'orphaned update manager must not remain in the service-worker shell');

const runtime = {
  timers: [],
  replacedUrl: '',
};
const documentListeners = [];
const buttonListeners = [];
const windowListeners = [];

const context = {
  console,
  URL,
  Date,
  confirm: () => true,
  performance: { now: () => 0 },
  setTimeout(fn) { runtime.timers.push(fn); return runtime.timers.length; },
  clearTimeout() {},
  requestAnimationFrame(fn) { fn(); return 1; },
  document: {
    visibilityState: 'visible',
    getElementById(id) {
      if (id !== 'btnForceUpdate') return null;
      return {
        id: 'btnForceUpdate',
        closest(selector) { return selector === '#btnForceUpdate' ? this : null; },
        addEventListener(type, handler, options) { buttonListeners.push({ type, handler, options }); },
      };
    },
    querySelectorAll() { return []; },
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
vm.runInContext(source, context, { filename: 'app-ui-core.js' });

const guards = buttonListeners.filter(x => x.type === 'click');
assert.strictEqual(guards.length, 1, 'safe update button guard must be installed exactly once');
assert.strictEqual(guards[0].options, true, 'safe update guard must run in capture phase on its target');

let legacyRan = false;
const button = context.document.getElementById('btnForceUpdate');
const event = {
  target: button,
  defaultPrevented: false,
  stopped: false,
  preventDefault() { this.defaultPrevented = true; },
  stopImmediatePropagation() { this.stopped = true; },
};

guards[0].handler(event);
if (!event.stopped) legacyRan = true;

assert.strictEqual(event.defaultPrevented, true, 'safe guard must prevent the legacy button action');
assert.strictEqual(event.stopped, true, 'safe guard must stop propagation before target listeners');
assert.strictEqual(legacyRan, false, 'legacy destructive target listener must be unreachable');
assert(runtime.timers.length > 0, 'safe update must schedule cache-busted navigation');
runtime.timers.shift()();
assert(runtime.replacedUrl.includes('_v='), 'safe update must finish with a cache-busted navigation');

const before = buttonListeners.length;
context.window.VestraUiCore.installSafeUpdateGuard();
assert.strictEqual(buttonListeners.length, before, 'safe update guard installation must be idempotent');

console.log('runtime_app_update_manager_contract: ok');
