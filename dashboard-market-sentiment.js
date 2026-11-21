/* Vestra Dashboard Market Sentiment v1.6 — compact transparent market barometer. */
(() => {
  'use strict';

  const STYLE_ID='vestraDashboardMarketSentimentStyle';
  const CARD_ID='vestraMarketSentimentCard';
  const CACHE_KEY='vestra-market-sentiment-v5';
  const CACHE_TTL_MS=15*60*1000;
  const FETCH_TIMEOUT_MS=10000;
  const AAII_REFRESH_INTERVAL_MS=15*60*1000;
  const NYSE_BREADTH_PATH='data/nyse-advance-decline.json';
  let aaiiLastAttempt=0;
  let aaiiRequest=null;

  const RISK_ASSETS=[
    {ticker:'ACWI',name:'Global',weight:.30},
    {ticker:'SPY',name:'S&P 500',weight:.20},
    {ticker:'QQQ',name:'Nasdaq 100',weight:.15},
    {ticker:'IWM',name:'Small caps',weight:.15},
    {ticker:'EFA',name:'Desenvolvidos ex-EUA',weight:.10},
    {ticker:'EEM',name:'Emergentes',weight:.10},
  ];
  const VIX_TICKER='^VIX';
  const VVIX_TICKER='^VVIX'; // Optional volatility-of-volatility context, not a sixth vote.
  const CORRELATION_TICKER='^COR1M'; // Optional Cboe 1-month implied correlation; never fabricated if absent.
  const CREDIT_TICKERS=['HYG','LQD']; // Optional tradable credit proxies, not a credit spread.

  const S={loading:false,data:null,error:'',scheduled:false,expanded:false,turningExpanded:false,aaiiExpanded:false,aaii:null,cnn:null,nyse:null};
  const num=v=>{if(v===null||v===undefined||v==='') return null;const n=Number(v);return Number.isFinite(n)?n:null};
  const clamp=(v,min=0,max=100)=>Math.max(min,Math.min(max,v));
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function workerBase(){
    try{return String((typeof state!=='undefined'&&state?.settings?.workerUrl)||'').trim().replace(/\/$/,'');}
    catch{return '';}
  }

  function ensureStyles(){
    if(document.getElementById(STYLE_ID)) return;
    const link=document.createElement('link');
    link.id=STYLE_ID;
    link.rel='stylesheet';
    link.href='dashboard-market-sentiment.css?v=1.8';
    document.head.appendChild(link);
  }

  function historyFor(detail){
    return (Array.isArray(detail?.price_history_1y)?detail.price_history_1y:[])
      .map(x=>({date:String(x?.date||x?.timestamp||''),close:num(x?.close)}))
      .filter(x=>x.close!=null);
  }

  function at(rows,offset=0){
    const i=rows.length-1-Math.max(0,offset);
    return i>=0?rows[i]:null;
  }

  function averageBefore(rows,count,offset=0){
    const end=rows.length-Math.max(0,offset);
    const vals=rows.slice(Math.max(0,end-count),end).map(x=>x.close).filter(Number.isFinite);
    return vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;
  }

  function returnPct(rows,count,offset=0){
    const end=rows.length-1-Math.max(0,offset);
    const start=end-count;
    if(end<0||start<0) return null;
    const a=num(rows[start]?.close),b=num(rows[end]?.close);
    return a>0&&b!=null?(b/a-1)*100:null;
  }

  function scoreDistance(current,ma){
    if(current==null||ma==null||ma<=0) return null;
    const d=(current/ma-1)*100;
    return clamp(50+clamp(d*3,-25,25));
  }

  function assetSignals(rows,offset=0){
    const current=num(at(rows,offset)?.close);
    if(current==null) return null;
    const ma50=averageBefore(rows,50,offset), ma200=averageBefore(rows,200,offset);
    const d50=scoreDistance(current,ma50), d200=scoreDistance(current,ma200);
    const trendParts=[d50,d200].filter(x=>x!=null);
    const trend=trendParts.length?trendParts.reduce((a,b)=>a+b,0)/trendParts.length:null;

    const r1=returnPct(rows,21,offset), r3=returnPct(rows,63,offset);
    const momentumParts=[];
    if(r1!=null) momentumParts.push(clamp(50+clamp(r1*2.2,-25,25)));
    if(r3!=null) momentumParts.push(clamp(50+clamp(r3*.9,-25,25)));
    const momentum=momentumParts.length?momentumParts.reduce((a,b)=>a+b,0)/momentumParts.length:null;

    let participation=null;
    if(ma50!=null||ma200!=null){
      const flags=[];
      if(ma50!=null) flags.push(current>=ma50?100:0);
      if(ma200!=null) flags.push(current>=ma200?100:0);
      participation=flags.reduce((a,b)=>a+b,0)/flags.length;
    }
    return {current,ma50,ma200,r1,r3,trend,momentum,participation};
  }

  function priceFreshness(details){
    const latestDates=[...RISK_ASSETS.map(x=>x.ticker),VIX_TICKER].map(ticker=>{
      const rows=historyFor(details[ticker]);
      const raw=String(rows[rows.length-1]?.date||'');
      const match=/^(\d{4}-\d{2}-\d{2})/.exec(raw);
      return match?.[1]||null;
    }).filter(Boolean);
    if(!latestDates.length) return {date:null,coverage:0};
    // Earliest last-quote date is conservative when instruments update at different times.
    return {date:latestDates.sort()[0],coverage:latestDates.length};
  }

  function weightedMetric(details,key,offset=0){
    let sum=0,weight=0;
    for(const asset of RISK_ASSETS){
      const rows=historyFor(details[asset.ticker]);
      const signals=assetSignals(rows,offset);
      const value=num(signals?.[key]);
      if(value==null) continue;
      sum+=value*asset.weight;
      weight+=asset.weight;
    }
    return weight>0?sum/weight:null;
  }

  function vixScore(details,offset=0){
    const rows=historyFor(details[VIX_TICKER]);
    const current=num(at(rows,offset)?.close);
    if(current==null) return null;
    const r1=returnPct(rows,21,offset);
    let score=clamp(100-(current-10)*3,10,90);
    if(r1!=null) score-=clamp(r1*.3,-10,10);
    return {score:clamp(score),current,r1};
  }

  function computeSnapshot(details,offset=0){
    const trend=weightedMetric(details,'trend',offset);
    const momentum=weightedMetric(details,'momentum',offset);
    const participation=weightedMetric(details,'participation',offset);
    const vol=vixScore(details,offset);
    const parts=[
      ['Tendência',trend,.35],
      ['Momentum',momentum,.30],
      ['Participação proxy',participation,.20],
      ['Volatilidade',num(vol?.score),.15],
    ].filter(x=>x[1]!=null);
    const totalWeight=parts.reduce((s,x)=>s+x[2],0);
    // Incomplete components must not be silently reweighted into a strong signal.
    if(totalWeight<.8) return null;
    const score=Math.round(parts.reduce((s,x)=>s+x[1]*x[2],0)/totalWeight);
    return {score:clamp(score),trend,momentum,participation,vol,parts};
  }

  // Experimental turning-point *confluence*, never a probability or trade signal.
  // Use only completed daily/weekly sessions and preserve missing measurements.
  function completedHistory(detail,asOf=new Date()){
    const today=asOf.toISOString().slice(0,10);
    const seen=new Set();
    return historyFor(detail).filter(row=>{
      const day=row.date.slice(0,10);
      if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||day>=today||seen.has(day)||!(row.close>0)) return false;
      seen.add(day);row.date=day;return true;
    }).sort((a,b)=>a.date.localeCompare(b.date));
  }

  function weeklyCompletedCloses(rows,asOf){
    const groups=new Map();
    const today=asOf.toISOString().slice(0,10);
    for(const row of rows){
      const date=new Date(`${row.date}T00:00:00Z`);
      const monday=new Date(date.getTime()-((date.getUTCDay()+6)%7)*86400000);
      const weekEnd=new Date(monday.getTime()+7*86400000).toISOString().slice(0,10);
      if(weekEnd<=today) groups.set(monday.toISOString().slice(0,10),row.close);
    }
    return [...groups.values()];
  }

  function weeklyRsi14(closes){
    if(closes.length<17) return null;
    let gains=0,losses=0;
    for(let i=1;i<=14;i++){
      const delta=closes[i]-closes[i-1];gains+=Math.max(0,delta);losses+=Math.max(0,-delta);
    }
    let avgGain=gains/14,avgLoss=losses/14;
    const output=[];
    const value=()=>avgLoss===0?(avgGain===0?50:100):100-100/(1+avgGain/avgLoss);
    output.push(value());
    for(let i=15;i<closes.length;i++){
      const delta=closes[i]-closes[i-1];
      avgGain=(avgGain*13+Math.max(0,delta))/14;
      avgLoss=(avgLoss*13+Math.max(0,-delta))/14;
      output.push(value());
    }
    return {current:output.at(-1),previous:output.at(-2),recent:output.slice(-4)};
  }

  // HYG/LQD relative performance is a price-only *credit risk-appetite proxy*.
  // It is not a corporate yield spread and does not change turning-point votes.
  function creditStressContext(details,anchor,asOf=new Date()){
    const hyg=completedHistory(details.HYG,asOf),lqd=completedHistory(details.LQD,asOf);
    const lqdByDate=new Map(lqd.map(row=>[row.date,row.close]));
    const joined=hyg.filter(row=>row.date<=anchor&&lqdByDate.has(row.date))
      .map(row=>({date:row.date,ratio:row.close/lqdByDate.get(row.date)}))
      .filter(row=>Number.isFinite(row.ratio)&&row.ratio>0);
    if(joined.length<65||joined.at(-1)?.date!==anchor||
       hyg.at(-1)?.date!==anchor||lqd.at(-1)?.date!==anchor)
      return {observed:false,value:'HYG/LQD sem histórico diário comparável'};
    const recent=joined.slice(-61),last=recent.at(-1).ratio;
    const change5=100*(last/recent.at(-6).ratio-1);
    const change20=100*(last/recent.at(-21).ratio-1);
    const low60=Math.min(...recent.map(x=>x.ratio));
    const high60=Math.max(...recent.map(x=>x.ratio));
    const easing=change5>0.5&&change20>0&&last/low60<=1.10;
    const worsening=change5< -0.5&&change20<0&&high60/last<=1.10;
    return {observed:true,easing,worsening,date:anchor,change5,change20,
      value:`HYG/LQD ${change5>=0?'+':''}${change5.toFixed(1)}%/5s · ${change20>=0?'+':''}${change20.toFixed(1)}%/20s · ${easing?'stress a aliviar':worsening?'stress a agravar':'sem confirmação'}`};
  }

  // COR1M is an index implied-correlation level, NOT a realized-correlation
  // measure and not itself a timing direction. 126 as-of completed sessions
  // give a within-regime percentile; prices on a different as-of date fail
  // closed instead of carrying an old value forward.
  function impliedCorrelationContext(detail,anchor,asOf=new Date()){
    const rows=completedHistory(detail,asOf).filter(row=>row.date<=anchor);
    if(rows.length<126||rows.at(-1)?.date!==anchor)
      return {observed:false,value:'COR1M sem 126 sessões comparáveis'};
    const recent=rows.slice(-126);
    const values=recent.map(x=>x.close);
    if(values.some(v=>!Number.isFinite(v)||v<0||v>100))
      return {observed:false,value:'COR1M inválido'};
    const current=values.at(-1),previous5=values.at(-6);
    if(!previous5||previous5<=0)
      return {observed:false,value:'COR1M sem base comparável'};
    const percentile=100*values.filter(v=>v<=current).length/values.length;
    const change5Pct=100*(current/previous5-1);
    const peak10=Math.max(...values.slice(-10));
    // An elevated but still rising COR1M indicates contagion risk; only
    // cooling after stress qualifies as *context* supporting a bottom.
    const bottomRelief=percentile>=75&&current<=peak10*.93&&change5Pct<=-7;
    const topFragility=percentile>=85&&change5Pct>=10;
    return {observed:true,date:anchor,current,percentile,change5Pct,
      bottomRelief,topFragility,
      value:`COR1M ${current.toFixed(1)} · percentil ${Math.round(percentile)}/100 (126s) · ${change5Pct>=0?'+':''}${change5Pct.toFixed(1)}%/5s`,
      methodology:'asof_completed_relative_percentile_no_directional_probability'};
  }

  // A bounded explanatory confluence scale, NOT a probability. Each family
  // receives a fixed maximum weight; COR1M can add only five points within
  // the already existing volatility family and never creates a sixth vote.
  function turningProximityScales(factors,correlation,asOf,now=new Date()){
    const familyWeights=[25,20,20,20,15]; // volatility, weekly RSI, SPY, breadth, sentiment
    if(!Array.isArray(factors)||factors.length!==familyWeights.length)
      return {available:false,reason:'Indicadores incompletos'};
    const dateMs=Date.parse(String(asOf||'')+'T23:59:59Z');
    const age=(now.getTime()-dateMs)/86400000;
    const observed=factors.filter(f=>typeof f?.bottom==='boolean'&&typeof f?.top==='boolean').length;
    if(observed<4||!Number.isFinite(age)||age< -1||age>5)
      return {available:false,reason:'Cobertura insuficiente ou observações antigas',observed};
    const vol=factors[0];
    const corr=correlation?.observed===true&&correlation.date===asOf?correlation:null;
    const one=(direction)=>{
      let total=0;
      for(let i=0;i<familyWeights.length;i++){
        const factor=factors[i];
        if(factor?.[direction]!==true) continue;
        if(i===0){
          total+=20;
          if(corr&&(direction==='bottom'?corr.bottomRelief:corr.topFragility)===true)
            total+=5;
        }else total+=familyWeights[i];
      }
      return Math.round(clamp(total));
    };
    const bottom=one('bottom'),top=one('top');
    const label=score=>score>=70?'Confluência elevada':score>=50?'Atenção acrescida':
      score>=25?'Sinais iniciais':'Confluência fraca';
    return {available:true,bottom,top,bottomLabel:label(bottom),topLabel:label(top),
      observed,possible:5,correlationObserved:!!corr,
      priceBottomConfirmed:factors[2]?.bottom===true,
      priceTopConfirmed:factors[2]?.top===true,
      methodology:'fixed_weight_heuristic_not_probability_not_backtested',
      weightFamilies:familyWeights,correlationMaxAdjustment:5};
  }

  function turningPointInputs(details,asOf=new Date()){
    const spy=completedHistory(details.SPY,asOf);
    const vix=completedHistory(details[VIX_TICKER],asOf);
    const anchor=spy.at(-1)?.date;
    if(!anchor||!vix.some(row=>row.date===anchor)) return null;
    const index=vix.findIndex(row=>row.date===anchor);
    const alignedVix=vix.slice(0,index+1);
    const correlation=impliedCorrelationContext(details[CORRELATION_TICKER],anchor,asOf);
    const vvix=completedHistory(details[VVIX_TICKER],asOf);
    const vvixIndex=vvix.findIndex(row=>row.date===anchor);
    const vvixRecent=vvixIndex>=125?vvix.slice(vvixIndex-125,vvixIndex+1):[];
    let vvixContext=null;
    if(vvixRecent.length===126){
      const levels=vvixRecent.map(row=>row.close).sort((a,b)=>a-b);
      const current=vvixRecent.at(-1).close;
      const peak=Math.max(...vvixRecent.slice(-10).map(row=>row.close));
      const prior5=vvixRecent.at(-6).close;
      vvixContext={current,
        risingStress:current>=levels[113]&&current>prior5*1.08,
        cooling:peak>=levels[113]&&current<=peak*.90,
        change5Pct:100*(current/prior5-1)};
    }
    const factors=[];
    const recent=alignedVix.slice(-126);
    if(recent.length===126){
      const sorted=recent.map(row=>row.close).sort((a,b)=>a-b);
      const peak=Math.max(...recent.slice(-10).map(row=>row.close));
      const trough=Math.min(...recent.slice(-10).map(row=>row.close));
      const current=recent.at(-1).close;
      factors.push({name:'VIX + VVIX · tensão',
        value:`VIX ${current.toFixed(1)} · ${vvixContext?`VVIX ${vvixContext.current.toFixed(1)} (${vvixContext.change5Pct>=0?'+':''}${vvixContext.change5Pct.toFixed(1)}%/5s)`:'VVIX sem histórico comparável'}`,
        bottom:peak>=Math.max(25,sorted[113])&&current<=peak*.92&&vvixContext?.risingStress!==true,
        top:trough<=Math.min(18,sorted[12])&&current>=trough*1.12&&vvixContext?.cooling!==true});
    }else factors.push({name:'VIX',value:'Histórico insuficiente',bottom:null,top:null});

    const weekly=weeklyRsi14(weeklyCompletedCloses(spy,asOf));
    factors.push({name:'RSI · semanal fechado',value:weekly?`RSI ${weekly.current.toFixed(1)}`:'Sem 17 semanas completas',
      bottom:weekly?Math.min(...weekly.recent)<=35&&weekly.current>weekly.previous+2:null,
      top:weekly?Math.max(...weekly.recent)>=65&&weekly.current<weekly.previous-2:null});

    const closes=spy.map(row=>row.close),n=closes.length;
    if(n>=60){
      const last=closes[n-1],prior=closes[n-6],low=Math.min(...closes.slice(-60)),high=Math.max(...closes.slice(-60));
      const ma5=closes.slice(-5).reduce((a,b)=>a+b,0)/5;
      factors.push({name:'S&P 500 · estabilização',value:`5 sessões ${((last/prior-1)*100).toFixed(1)}%`,
        bottom:last>ma5&&last>prior&&last/low-1<=.10,
        top:last<ma5&&last<prior&&high/last-1<=.10});
    }else factors.push({name:'S&P 500',value:'Histórico insuficiente',bottom:null,top:null});

    let coverage=0,recovering=0,deteriorating=0;
    for(const asset of RISK_ASSETS){
      const rows=completedHistory(details[asset.ticker],asOf).filter(row=>row.date<=anchor);
      if(rows.length<21||rows.at(-1).date<anchor) continue;
      coverage++;
      const values=rows.map(row=>row.close),last=values.at(-1),prior=values.at(-6);
      const ma10=values.slice(-10).reduce((a,b)=>a+b,0)/10;
      if(last>prior&&last>ma10) recovering++;
      if(last<prior&&last<ma10) deteriorating++;
    }
    factors.push({name:'Participação · 6 mercados proxy',value:`${coverage}/6 mercados comparáveis`,
      bottom:coverage>=5?recovering>=4:null,
      top:coverage>=5?deteriorating>=4:null});
    return {date:anchor,factors,spyDaily:spy.slice(-90),
      impliedCorrelation:correlation,
      creditContext:creditStressContext(details,anchor,asOf),vvixContext:vvixContext?{
      observed:true,risingStress:vvixContext.risingStress,cooling:vvixContext.cooling,
      current:vvixContext.current}: {observed:false},
      method:'experimental_unvalidated_not_probability'};
  }

  function turningSentiment(cnn,aaii,asOf=new Date()){
    const age=iso=>{const t=Date.parse(iso||'');return Number.isFinite(t)?(asOf.getTime()-t)/86400000:Infinity;};
    const score=num(cnn?.score);
    if(cnn?.source==='cnn'&&score!=null&&score>=0&&score<=100&&age(cnn.timestamp)>=0&&age(cnn.timestamp)<=3)
      return {name:'Sentimento · CNN',value:`Fear & Greed ${Math.round(score)}`,bottom:score<=25,top:score>=75};
    const latest=aaii?.weeks?.[0],spread=aaiiSpread(latest);
    if(spread!=null&&age(`${latest.date}T23:59:59Z`)>=0&&age(`${latest.date}T23:59:59Z`)<=8)
      return {name:'Sentimento · AAII',value:`Bull−Bear ${spread.toFixed(1)} pp`,bottom:spread<=-20,top:spread>=20};
    return {name:'Sentimento',value:'Sem observação recente',bottom:null,top:null};
  }

  // NYSE advancing minus declining *listed common shares*, never ETF-proxy breadth.
  // The source must provide observed issue counts and an auditable provenance URL.
  // Missing, mismatched or stale observations never become a vote.
  function nyseBreadthFactor(payload,spyDaily,anchor){
    const unavailable=(reason)=>({name:'NYSE · Advance–Decline',value:reason,bottom:null,top:null});
    if(payload?.venue!=='NYSE'||payload?.instrument_scope!=='listed_common_stocks'||
       payload?.method!=='issues_advancers_minus_decliners'||
       !/^https:\/\//.test(payload?.source_url||'')||!Array.isArray(payload?.sessions))
      return unavailable('Fonte NYSE verificável indisponível');
    const spy=new Map((spyDaily||[]).map(row=>[row.date,row.close]));
    const sessions=payload.sessions;
    if(sessions.length<60||sessions.length>1500) return unavailable('Série NYSE insuficiente');
    let prev='',cumulative=0;
    const aligned=[];
    for(const row of sessions){
      const {date,advancers,decliners}=row||{};
      if(typeof date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(date)||date<=prev||date>anchor||
         !Number.isSafeInteger(advancers)||!Number.isSafeInteger(decliners)||
         advancers<0||decliners<0||advancers+decliners<100||advancers+decliners>10000)
        return unavailable('Série NYSE inválida');
      prev=date;cumulative+=advancers-decliners;
      if(spy.has(date)) aligned.push({date,price:spy.get(date),ad:cumulative});
    }
    if(prev!==anchor||aligned.length<45||aligned.at(-1)?.date!==anchor)
      return unavailable('NYSE sem cobertura comparável ao S&P 500');
    const recent=aligned.slice(-41);
    if(recent.length<41) return unavailable('NYSE sem janela de divergência');
    const prior=recent.slice(0,20),last=recent.slice(20);
    const p=last.at(-1),prevPriceLow=Math.min(...prior.map(x=>x.price));
    const prevPriceHigh=Math.max(...prior.map(x=>x.price));
    const priorAdLow=Math.min(...prior.map(x=>x.ad)),priorAdHigh=Math.max(...prior.map(x=>x.ad));
    const adChange5=p.ad-last.at(-6).ad;
    const bottom=p.price<=prevPriceLow*1.005&&p.ad>priorAdLow&&adChange5>0;
    const top=p.price>=prevPriceHigh*.995&&p.ad<priorAdHigh&&adChange5<0;
    return {name:'NYSE · Advance–Decline',value:`A−D 5 sessões ${adChange5>=0?'+':''}${adChange5} · divergência ${bottom?'positiva':top?'negativa':'não confirmada'}`,
      bottom,top,sourceUrl:payload.source_url};
  }

  function turningPointReading(base,cnn,aaii,asOf=new Date(),nyse=null){
    if(!base||!Array.isArray(base.factors)) return null;
    const breadth=nyseBreadthFactor(nyse,base.spyDaily,base.date);
    // NYSE breadth supersedes, rather than double-counts, the six-ETF proxy.
    const factors=[...base.factors];
    if(typeof breadth.bottom==='boolean') factors[3]=breadth;
    factors.push(turningSentiment(cnn,aaii,asOf));
    const available=factors.filter(f=>typeof f.bottom==='boolean').length;
    const bottom=factors.filter(f=>f.bottom===true).length,top=factors.filter(f=>f.top===true).length;
    const ageDays=(asOf.getTime()-Date.parse(`${base.date}T23:59:59Z`))/86400000;
    const usable=available>=4&&Number.isFinite(ageDays)&&ageDays>=-1&&ageDays<=5;
    const direction=usable&&bottom>=3&&bottom>top&&factors[2]?.bottom===true?'bottom':
      usable&&top>=3&&top>bottom&&factors[2]?.top===true?'top':null;
    return {direction,bottom,top,available,factors,nyseBreadth:breadth,asOf:base.date,
      correlation:base.impliedCorrelation||{observed:false,value:'COR1M indisponível'},
      proximity:turningProximityScales(factors,base.impliedCorrelation,base.date,asOf),
      priceStructure:turningPriceStructure(base.spyDaily),
      label:!usable?'Evidência incompleta ou antiga':direction==='bottom'?'Possível fundo em formação':direction==='top'?'Possível topo em formação':'Sem confluência de inversão',
      unvalidated:true};
  }

  // Descriptive price-structure context, deliberately NOT an additional vote.
  // This distinguishes a falling market from an observed recovery without
  // asserting that either state predicts the final bottom or top.
  function turningPriceStructure(rows){
    const values=(Array.isArray(rows)?rows:[]).map(r=>Number(r?.close));
    if(values.length<55||values.some(v=>!Number.isFinite(v)||v<=0))
      return {state:'unavailable',label:'Estrutura de preços indisponível'};
    const mean=(part)=>part.reduce((a,b)=>a+b,0)/part.length;
    const last=values.at(-1),ma20=mean(values.slice(-20)),ma50=mean(values.slice(-50));
    const priorMa20=mean(values.slice(-25,-5));
    const r5=last/values.at(-6)-1,r20=last/values.at(-21)-1;
    const low20=Math.min(...values.slice(-20));
    let state='mixed',label='Estrutura sem direção clara';
    if(last>ma20&&last>ma50&&ma20>priorMa20&&r20>0){
      state='technical_recovery';label='Recuperação técnica observada';
    }else if(last>ma20&&r5>0&&last<=ma50){
      state='early_recovery';label='Recuperação inicial, ainda abaixo da média de 50 sessões';
    }else if(last<=ma20&&r20<0&&last>values.at(-6)&&last<=low20*1.05){
      state='stabilizing_decline';label='Queda com estabilização inicial a verificar';
    }else if(last<=ma20&&r20<0){
      state='declining';label='Queda ainda em curso';
    }
    return {state,label,asOf:rows.at(-1)?.date||null,
      aboveMa20:last>ma20,aboveMa50:last>ma50,
      return5Pct:Number((r5*100).toFixed(2)),return20Pct:Number((r20*100).toFixed(2)),
      descriptiveOnly:true};
  }

  function turningMarkup(){
    const r=turningPointReading(S.data?.turningInputs,S.cnn,S.aaii,new Date(),S.nyse);
    if(!r) return '<section class="dms-turning"><span>INVERSÕES · EXPERIMENTAL</span><strong>Leitura indisponível</strong><p>Faltam históricos completos do SPY e do VIX.</p></section>';
    const rows=r.factors.map(f=>`<li><span>${esc(f.name)}</span><b>${esc(f.value)}</b><small>${f.bottom===null?'Sem evidência':f.bottom?'Pista de fundo':f.top?'Pista de topo':'Não confirma'}</small></li>`).join('');
    const count=r.direction==='top'?r.top:r.bottom;
    const proximity=r.proximity?.available?r.proximity:null;
    const scale=(kind,label,score,caption)=>`<div class="dms-turning-proximity-item dms-turning-proximity-${kind}">
      <div class="dms-turning-proximity-heading"><span>${esc(label)}</span><strong>${score}<small>/100</small></strong></div>
      <div class="dms-turning-proximity-track" role="meter" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${score}" aria-valuetext="${esc(caption)}"><span style="width:${score}%"></span></div>
      <small>${esc(caption)}</small></div>`;
    const scalesMarkup=proximity?`<div class="dms-turning-proximity" aria-label="Escalas experimentais de confluência">
      ${scale('bottom','Proximidade de fundo',proximity.bottom,proximity.bottomLabel)}
      ${scale('top','Proximidade de topo',proximity.top,proximity.topLabel)}
      <p>Escalas heurísticas de confluência, não probabilidades de fundo/topo. ${proximity.observed}/5 famílias observadas. ${proximity.correlationObserved?'COR1M disponível como contexto':'COR1M indisponível; sem pontos de correlação'}.</p>
    </div>`:'<p class="dms-turning-proximity-missing">Escalas 0–100 indisponíveis: cobertura insuficiente ou dados antigos.</p>';
    return `<section class="dms-turning" aria-label="Possíveis inversões de mercado, investigação experimental">
      <span>INVERSÕES · EXPERIMENTAL</span><strong>${esc(r.label)}</strong>
      ${scalesMarkup}
      <p>${esc(r.priceStructure.label)} (estrutura técnica descritiva). ${r.direction?`${count} de ${r.available} critérios observados convergem.`:`Fundo ${r.bottom} · topo ${r.top} de ${r.available} critérios observados.`} Contagem de evidências, não probabilidade nem sinal de investimento.</p>
      <button type="button" class="dms-turning-toggle" data-dms-turning-toggle aria-expanded="${S.turningExpanded?'true':'false'}" aria-controls="dmsTurningEvidence">${S.turningExpanded?'Ocultar evidências':'Ver VIX, VVIX, RSI e evidências'} <span aria-hidden="true">${S.turningExpanded?'−':'+'}</span></button>
      <div class="dms-turning-evidence" id="dmsTurningEvidence"${S.turningExpanded?'':' hidden'}><ul>${rows}</ul><p><strong>Crédito (contexto, sem voto):</strong> ${esc(S.data?.turningInputs?.creditContext?.value||'HYG/LQD indisponível')}. ${esc(r.nyseBreadth.value)}${r.nyseBreadth.sourceUrl?` · <a href="${esc(r.nyseBreadth.sourceUrl)}" target="_blank" rel="noopener noreferrer">Fonte NYSE ↗</a>`:''}. Última sessão fechada ${esc(r.asOf)}. COR1M: ${esc(r.correlation.value)}. O COR1M só pode acrescentar até 5 pontos dentro da família VIX, se houver evidência de alívio após tensão ou contágio em alta; não soma um voto independente. VVIX ajusta o contexto do VIX, sem voto adicional. A linha A−D NYSE substitui a proxy dos seis mercados apenas com dados auditáveis; não soma um voto. HYG/LQD é uma proxy de preços, não um spread de crédito. Limiar heurístico sem validação prospetiva; VIX e VVIX não preveem direção.</p></div>
    </section>`;
  }

  function labelFor(score){
    if(score<=20) return ['Muito Bearish','bearish'];
    if(score<=40) return ['Bearish','bearish'];
    if(score<60) return ['Neutral','neutral'];
    if(score<80) return ['Bullish','bullish'];
    return ['Muito Bullish','bullish'];
  }

  function deltaLabel(current,previous,label){
    if(current==null||previous==null) return `${label} —`;
    const d=Math.round(current-previous);
    return `${label} ${d>0?'+':''}${d} pts`;
  }

  function aaiiPct(value){
    const n=num(value);
    return n==null?'—':`${n.toFixed(1)}%`;
  }

  function aaiiDate(iso){
    try{
      return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short'}).format(new Date(`${iso}T12:00:00Z`));
    }catch{return String(iso||'—');}
  }

  function aaiiSpread(row){
    const bull=num(row?.bullish),bear=num(row?.bearish);
    return bull==null||bear==null?null:bull-bear;
  }

  function aaiiSpreadText(value){
    const n=num(value);
    return n==null?'—':`${n>0?'+':''}${n.toFixed(1)} pp`;
  }

  function aaiiWeekCard(week){
    const spread=aaiiSpread(week);
    const tone=spread==null?'neutral':spread>8?'bull':spread<-8?'bear':'neutral';
    return `<article class="dms-aaii-weekcard">
      <div class="dms-aaii-weekcard__head">
        <strong>Semana de ${esc(aaiiDate(week.date))}</strong>
        <div class="dms-aaii-weekcard__spread"><small>Bull–Bear</small><b class="is-${tone}">${aaiiSpreadText(spread)}</b></div>
      </div>
      <div class="dms-aaii-mix" aria-label="Bullish ${aaiiPct(week.bullish)}, neutral ${aaiiPct(week.neutral)}, bearish ${aaiiPct(week.bearish)}">
        <i class="is-bull" style="width:${num(week.bullish)??0}%"></i>
        <i class="is-neutral" style="width:${num(week.neutral)??0}%"></i>
        <i class="is-bear" style="width:${num(week.bearish)??0}%"></i>
      </div>
      <div class="dms-aaii-legend">
        <span>▲ Bullish <b>${aaiiPct(week.bullish)}</b></span>
        <span>● Neutral <b>${aaiiPct(week.neutral)}</b></span>
        <span>▼ Bearish <b>${aaiiPct(week.bearish)}</b></span>
      </div>
    </article>`;
  }

  function cnnMarkup(){
    const item=S.cnn;
    const score=num(item?.score);
    const zone=score==null?'Sem dados':'CNN · '+String(item.rating||'').replace(/_/g,' ');
    const official='<a href="https://www.cnn.com/markets/fear-and-greed" target="_blank" rel="noopener noreferrer">CNN Business ↗</a>';
    return `<section class="dms-cnn" aria-label="CNN Fear and Greed Index">
      <div class="dms-cnn-top"><div><span class="dms-cnn-kicker">CNN BUSINESS · FEAR & GREED INDEX</span><h3>Medo e ganância</h3></div><div class="dms-cnn-value">${score==null?'—':Math.round(score)}<small>/100</small></div></div>
      <p class="dms-cnn-intro">Indicador independente da CNN, baseado em sete sinais de mercado. Não é o score Vestra nem o inquérito AAII.</p>
      <div class="dms-cnn-meter"><i style="left:${score==null?50:clamp(score)}%"></i></div>
      <div class="dms-cnn-scale"><span>Medo extremo</span><strong>${esc(zone)}</strong><span>Ganância extrema</span></div>
      <div class="dms-cnn-comparisons"><span>Fecho anterior <b>${metric(num(item?.previous_close))}</b></span><span>1 semana <b>${metric(num(item?.previous_1_week))}</b></span><span>1 mês <b>${metric(num(item?.previous_1_month))}</b></span><span>1 ano <b>${metric(num(item?.previous_1_year))}</b></span></div>
      <div class="dms-cnn-source">Fonte: ${official} · ${item?.timestamp?esc(String(item.timestamp).slice(0,16).replace('T',' '))+' UTC':'Aguardando atualização verificada'}</div>
    </section>`;
  }

  async function loadCnn(){
    try{
      const response=await fetch('data/cnn-fear-greed.json',{cache:'no-store'});
      if(!response.ok) throw new Error('CNN data '+response.status);
      const payload=await response.json();
      if(payload?.source!=='cnn' || num(payload.score)==null || num(payload.score)<0 || num(payload.score)>100) throw new Error('CNN payload inválido');
      S.cnn=payload;
    }catch(error){console.warn('[Vestra] CNN Fear & Greed unavailable',error);S.cnn=null;}
    render();
  }

  function aaiiMarkup(){
    const weeks=Array.isArray(S.aaii?.weeks)?S.aaii.weeks.slice(0,5):[];
    if(!weeks.length) return '';
    const latest=weeks[0];
    const latestMillis=Date.parse(String(latest.date||'')+'T00:00:00Z');
    const ageDays=Number.isFinite(latestMillis)?Math.floor((Date.now()-latestMillis)/86400000):null;
    const stale=ageDays==null||ageDays<0||ageDays>8;
    const staleNotice=stale
      ? '<p class="dms-aaii-note" role="status">Dados AAII desatualizados · última semana '+esc(aaiiDate(latest.date))+' · atualização por confirmar</p>'
      : '';
    const spread=aaiiSpread(latest);
    const prior=weeks[1]?aaiiSpread(weeks[1]):null;
    const delta=spread!=null&&prior!=null?spread-prior:null;
    const dominant=num(latest?.bearish)>num(latest?.bullish)?'Predomina cautela':num(latest?.bullish)>num(latest?.bearish)?'Predomina optimismo':'Sentimento equilibrado';
    const previousWeeks=weeks.slice(1).map(aaiiWeekCard).join('');
    return `<section class="dms-aaii" aria-label="AAII Investor Sentiment Survey">
      ${staleNotice}
      <div class="dms-aaii-head">
        <div><span>AAII · RETAIL SENTIMENT</span><strong>${dominant}</strong></div>
        <div class="dms-aaii-spread"><small>Bull–Bear</small><b>${aaiiSpreadText(spread)}</b></div>
      </div>
      <div class="dms-aaii-mix" aria-label="Bullish ${aaiiPct(latest.bullish)}, neutral ${aaiiPct(latest.neutral)}, bearish ${aaiiPct(latest.bearish)}">
        <i class="is-bull" style="width:${num(latest.bullish)??0}%"></i>
        <i class="is-neutral" style="width:${num(latest.neutral)??0}%"></i>
        <i class="is-bear" style="width:${num(latest.bearish)??0}%"></i>
      </div>
      <div class="dms-aaii-legend">
        <span>▲ Bullish <b>${aaiiPct(latest.bullish)}</b></span>
        <span>● Neutral <b>${aaiiPct(latest.neutral)}</b></span>
        <span>▼ Bearish <b>${aaiiPct(latest.bearish)}</b></span>
      </div>
      <div class="dms-aaii-note">Semana de ${esc(aaiiDate(latest.date))}${delta==null?'':` · spread ${aaiiSpreadText(delta)} vs. semana anterior`}</div>
      <details class="dms-aaii-history"${S.aaiiExpanded?' open':''}>
        <summary>Ver semanas anteriores <span>›</span></summary>
        <div class="dms-aaii-history__weeks">${previousWeeks}</div>
      </details>
    </section>`;
  }

  function loadAaii(force=false){
    const now=Date.now();
    if(aaiiRequest) return aaiiRequest;
    if(!force && now-aaiiLastAttempt<AAII_REFRESH_INTERVAL_MS) return Promise.resolve();
    aaiiLastAttempt=now;
    aaiiRequest=(async()=>{
      try{
        const response=await fetch('data/aaii-sentiment.json',{cache:'no-store'});
        if(!response.ok) throw new Error(`AAII ${response.status}`);
        const payload=await response.json();
        if(!Array.isArray(payload?.weeks)||!payload.weeks.length) throw new Error('AAII payload vazio');
        S.aaii=payload;
        render();
      }catch(error){
        // Failed fetch must remain retryable on the next app foreground.
        aaiiLastAttempt=0;
        console.warn('[Vestra] AAII sentiment unavailable',error);
      }finally{aaiiRequest=null;}
    })();
    return aaiiRequest;
  }

  async function loadNyseBreadth(){
    try{
      const response=await fetchWithTimeout(NYSE_BREADTH_PATH);
      if(!response.ok) throw new Error(`NYSE breadth ${response.status}`);
      const payload=await response.json();
      S.nyse=payload;
    }catch(error){
      S.nyse=null;
      console.warn('[Vestra] NYSE advance-decline unavailable',error);
    }
    render();
  }

  function reason(snapshot){
    const drivers=(snapshot?.parts||[]).map(([name,value])=>({name,value})).filter(x=>x.value!=null).sort((a,b)=>b.value-a.value);
    if(!drivers.length) return 'Ainda não há componentes suficientes para explicar a leitura.';
    const best=drivers[0], worst=drivers[drivers.length-1];
    if(best.name===worst.name) return `${best.name} é o principal sinal disponível neste momento.`;
    if(best.value>=60&&worst.value<=40) return `${best.name} está a apoiar o score, enquanto ${worst.name.toLowerCase()} continua a limitar a leitura.`;
    if(best.value>=60) return `${best.name} é atualmente o contributo mais favorável para o barómetro.`;
    if(worst.value<=40) return `${worst.name} é atualmente o principal travão do barómetro.`;
    return 'Os principais componentes estão próximos da zona neutra.';
  }

  function gauge(score,tone){
    const s=clamp(num(score)??50);
    const angle=(180+s*1.8)*Math.PI/180;
    const x=(110+69*Math.cos(angle)).toFixed(1);
    const y=(105+69*Math.sin(angle)).toFixed(1);
    return `<div class="dms-gauge dms-gauge--${tone}">
      <svg viewBox="0 0 220 122" role="img" aria-label="Sentimento do mercado ${s} em 100">
        <path class="dms-arc dms-arc--bear" pathLength="100" d="M30 105 A80 80 0 0 1 190 105"/>
        <path class="dms-arc dms-arc--neutral" pathLength="100" d="M30 105 A80 80 0 0 1 190 105"/>
        <path class="dms-arc dms-arc--bull" pathLength="100" d="M30 105 A80 80 0 0 1 190 105"/>
        <line class="dms-needle" x1="110" y1="105" x2="${x}" y2="${y}"/>
        <circle class="dms-hub" cx="110" cy="105" r="6"/>
      </svg>
    </div>`;
  }

  function metric(value){
    return value==null?'—':Math.round(value);
  }

  function mountPoint(){
    const dashboard=document.getElementById('viewDashboard');
    if(!dashboard) return null;
    const anchor=document.getElementById('dashboardTodayBrief') || document.getElementById('dashboardTodayHeading') || dashboard.querySelector('.card.hero');
    return {dashboard,anchor};
  }

  function cardMarkup(){
    const base=workerBase();
    if(!base) return `<section class="dms-card" id="${CARD_ID}">
      <div class="dms-head"><div><span class="dms-kicker">MARKET SENTIMENT</span><h2>Como está o mercado?</h2><p>O barómetro precisa do Worker Vestra para ler preços e histórico.</p></div></div>
      <div class="dms-empty">Configura o Worker em Mais → Preferências.</div>
      ${cnnMarkup()}
      ${aaiiMarkup()}
    </section>`;

    if(S.loading&&!S.data) return `<section class="dms-card" id="${CARD_ID}">
      <div class="dms-head"><div><span class="dms-kicker">MARKET SENTIMENT</span><h2>Como está o mercado?</h2><p>A combinar tendência, momentum, participação proxy e volatilidade.</p></div></div>
      <div class="dms-loading"><span></span>A calcular leitura…</div>
      ${cnnMarkup()}
      ${aaiiMarkup()}
    </section>`;

    if(!S.data) return `<section class="dms-card" id="${CARD_ID}">
      <div class="dms-head"><div><span class="dms-kicker">MARKET SENTIMENT</span><h2>Como está o mercado?</h2><p>Leitura indisponível neste momento.</p></div><button class="dms-refresh" type="button" data-dms-refresh>↻</button></div>
      <div class="dms-empty">${esc(S.error||'Ainda não existem dados suficientes para calcular o score.')}</div>
      ${cnnMarkup()}
      ${aaiiMarkup()}
    </section>`;

    const current=S.data.current;
    const [label,tone]=labelFor(current.score);
    const vix=current.vol?.current;
    const priceDate=S.data.priceFreshness?.date;
    const priceCoverage=Number(S.data.priceFreshness?.coverage)||0;
    const priceDateText=priceDate?priceDate.split('-').reverse().join('/'):'data indisponível';
    const priceAge=priceDate?Math.floor((Date.now()-Date.parse(priceDate+'T23:59:59Z'))/86400000):null;
    const priceWarning=priceAge!=null&&priceAge>4;
    return `<section class="dms-card" id="${CARD_ID}">
      <div class="dms-head">
        <div><span class="dms-kicker">MARKET SENTIMENT · VESTRA READ</span><h2>Como está o mercado?</h2><p>${esc(reason(current))}</p></div>
        <button class="dms-refresh" type="button" data-dms-refresh aria-label="Atualizar sentimento">↻</button>
      </div>
      <div class="dms-main">
        <div class="dms-score-block">
          <div class="dms-score">${current.score}<small>/100</small></div>
          <div class="dms-label dms-label--${tone}">${label}</div>
          <div class="dms-deltas"><span>${deltaLabel(current.score,S.data.previousDay?.score,'ontem')}</span><span>${deltaLabel(current.score,S.data.previousWeek?.score,'1 semana')}</span></div>
        </div>
        ${gauge(current.score,tone)}
      </div>
      <div class="dms-context" aria-label="Frescura das cotações">Cotações até ${esc(priceDateText)} · ${priceCoverage}/7 fontes${priceWarning?' · Dados antigos':''}</div>
      ${turningMarkup()}
      ${cnnMarkup()}
      ${aaiiMarkup()}
      <button class="dms-detail-toggle" type="button" data-dms-detail-toggle aria-expanded="${S.expanded?'true':'false'}">
        ${S.expanded?'Ocultar detalhe':'Ver como é calculado'} <span aria-hidden="true">${S.expanded?'−':'+'}</span>
      </button>
      <div class="dms-detail"${S.expanded?'':' hidden'}>
        <div class="dms-components">
          <div><span>Tendência</span><strong>${metric(current.trend)}</strong></div>
          <div><span>Momentum</span><strong>${metric(current.momentum)}</strong></div>
          <div><span>Participação proxy</span><strong>${metric(current.participation)}</strong></div>
          <div><span>Volatilidade</span><strong>${metric(current.vol?.score)}</strong></div>
        </div>
        <div class="dms-context">${vix!=null?`VIX ${vix.toFixed(1)} · `:''}universo: ACWI, S&P 500, Nasdaq 100, small caps, desenvolvidos ex-EUA e emergentes.</div>
        <aside class="dms-explainer"><strong>O QUE ESTÁS A VER.</strong><p>Score 0–100 calculado com dados de preço: 35% tendência vs médias 50/200, 30% momentum 1/3 meses, 20% participação proxy destes seis mercados acima das médias e 15% VIX. Não usa breadth real, put/call, credit spreads ou COT enquanto essas fontes não estiverem ligadas de forma robusta.</p></aside>
      </div>
    </section>`;
  }

  function render(){
    ensureStyles();
    const mount=mountPoint();
    if(!mount) return false;
    const html=cardMarkup();
    const shell=document.createElement('div');
    shell.innerHTML=html;
    const next=shell.firstElementChild;
    if(!next) return false;
    const existing=document.getElementById(CARD_ID);
    if(existing) existing.replaceWith(next);
    else if(mount.anchor) mount.anchor.insertAdjacentElement('afterend',next);
    else mount.dashboard.prepend(next);
    try { window.dispatchEvent(new CustomEvent('vestra:dashboard-signal-updated', { detail: { source: 'market-sentiment' } })); } catch (_) {}
    return true;
  }

  function cacheGet(){
    try{
      const row=JSON.parse(localStorage.getItem(CACHE_KEY)||'null');
      const freshness=row?.data?.priceFreshness;
      const age=freshness?.date?Math.floor((Date.now()-Date.parse(freshness.date+'T23:59:59Z'))/86400000):Infinity;
      return row&&Date.now()-Number(row.ts||0)<CACHE_TTL_MS&&freshness?.coverage>=6&&age<=5&&age>=-1&&row.data?row.data:null;
    }catch{return null;}
  }
  function cacheSet(data){
    try{localStorage.setItem(CACHE_KEY,JSON.stringify({ts:Date.now(),data}));}catch{}
  }

  async function fetchWithTimeout(url){
    const controller=typeof AbortController==='function'?new AbortController():null;
    let timer=null;
    try{
      const request=fetch(url,{cache:'no-store',...(controller?{signal:controller.signal}:{})});
      const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{try{controller?.abort();}catch{} reject(new Error('timeout'));},FETCH_TIMEOUT_MS);});
      return await Promise.race([request,timeout]);
    }finally{if(timer!==null) clearTimeout(timer);}
  }

  async function fetchDetail(base,ticker){
    const response=await fetchWithTimeout(`${base}/market?ticker=${encodeURIComponent(ticker)}`);
    if(!response.ok) throw new Error(`market ${ticker} ${response.status}`);
    const data=await response.json();
    if(data?.error) throw new Error(data.error);
    return data;
  }

  async function load(force=false){
    if(S.loading) return;
    if(!force){
      const cached=cacheGet();
      if(cached){S.data=cached;S.error='';render();return;}
    }
    const base=workerBase();
    if(!base){S.data=null;S.error='';render();return;}
    S.loading=true;S.error='';render();
    try{
      const tickers=[...RISK_ASSETS.map(x=>x.ticker),VIX_TICKER,VVIX_TICKER,CORRELATION_TICKER,...CREDIT_TICKERS];
      const settled=await Promise.allSettled(tickers.map(t=>fetchDetail(base,t)));
      const details={};
      settled.forEach((row,i)=>{if(row.status==='fulfilled') details[tickers[i]]=row.value;});
      const freshness=priceFreshness(details);
      const daysOld=freshness.date?Math.floor((Date.now()-Date.parse(freshness.date+'T23:59:59Z'))/86400000):Infinity;
      if(freshness.coverage<6 || daysOld>5 || daysOld< -1) throw new Error('Leitura indisponível: cobertura ou frescura insuficiente das cotações');
      const current=computeSnapshot(details,0);
      if(!current) throw new Error('Dados insuficientes para calcular o score');
      const data={
        current,
        turningInputs:turningPointInputs(details),
        previousDay:computeSnapshot(details,1),
        previousWeek:computeSnapshot(details,5),
        priceFreshness:freshness,
        generatedAt:new Date().toISOString(),
      };
      S.data=data;cacheSet(data);
    }catch(error){
      S.data=null;
      S.error=String(error?.message||'Não foi possível calcular o sentimento.');
    }finally{
      S.loading=false;render();
    }
  }

  function scheduleLoad(){
    if(S.scheduled) return;
    S.scheduled=true;
    const run=()=>{S.scheduled=false;load(false);};
    if(typeof requestIdleCallback==='function') requestIdleCallback(run,{timeout:1400});
    else setTimeout(run,700);
  }

  function boot(){
    ensureStyles();
    S.data=cacheGet();
    render();
    scheduleLoad();
    loadAaii();
    loadCnn();
    loadNyseBreadth();
    window.addEventListener('focus',()=>loadAaii());
    document.addEventListener('visibilitychange',()=>{if(!document.hidden) loadAaii();});
    window.addEventListener('vestra:app-ready',()=>{render();scheduleLoad();});
    document.addEventListener('toggle',event=>{
      const details=event.target?.closest?.('.dms-aaii-history');
      if(details) S.aaiiExpanded=!!details.open;
    },true);
    document.addEventListener('click',event=>{
      if(event.target?.closest?.('[data-dms-turning-toggle]')){S.turningExpanded=!S.turningExpanded;render();return;}
      if(event.target?.closest?.('[data-dms-detail-toggle]')){S.expanded=!S.expanded;render();return;}
      if(event.target?.closest?.('[data-dms-refresh]')){load(true);loadAaii(true);loadCnn();loadNyseBreadth();return;}
      if(event.target?.closest?.('[data-view="dashboard"]')) setTimeout(()=>{render();scheduleLoad();},60);
    });
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();

  window.VestraDashboardMarketSentiment=Object.freeze({
    version:'1.12',
    computeSnapshot,
    turningPointInputs,
    turningPointReading,
    turningProximityScales,
    impliedCorrelationContext,
    nyseBreadthFactor,
    creditStressContext,
    weeklyRsi14,
    priceFreshness,
    labelFor,
    load,
    render,
    riskAssets:RISK_ASSETS,
  });
})();
