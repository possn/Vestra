/* Offline market-turning research: no synthetic future bars or success odds. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync('dashboard-market-sentiment.js','utf8');
const context={window:{},document:{readyState:'loading',addEventListener(){}},console,Date,Intl};
vm.runInNewContext(script,context);
const api=context.window.VestraDashboardMarketSentiment;

const noData=api.turningPointInputs({},new Date('2026-11-19T12:00:00Z'));
assert.equal(noData,null,'without SPY/VIX evidence, do not infer a bottom');
assert.equal(api.turningPointReading(noData,null,null),null);

const rsi=api.weeklyRsi14(Array.from({length:30},(_,i)=>100-i));
assert.ok(rsi.current>=0&&rsi.current<=1,'Wilder RSI on uninterrupted losses is near zero');
assert.equal(api.weeklyRsi14(Array.from({length:15},()=>100)),null,'insufficient completed weeks');

const asOf=new Date('2026-11-19T12:00:00Z');
const days=[];
for(let d=new Date('2025-11-01T00:00:00Z');d<asOf;d=new Date(d.getTime()+86400000)){
  if(d.getUTCDay()!==0&&d.getUTCDay()!==6) days.push(d.toISOString().slice(0,10));
}
const make=(value)=>({price_history_1y:days.map((day,i)=>({date:day,close:value(i)}))});
const details={SPY:make(i=>500-i*.35),'^VIX':make(i=>18+i*.03)};
for(const ticker of ['ACWI','QQQ','IWM','EFA','EEM']) details[ticker]=make(i=>100-i*.08);
const inputs=api.turningPointInputs(details,asOf);
assert.ok(inputs,'completed 1y of SPY/VIX should permit an observational reading');
assert.equal(inputs.factors.length,4);
assert.equal(inputs.date,days.at(-2),'today is an unfinished bar and must be excluded');
const reading=api.turningPointReading(inputs,{source:'cnn',score:15,timestamp:'2026-11-18T23:00:00Z'},null,asOf);
assert.equal(reading.available,5);
assert.equal(reading.direction,null,'extreme fear alone does not qualify a bottom');
assert.equal(reading.factors[4].bottom,true);
assert.equal(reading.unvalidated,true);
assert.equal(Object.hasOwn(reading,'probability'),false);

const stale=api.turningPointReading(inputs,{source:'cnn',score:5,timestamp:'2026-10-01T00:00:00Z'},null,asOf);
assert.equal(stale.available,4,'stale fear score is missing evidence, not neutral or positive');
assert.equal(stale.factors[4].bottom,null);

// Adding a future-looking price row cannot change the as-of snapshot.
details.SPY.price_history_1y.push({date:'2026-11-20',close:900});
const before=JSON.stringify(inputs);
assert.equal(JSON.stringify(api.turningPointInputs(details,asOf)),before);
console.log('Market turning-point observational invariants passed');
