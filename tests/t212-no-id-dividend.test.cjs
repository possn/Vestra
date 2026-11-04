#!/usr/bin/env node
// Broker event identity regression using the real brokerEventKey implementation.
// Synthetic rows mirror the Trading 212 2023-2026 export fields; no account data.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const src = fs.readFileSync('app-broker-parsing-core.js', 'utf8');
const start = src.indexOf('function brokerExternalIdScope(');
const end = src.indexOf('function brokerPositionKey(', start);
assert(start >= 0 && end > start, 'broker identity functions present');
const context = {
  normStr: x => String(x || '').toLowerCase().trim(),
  parseNum: x => Number(x) || 0,
};
const brokerEventKey = vm.runInNewContext(
  src.slice(start, end) + '\n brokerEventKey;', context,
);
const base = {
  broker: 'Trading 212', type: 'DIVIDEND', dateTime: '2026-07-14 08:20:01',
  ticker: 'TEST', isin: 'US0000000000', name: 'Synthetic Company',
  qty: 0, totalEUR: 1.25, grossLocal: 0,
  actionRaw: 'Dividend (Dividend)', notes: '',
};
const noId = { ...base };
assert.equal(brokerEventKey(noId), brokerEventKey({...noId}),
  'reimporting an ID-less dividend must be idempotent');
assert.notEqual(brokerEventKey(noId), brokerEventKey({...noId, dateTime: '2026-07-15 08:20:01'}),
  'different dividend timestamps must remain distinct');
assert.notEqual(brokerEventKey(noId), brokerEventKey({...noId, notes: 'Manufactured payment'}),
  'different dividend notes must remain distinct');
const a = {...base, type:'BUY', extId:'11111111-1111-4111-8111-111111111111'};
const b = {...a, extId:'22222222-2222-4222-8222-222222222222'};
assert.notEqual(brokerEventKey(a), brokerEventKey(b),
  'two same-amount purchases with distinct official IDs must remain distinct');
assert.equal(brokerEventKey(a), brokerEventKey({...a, broker:'Trading212', notes:'changed export'}),
  'official UUID identity must be independent of file/broker naming');
assert.notEqual(brokerEventKey(a), brokerEventKey({...a, type:'SELL'}),
  'different operation types must remain distinct');
console.log('Trading 212 ID/no-ID identity checks passed');
