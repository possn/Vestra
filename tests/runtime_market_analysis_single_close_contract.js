const fs = require('fs');
const assert = require('assert');

const runtime = fs.readFileSync('market-analysis-tools-runtime.js', 'utf8');
const html = fs.readFileSync('index.html', 'utf8');

assert.match(html, /class="market-close-persistent"[^>]*data-market-close/, 'market sheet must keep the single persistent close control');
assert.doesNotMatch(runtime, /data-tool-runtime-close/, 'analysis tools runtime must not render a second close control inside the sheet header');
assert.doesNotMatch(runtime, /class=\\?"market-close\\?"/, 'analysis tools runtime must not inject an inline market-close button');

console.log('market analysis single-close contract ok');
