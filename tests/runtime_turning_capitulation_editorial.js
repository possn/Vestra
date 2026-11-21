'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('dashboard-market-sentiment.js','utf8');
const window={};
vm.runInNewContext(source,{window,document:{readyState:'loading',addEventListener(){}},console,Date,Intl});
const api=window.VestraDashboardMarketSentiment;
const dates=[];
for(let t=Date.parse('2026-04-01T00:00:00Z');t<=Date.parse('2026-11-20T00:00:00Z');t+=86400000){
  const date=new Date(t);
  if(date.getUTCDay()!==0&&date.getUTCDay()!==6)dates.push(date.toISOString().slice(0,10));
}
const last=dates.slice(-126),anchor=last.at(-1),asOf=new Date('2026-11-21T12:00:00Z');
const detail=closes=>({price_history_1y:last.map((date,i)=>({date,close:closes[i]}))});
const prices=last.map((_,i)=>i===125?88.5:100);
const qqq=last.map((_,i)=>i===125?80:100);
const vix=last.map((_,i)=>i===125?39:15);
const context=api.capitulationContext({SPY:detail(prices),QQQ:detail(qqq),'^VIX':detail(vix)},anchor,asOf);
assert.equal(context.available,true);
assert.equal(context.level,'extreme');
assert.equal(context.vixPercentile,100);
assert.equal(Math.round(context.spyDrawdown126*10)/10,-11.5);
assert.equal(Math.round(context.qqqDrawdown126),-20);
assert.equal(context.methodology,'descriptive_126_session_stress_not_predictive');
// A low technical-recovery score MUST NOT suppress extreme contemporaneous stress.
const factors=[{bottom:false,top:true},{bottom:false,top:false},{bottom:false,top:false},
 {bottom:false,top:false},{bottom:true,top:false}];
const confirmation=api.turningProximityScales(factors,null,anchor,asOf);
assert.equal(confirmation.bottom,15);
assert.equal(confirmation.available,true);
assert.equal(context.level,'extreme');
assert.match(source,/Recuperação técnica/);
assert.doesNotMatch(source,/>Proximidade de fundo</);
assert.match(source,/CORRELATION_TIMEOUT_MS=1800/);
assert.match(source,/html===lastMarkup/);
assert.match(source,/data-dms-turning-toggle/);
const missing=api.capitulationContext({SPY:detail(prices),'^VIX':detail(vix).price_history_1y.slice(-2)},anchor,asOf);
assert.equal(missing.available,false);
console.log('Turning stress / technical confirmation split and Home latency guard passed');
