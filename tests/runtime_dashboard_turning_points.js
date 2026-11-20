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

// No NYSE observations are inferred from ETF prices or from a provider label alone.
assert.equal(reading.nyseBreadth.bottom,null);
const nyseSessions=days.filter(day=>day<=inputs.date).slice(-75).map((date,i)=>({date,advancers:1500+i,decliners:1400}));
const nyse={venue:'NYSE',instrument_scope:'listed_common_stocks',method:'issues_advancers_minus_decliners',
  source_url:'https://www.nyse.com/market-data/historical',sessions:nyseSessions};
const observed=api.nyseBreadthFactor(nyse,inputs.spyDaily,inputs.date);
assert.equal(typeof observed.bottom,'boolean');
const supplemented=api.turningPointReading(inputs,null,null,asOf,nyse);
assert.equal(supplemented.factors.length,5,'NYSE must replace proxy, not add a sixth vote');
assert.equal(supplemented.factors[3].name,'NYSE · Advance–Decline');
assert.equal(supplemented.available,4);
assert.equal(api.nyseBreadthFactor({...nyse,sessions:nyseSessions.slice(0,-1)},inputs.spyDaily,inputs.date).bottom,null,
  'a feed missing the anchor session cannot participate');
assert.equal(api.nyseBreadthFactor({...nyse,source_url:''},inputs.spyDaily,inputs.date).bottom,null);
assert.equal(api.nyseBreadthFactor({...nyse,sessions:nyseSessions.map(x=>({...x,advancers:null}))},inputs.spyDaily,inputs.date).bottom,null);

// VVIX is an optional risk modifier for VIX, never a sixth independent vote.
const n=days.length;
const spike={...details,'^VIX':make(i=>i===n-11?45:17)};
const vixOnly=api.turningPointInputs(spike,asOf);
assert.equal(vixOnly.factors.length,4);
assert.equal(vixOnly.factors[0].bottom,true,'VIX spike followed by a sharp fall qualifies for research');
assert.equal(vixOnly.vvixContext.observed,false,'missing VVIX is not a neutral measured value');
const withVVIX={...spike,'^VVIX':make(i=>i>=n-8?85+(i-(n-8))*9:85)};
const guarded=api.turningPointInputs(withVVIX,asOf);
assert.equal(guarded.factors.length,4,'VVIX must not be double-counted');
assert.equal(guarded.vvixContext.observed,true);
assert.equal(guarded.vvixContext.risingStress,true);
assert.equal(guarded.factors[0].bottom,false,'rising VVIX stress blocks a premature VIX relief claim');

// Adding a future-looking price row cannot change the as-of snapshot.
details.SPY.price_history_1y.push({date:'2026-11-20',close:900});
const before=JSON.stringify(inputs);
assert.equal(JSON.stringify(api.turningPointInputs(details,asOf)),before);
console.log('Market turning-point observational invariants passed');
