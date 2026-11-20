#!/usr/bin/env node
/* Read-only, as-of research of experimental market turning-point confluence.
 * Usage: node scripts/market_turning_forward_audit.js --live
 * Network is only used for live Worker observations; this never publishes signals.
 */
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const script=fs.readFileSync('dashboard-market-sentiment.js','utf8');
const context={window:{},document:{readyState:'loading',addEventListener(){}},console,Date,Intl};
vm.runInNewContext(script,context);
const api=context.window.VestraDashboardMarketSentiment;
const tickers=['ACWI','SPY','QQQ','IWM','EFA','EEM','^VIX','^VVIX','HYG','LQD'];
const worker='https://delicate-bar-cc80.pedrossnunes.workers.dev';

function liveDetails(){
  const details={};
  for(const ticker of tickers){
    const url=`${worker}/market?ticker=${encodeURIComponent(ticker)}`;
    const output=execFileSync('curl',['--fail','--location','--silent','--show-error','--max-time','25',url],
      {encoding:'utf8',maxBuffer:2*1024*1024});
    const detail=JSON.parse(output);
    if(detail?.ticker!==ticker||!Array.isArray(detail?.price_history_1y))
      throw Error(`Invalid Worker identity/history for ${ticker}`);
    details[ticker]=detail;
  }
  return details;
}

function audit(details,now=new Date()){
  const maxDay=now.toISOString().slice(0,10);
  const spy=details.SPY.price_history_1y.filter(x=>x.date<maxDay&&Number(x.close)>0)
    .sort((a,b)=>a.date.localeCompare(b.date));
  const report={generatedAt:now.toISOString(),provider:worker,observations:{},
    asOfSessions:0,qualifiedDates:0,confirmed:{bottom:[],top:[]},
    creditObserved:0,creditEasing:0,creditWorsening:0,horizons:[5,10,20,60],
    priceStructureStates:{},
    methodology:'retrospective_as_of_daily_bars_overlapping_events_not_independent_no_predictive_claim',
    limitations:['One-year rolling history; warm-up reduces the evaluable period',
      'CNN/AAII and genuine NYSE breadth unavailable point-in-time',
      'Overlapping daily signals are not independent observations']};
  for(const ticker of tickers){
    const h=details[ticker].price_history_1y;
    report.observations[ticker]={count:h.length,last:h.at(-1)?.date||null,
      source:details[ticker].source||null};
  }
  // Check every as-of date separately. The API excludes unclosed/future bars.
  // Historical CNN/AAII and genuine NYSE breadth are intentionally absent.
  for(let i=0;i<spy.length;i++){
    const date=spy[i].date;
    const asOf=new Date(`${date}T12:00:00Z`);
    asOf.setUTCDate(asOf.getUTCDate()+1);
    const inputs=api.turningPointInputs(details,asOf);
    if(!inputs||inputs.date!==date)continue;
    report.asOfSessions++;
    if(inputs.creditContext?.observed){
      report.creditObserved++;
      if(inputs.creditContext.easing)report.creditEasing++;
      if(inputs.creditContext.worsening)report.creditWorsening++;
    }
    const reading=api.turningPointReading(inputs,null,null,asOf);
    if(!reading)continue;
    const structure=reading.priceStructure?.state||'unavailable';
    report.priceStructureStates[structure]=(report.priceStructureStates[structure]||0)+1;
    if(reading.available>=4)report.qualifiedDates++;
    if(!reading.direction)continue;
    const event={date,available:reading.available,bottomVotes:reading.bottom,topVotes:reading.top,
      credit:inputs.creditContext?.observed?(inputs.creditContext.easing?'easing':inputs.creditContext.worsening?'worsening':'neutral'):'missing',returns:{}};
    for(const h of report.horizons){
      event.returns[h]=i+h<spy.length?Number(((spy[i+h].close/spy[i].close-1)*100).toFixed(2)):null;
    }
    // Maximum adverse excursion is measured *after* the signal, not inferred from the
    // closing return. Null means the entire horizon is not yet observable.
    event.adverseExcursionPct={};
    for(const h of report.horizons){
      if(i+h>=spy.length){event.adverseExcursionPct[h]=null;continue;}
      const subsequent=spy.slice(i+1,i+h+1).map(x=>x.close/spy[i].close-1);
      const adverse=reading.direction==='bottom'?Math.min(...subsequent):-Math.max(...subsequent);
      event.adverseExcursionPct[h]=Number((100*adverse).toFixed(2));
    }
    report.confirmed[reading.direction].push(event);
  }
  // Sanity: an as-of result must never contain a future source date.
  assert.ok(report.asOfSessions<=spy.length);
  for(const dir of ['bottom','top'])for(const event of report.confirmed[dir])
    assert.ok(event.date<maxDay);
  report.signalCount=report.confirmed.bottom.length+report.confirmed.top.length;
  report.signalSessionsPct=report.asOfSessions?Number((report.signalCount/report.asOfSessions*100).toFixed(2)):null;
  // Consecutive qualifying sessions belong to the same signal episode. This
  // prevents treating five adjacent readings as five independent discoveries.
  report.episodes={bottom:[],top:[]};
  for(const direction of ['bottom','top']){
    const events=report.confirmed[direction];
    let episode=null,previousIndex=-2;
    for(const event of events){
      const sessionIndex=spy.findIndex(x=>x.date===event.date);
      if(!episode||sessionIndex>previousIndex+1){
        episode={start:event.date,end:event.date,observedSessions:0,firstReadingReturns:event.returns,
          firstReadingAdverseExcursionPct:event.adverseExcursionPct};
        report.episodes[direction].push(episode);
      }
      episode.end=event.date;episode.observedSessions++;
      previousIndex=sessionIndex;
    }
  }
  report.matured={};
  for(const h of report.horizons){
    const candidates=[...report.confirmed.bottom.map(x=>({sign:1,event:x})),
      ...report.confirmed.top.map(x=>({sign:-1,event:x}))]
      .filter(x=>x.event.returns[h]!=null);
    const signed=candidates.map(x=>x.sign*x.event.returns[h]);
    const benchmark=spy.length>h?spy.slice(0,-h).map((x,i)=>100*(spy[i+h].close/x.close-1)):[];
    const adverse=candidates.map(x=>x.event.adverseExcursionPct[h]);
    report.matured[h]={count:signed.length,
      positive:signed.filter(x=>x>0).length,
      positiveRatePct:signed.length?Number((100*signed.filter(x=>x>0).length/signed.length).toFixed(2)):null,
      averageSignedReturnPct:signed.length?Number((signed.reduce((a,b)=>a+b,0)/signed.length).toFixed(2)):null,
      averageAdverseExcursionPct:adverse.length?Number((adverse.reduce((a,b)=>a+b,0)/adverse.length).toFixed(2)):null,
      unconditionalSpyMeanReturnPct:benchmark.length?Number((benchmark.reduce((a,b)=>a+b,0)/benchmark.length).toFixed(2)):null,
      benchmarkCaveat:'Unconditional SPY return is descriptive, not a direction-matched or regime-matched control'};
  }
  return report;
}
if(require.main===module){
  if(process.argv[2]!=='--live'){
    console.error('Pass --live to explicitly query the production Worker (read-only).');
    process.exitCode=2;
  }else console.log(JSON.stringify(audit(liveDetails()),null,2));
}
module.exports={audit};
