'use strict';
const assert=require('node:assert/strict');
const {audit}=require('../scripts/market_turning_forward_audit');

const dates=[];
for(let d=new Date('2025-01-02T00:00:00Z');d<new Date('2026-02-01T00:00:00Z');d=new Date(d.getTime()+86400000)){
  if(d.getUTCDay()!==0&&d.getUTCDay()!==6)dates.push(d.toISOString().slice(0,10));
}
const row=(ticker,n)=>({ticker,source:'offline-synthetic-test',price_history_1y:dates.map((date,i)=>({date,close:n+i*.03}))});
const details={};
for(const [ticker,price] of [['ACWI',120],['SPY',500],['QQQ',420],['IWM',220],['EFA',85],['EEM',50],['^VIX',20],['^VVIX',100],['HYG',78],['LQD',110]])
  details[ticker]=row(ticker,price);
const r=audit(details,new Date('2026-02-02T12:00:00Z'));
assert.equal(r.observations.SPY.count,dates.length);
assert.ok(r.asOfSessions>=100);
assert.ok(r.creditObserved>0);
assert.ok(r.qualifiedDates>0);
assert.equal(r.signalCount,0,'a rising synthetic ETF market cannot fabricate a turning point');
assert.equal(r.matured[60].count,0,'no signals means no estimated forward accuracy');

// Outcomes and vote counts must not depend on bars strictly after the research as-of date.
const earlier=new Date('2025-12-01T12:00:00Z');
const before=audit(details,earlier);
const withFuture={...details,SPY:{...details.SPY,price_history_1y:[...details.SPY.price_history_1y,{date:'2026-03-01',close:999999}]}};
const after=audit(withFuture,earlier);
assert.deepEqual(after.confirmed,before.confirmed);
assert.deepEqual(after.matured,before.matured);
console.log('Market turning-point forward-audit invariants passed');
