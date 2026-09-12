const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('dashboard-weekly-events-navigation.js', 'utf8');
const styles = fs.readFileSync('dashboard-weekly-events.css', 'utf8');
const renders = [];
const head = { querySelector: () => null, appendChild: () => {} };
const card = { querySelector: selector => selector === '.weekly-events-head' ? head : null };
const document = {
  readyState: 'loading', documentElement: {},
  getElementById: id => id === 'dashboardWeeklyEventsCard' ? card : null,
  createElement: tag => ({ tagName:tag.toUpperCase(), dataset:{}, setAttribute:()=>{}, append:()=>{}, appendChild:()=>{} }),
  addEventListener: () => {},
};
const windowObj = {
  VestraWeeklyEvents: { render: options => { renders.push(options.now); return []; } },
  addEventListener: () => {},
};
class MutationObserver { constructor(fn){ this.fn=fn; } observe(){} disconnect(){} }
const context = { window:windowObj, document, console, Date, MutationObserver, setTimeout:fn=>{fn();return 0;} };
vm.createContext(context);
vm.runInContext(source, context);
const api = windowObj.VestraWeeklyEventsNavigation;
assert(api, 'navigation API is exposed');
assert.strictEqual(api.version, '1.1');
assert.strictEqual(api.maxWeekOffset, 52);
const base = new Date(2026,8,11,9,0,0);
assert.strictEqual(api.shiftedDate(base,-1).getDate(),4);
api.move(-1,base); assert.strictEqual(api.getWeekOffset(),-1); assert.strictEqual(renders.at(-1).getDate(),4);
api.move(1,base); assert.strictEqual(api.getWeekOffset(),0);
api.move(999,base); assert.strictEqual(api.getWeekOffset(),52);
api.reset(base); assert.strictEqual(api.getWeekOffset(),0);
assert(source.includes('weeklyWeekAction'));
assert(!source.includes('style.cssText'));
assert(!source.includes('.style.flexWrap'));
assert(!source.includes('.style.minWidth'));
assert(!source.includes('.style.fontSize'));
assert(styles.includes('[data-weekly-week-nav]{display:flex'));
assert(styles.includes('[data-weekly-week-action]{appearance:none'));
assert(styles.includes('[data-weekly-week-action="today"]{min-width:92px;font-size:10px}'));
console.log('weekly events navigation runtime contract: ok');
