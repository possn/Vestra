// Regression: the Market stylesheet cache key must track the contrast fix.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const page = fs.readFileSync('index.html','utf8');
const styles = fs.readFileSync('market.css','utf8');
assert.match(page,/market\.css\?v=20261026-contrast1558/);
assert.match(styles,/#viewMarket \.market-row__ticker\s*\{/);
assert.match(styles,/#viewMarket \.market-row__name\s*\{/);
assert.match(styles,/#viewMarket \.market-row__meta\s*\{/);
console.log('Market light-card CSS cache/contrast contract OK');
