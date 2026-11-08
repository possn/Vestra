const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');

const source=fs.readFileSync(path.join(__dirname,'..','market-static-universe.js'),'utf8');
const start=source.indexOf('  function unpackStartupPayload(payload) {');
const end=source.indexOf('\n  function create(',start);
assert.ok(start>=0 && end>start,'canonical loader must export an unpack function');
const decode=vm.runInNewContext('('+source.slice(start,end).trim()+')');

const row0={ticker:'BRK-B',risk_gate:'unknown',currency:'USD',market_cap:123456789012345,
            insider_buy_value_30d:null,score:72.3456789};
const v2={layout:'field_rows_v2',generated_at:'2026-11-08',
  fields:['ticker','risk_gate','currency','market_cap','insider_buy_value_30d','score'],
  string_dictionaries:{'1':['unknown','clear'],'2':['USD','EUR']},
  rows:[['BRK-B',0,0,123456789012345,null,72.3456789],
        ['BRK-A',1,1,987654321012345,null,64.4]]};
const value=decode(v2);
assert.equal(value.stocks[0].ticker,row0.ticker);
assert.equal(value.stocks[0].risk_gate,'unknown');
assert.equal(value.stocks[0].currency,'USD');
assert.equal(value.stocks[0].market_cap,row0.market_cap);
assert.equal(value.stocks[0].insider_buy_value_30d,null);
assert.equal(value.stocks[0].score,row0.score);
assert.equal(value.stocks[1].ticker,'BRK-A');
assert.equal(value.stocks[1].risk_gate,'clear');
assert.equal(value.stocks[1].currency,'EUR');
assert.equal(value.string_dictionaries,undefined);
assert.equal(decode({...v2,rows:[['BAD',99,0,1,null,70]]}),null);
assert.equal(decode({...v2,string_dictionaries:{'1':'not-an-array'}}),null);
const legacy=decode({layout:'field_rows_v1',fields:['ticker','risk_gate'],
  rows:[['MSFT','unknown']]});
assert.equal(legacy.stocks[0].risk_gate,'unknown');
console.log('market column dictionary browser contract: ok');
