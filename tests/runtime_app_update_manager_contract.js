const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('app-update-manager.js', 'utf8');

assert(source.includes("version: '1.3'"), 'safe update manager version must be 1.3');
assert(source.includes('getRegistration()'), 'safe update path must update the existing service worker registration');
assert(!source.includes('getRegistrations()'), 'safe update path must not enumerate registrations for removal');
assert(!source.includes('.unregister('), 'safe update path must never unregister service workers');
assert(!source.includes('caches.delete'), 'safe update path must never delete application caches');
assert(source.includes("addEventListener('DOMContentLoaded', reclaimAfterAppSetup"), 'manager must reclaim ownership after DOM setup');
assert(source.includes("addEventListener('vestra:app-ready', reclaimAfterAppSetup"), 'manager must reclaim ownership after the app-ready lifecycle');
assert(source.includes('stopImmediatePropagation()'), 'owned button must block later legacy target listeners');

function makeButton(owner = false) {
  const listeners = [];
  const button = {
    dataset: owner ? { vestraSafeUpdateOwner: '1' } : {},
    listeners,
    cloneNode() { return makeButton(owner); },
    addEventListener(type, handler) { listeners.push({ type, handler }); },
    replaceWith(next) { runtime.currentButton = next; },
  };
  return button;
}

const runtime = { currentButton: makeButton(false), timers: [] };
const windowListeners = [];
const documentListeners = [];
const context = {
  console,
  URL,
  Date,
  confirm: () => false,
  setTimeout(fn) { runtime.timers.push(fn); return runtime.timers.length; },
  navigator: { serviceWorker: { getRegistration: async () => null } },
  document: {
    readyState: 'loading',
    getElementById(id) { return id === 'btnForceUpdate' ? runtime.currentButton : null; },
    addEventListener(type, handler, options) { documentListeners.push({ type, handler, options }); },
  },
  window: {
    location: { href: 'https://example.test/Vestra/', replace() {} },
    addEventListener(type, handler, options) { windowListeners.push({ type, handler, options }); },
  },
};
context.window.window = context.window;
vm.createContext(context);
vm.runInContext(source, context, { filename: 'app-update-manager.js' });

assert.strictEqual(runtime.currentButton.dataset.vestraSafeUpdateOwner, '1', 'initial install must own update button');
assert.strictEqual(runtime.currentButton.listeners.filter(x => x.type === 'click').length, 1, 'owned button must expose one safe click listener');
assert(documentListeners.some(x => x.type === 'DOMContentLoaded'), 'DOMContentLoaded reclaim must be registered');
assert(windowListeners.some(x => x.type === 'vestra:app-ready'), 'app-ready reclaim must be registered');

const firstOwned = runtime.currentButton;
// Simulate app.js attaching its legacy listener after the manager loaded early.
firstOwned.addEventListener('click', () => { throw new Error('legacy listener must be removed by reclaim'); });
assert.strictEqual(firstOwned.listeners.filter(x => x.type === 'click').length, 2, 'fixture should contain the late legacy listener');

documentListeners.find(x => x.type === 'DOMContentLoaded').handler();
while (runtime.timers.length) runtime.timers.shift()();
assert.notStrictEqual(runtime.currentButton, firstOwned, 'post-setup reclaim must replace the contaminated node');
assert.strictEqual(runtime.currentButton.listeners.filter(x => x.type === 'click').length, 1, 'reclaimed button must keep only the safe listener');

console.log('runtime_app_update_manager_contract: ok');
