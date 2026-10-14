const assert=require('node:assert/strict');
const fs=require('node:fs');
const scanner=fs.readFileSync('scripts/refresh_prebreakout_scanner.py','utf8');
const copy=fs.readFileSync('market-opportunity-lenses.js','utf8');
assert.match(scanner,/len\(clean\)<220\s*:\s*return None|len\(clean\)<220:return None/);
assert.match(copy,/pelo menos 220 sessões diárias com OHLC válido/);
assert.doesNotMatch(copy,/pelo menos 210 sessões diárias/);
console.log('Prebreakout scanner/UI minimum sample aligned');
