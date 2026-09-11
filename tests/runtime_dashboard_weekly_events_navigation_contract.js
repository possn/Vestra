const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('dashboard-weekly-events-navigation.js', 'utf8');
const renders = [];
const listeners = {};
const head = { querySelector: () => null, appendChild: () => {} };
const card = { querySelector: selector => selector === '.weekly-events-head' ? head : null };
const document = {
  readyState: 'loading', documentElement: {},
  getElementById: id => id === 'dashboardWeeklyEventsCard' ? card : null,
  createElement: tag => ({ tagName: tag.toUpperCase(), dataset:{}, style:{}, classList:{add:()=>{}}, setAttribute:()=>{}, append:()=>{}, appendChild:()=>{} }),
  addEventListener: (name, fn) => { listeners[name] = fn; },
};
const windowObj = {
  VestraWeeklyEvents: { render: options => { renders.push(options.now); return []; } },
  addEventListener: () => {},
};
class MutationObserver { constructor(fn){ this.fn=fn; } observe(){} disconnect(){} }
const context = { window:windowObj, document, console, Date, MutationObserver, setTimeout: fn => { fn(); return 0; } };
vm.createContext(context);
vm.runInContext(source, context);
const api = windowObj.VestraWeeklyEventsNavigation;
assert(api, 'navigation API is exposed');
assert.strictEqual(api.maxWeekOffset, 52);
const base = new Date(2026, 8, 11, 9, 0, 0);
const prior = api.shiftedDate(base, -1);
assert.strictEqual(prior.getDate(), 4);
api.move(-1, base);
assert.strictEqual(api.getWeekOffset(), -1);
assert.strictEqual(renders.at(-1).getDate(), 4);
api.move(1, base);
assert.strictEqual(api.getWeekOffset(), 0);
api.move(999, base);
assert.strictEqual(api.getWeekOffset(), 52, 'navigation clamps to 52 weeks forward');
api.reset(base);
assert.strictEqual(api.getWeekOffset(), 0);
assert(source.includes("data-weekly-week-action") || source.includes('weeklyWeekAction'), 'navigation has explicit week controls');
console.log('weekly events navigation runtime contract: ok');
