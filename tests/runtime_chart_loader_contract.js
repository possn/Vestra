'use strict';

const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('app-chart-loader.js', 'utf8');
const index = fs.readFileSync('index.html', 'utf8');

assert(!index.includes('chart.umd.min.js'), 'Chart.js must not remain in the parser-ordered HTML bundle');
assert(index.includes('app-chart-loader.js?v=1.0'), 'the local Chart runtime loader must remain versioned');
assert(source.includes("vestra:charts-ready"), 'loader must publish the real runtime readiness boundary');
assert(!/window\.Chart\s*=(?!=)/.test(source), 'loader must never create a fake Chart global');

function harness() {
  const appended = [];
  const events = [];
  const listeners = new Map();
  const document = {
    head: { appendChild(node) { node.isConnected = true; appended.push(node); } },
    documentElement: { appendChild(node) { node.isConnected = true; appended.push(node); } },
    querySelector() { return appended.find(node => node.isConnected) || null; },
    createElement(tag) {
      assert.strictEqual(tag, 'script');
      return {
        dataset: {},
        remove() { this.isConnected = false; }
      };
    }
  };
  const window = {
    __vestraAppHydrated: false,
    addEventListener(type, callback) { listeners.set(type, callback); },
    dispatchEvent(event) { events.push(event.type); }
  };
  class CustomEvent { constructor(type, init) { this.type = type; this.detail = init?.detail; } }
  const context = vm.createContext({ window, document, CustomEvent, setTimeout, clearTimeout, Promise });
  vm.runInContext(source, context, { filename: 'app-chart-loader.js' });
  return { window, appended, events, listeners };
}

(async () => {
  const ok = harness();
  const first = ok.window.VestraChartLoader.ensure();
  const second = ok.window.VestraChartLoader.ensure();
  assert.strictEqual(first, second, 'parallel callers must share one Chart.js request');
  assert.strictEqual(ok.appended.length, 1, 'single-flight must append one script');
  assert.strictEqual(ok.appended[0].async, true, 'dynamic Chart.js must not join parser ordering');
  assert.strictEqual(ok.appended[0].src, ok.window.VestraChartLoader.src);
  ok.window.Chart = { defaults: {} };
  ok.appended[0].onload();
  assert.strictEqual(await first, ok.window.Chart);
  assert.deepStrictEqual(ok.events, ['vestra:charts-ready']);

  const retry = harness();
  const failed = retry.window.VestraChartLoader.ensure();
  retry.appended[0].onerror();
  await assert.rejects(failed, /Não foi possível carregar/);
  const retried = retry.window.VestraChartLoader.ensure();
  assert.strictEqual(retry.appended.length, 2, 'a failed request must be removable and retryable');
  retry.window.Chart = { defaults: {} };
  retry.appended[1].onload();
  await retried;

  assert(retry.listeners.has('vestra:app-ready'), 'idle loading must wait for the hydration boundary');
  console.log('runtime_chart_loader_contract: ok');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
