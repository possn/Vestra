'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('dashboard-market-sentiment.js','utf8');
const window={};
const document={readyState:'loading',addEventListener(){}};
vm.runInNewContext(source,{window,document,console,Date,Intl});
const api=window.VestraDashboardMarketSentiment;
assert.equal(typeof api.impliedCorrelationContext,'function');
assert.equal(typeof api.turningProximityScales,'function');

const until=new Date('2026-11-21T12:00:00Z');
const anchor='2026-11-20';
const dates=[];
for(let t=Date.parse('2026-04-01T00:00:00Z');t<=Date.parse('2026-11-20T00:00:00Z');t+=86400000){
  const d=new Date(t);
  if(d.getUTCDay()!==0&&d.getUTCDay()!==6) dates.push(d.toISOString().slice(0,10));
}
const last126=dates.slice(-126);
assert.equal(last126.at(-1),anchor);
const series=values=>({price_history_1y:last126.map((date,i)=>({date,close:values[i]}))});
const lowToHigh=last126.map((_,i)=>i<110?10:i===125?46:55);
const cooling=api.impliedCorrelationContext(series(lowToHigh),anchor,until);
assert.equal(cooling.observed,true);
assert.equal(cooling.bottomRelief,true);
assert.equal(cooling.topFragility,false);
assert.ok(cooling.percentile>=75);
assert.equal(cooling.methodology,'asof_completed_relative_percentile_no_directional_probability');
const rising=api.impliedCorrelationContext(series(last126.map((_,i)=>i<110?10:i===125?38:30)),anchor,until);
assert.equal(rising.observed,true);
assert.equal(rising.topFragility,true);
assert.equal(rising.bottomRelief,false);
const missing=api.impliedCorrelationContext(null,anchor,until);
assert.equal(missing.observed,false);
const stale=api.impliedCorrelationContext(series(lowToHigh.slice(0,-1)),anchor,until);
assert.equal(stale.observed,false,'do not carry yesterday COR1M into today');
const future=api.impliedCorrelationContext(series(lowToHigh),anchor,new Date('2026-11-20T12:00:00Z'));
assert.equal(future.observed,false,'unfinished today candle must never be used');

const factors=[
  {name:'VIX + VVIX',bottom:true,top:false},
  {name:'Weekly RSI',bottom:true,top:false},
  {name:'SPY',bottom:true,top:false},
  {name:'NYSE',bottom:true,top:false},
  {name:'Sentiment',bottom:true,top:false},
];
const score=api.turningProximityScales(factors,cooling,anchor,until);
assert.equal(score.available,true);
assert.equal(score.bottom,100);
assert.equal(score.top,0);
assert.equal(score.correlationMaxAdjustment,5);
assert.equal(score.methodology,'fixed_weight_heuristic_not_probability_not_backtested');
const without=api.turningProximityScales(factors,missing,anchor,until);
assert.equal(without.bottom,95,'optional missing COR1M cannot invent five points');
assert.equal(without.correlationObserved,false);
const blocked=api.turningProximityScales(factors.map((x,i)=>i===0?{...x,bottom:false}:x),cooling,anchor,until);
assert.equal(blocked.bottom,75,'COR1M never independently replaces a missing VIX vote');
const topo=api.turningProximityScales(factors.map(x=>({...x,bottom:false,top:true})),rising,anchor,until);
assert.equal(topo.top,100);
assert.equal(topo.bottom,0);
const incomplete=api.turningProximityScales(factors.map((x,i)=>i<2?{...x,bottom:null,top:null}:x),cooling,anchor,until);
assert.equal(incomplete.available,false);
const expired=api.turningProximityScales(factors,cooling,anchor,new Date('2026-12-01T00:00:00Z'));
assert.equal(expired.available,false);
assert.match(source,/const CORRELATION_TICKER='\^COR1M'/);
assert.match(source,/CORRELATION_TICKER,\.\.\.CREDIT_TICKERS/);
assert.match(source,/dms-turning-proximity/);
assert.match(source,/não probabilidades de fundo\/topo/);
console.log('Turning proximity and COR1M as-of research invariants passed');
