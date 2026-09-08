const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-static-universe.js', 'utf8');
assert(source.includes('ensureAnalysisToolsRuntime'), 'static universe must expose analysis tools runtime loader');
assert(source.includes("market-analysis-tools-runtime.js?v=1.0"), 'analysis tools runtime must be cache-busted');

const sw = fs.readFileSync('sw.js', 'utf8');
assert(sw.includes('"./market-analysis-tools-runtime.js"'), 'service worker shell must include analysis tools runtime');
assert(sw.includes('"market-analysis-tools-runtime.js"'), 'analysis tools runtime must be network-first');

const runtimeSource = fs.readFileSync('market-analysis-tools-runtime.js', 'utf8');
new vm.Script(runtimeSource, { filename: 'market-analysis-tools-runtime.js' });
assert(runtimeSource.includes("new Set(['compare', 'scanner', 'theses', 'news'])"), 'runtime must cover all four promoted tools');
assert(runtimeSource.includes('VestraMarketAnalysisToolsRuntime'), 'runtime must publish its controller');

console.log('market analysis tools contract: ok');
