/* Vestra Dashboard Market Sentiment v1.0 — transparent, price-derived market barometer. */
(() => {
  'use strict';

  const STYLE_ID='vestraDashboardMarketSentimentStyle';
  const CARD_ID='vestraMarketSentimentCard';
  const CACHE_KEY='vestra-market-sentiment-v1';
  const CACHE_TTL_MS=15*60*1000;
  const FETCH_TIMEOUT_MS=10000;

  const RISK_ASSETS=[
    {ticker:'ACWI',name:'Global',weight:.30},
    {ticker:'SPY',name:'S&P 500',weight:.20},
    {ticker:'QQQ',name:'Nasdaq 100',weight:.15},
    {ticker:'IWM',name:'Small caps',weight:.15},
    {ticker:'EFA',name:'Desenvolvidos ex-EUA',weight:.10},
    {ticker:'EEM',name:'Emergentes',weight:.10},
  ];
  const VIX_TICKER='^VIX';

  const S={loading:false,data:null,error:'',scheduled:false};
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
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
    link.href='dashboard-market-sentiment.css?v=1.0';
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
    if(totalWeight<.6) return null;
    const score=Math.round(parts.reduce((s,x)=>s+x[1]*x[2],0)/totalWeight);
    return {score:clamp(score),trend,momentum,participation,vol,parts};
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
    const hero=dashboard.querySelector('.card.hero');
    return {dashboard,hero};
  }

  function cardMarkup(){
    const base=workerBase();
    if(!base) return `<section class="dms-card" id="${CARD_ID}">
      <div class="dms-head"><div><span class="dms-kicker">MARKET SENTIMENT</span><h2>Como está o mercado?</h2><p>O barómetro precisa do Worker Vestra para ler preços e histórico.</p></div></div>
      <div class="dms-empty">Configura o Worker em Mais → Preferências.</div>
    </section>`;

    if(S.loading&&!S.data) return `<section class="dms-card" id="${CARD_ID}">
      <div class="dms-head"><div><span class="dms-kicker">MARKET SENTIMENT</span><h2>Como está o mercado?</h2><p>A combinar tendência, momentum, participação proxy e volatilidade.</p></div></div>
      <div class="dms-loading"><span></span>A calcular leitura…</div>
    </section>`;

    if(!S.data) return `<section class="dms-card" id="${CARD_ID}">
      <div class="dms-head"><div><span class="dms-kicker">MARKET SENTIMENT</span><h2>Como está o mercado?</h2><p>Leitura indisponível neste momento.</p></div><button class="dms-refresh" type="button" data-dms-refresh>↻</button></div>
      <div class="dms-empty">${esc(S.error||'Ainda não existem dados suficientes para calcular o score.')}</div>
    </section>`;

    const current=S.data.current;
    const [label,tone]=labelFor(current.score);
    const vix=current.vol?.current;
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
      <div class="dms-components">
        <div><span>Tendência</span><strong>${metric(current.trend)}</strong></div>
        <div><span>Momentum</span><strong>${metric(current.momentum)}</strong></div>
        <div><span>Participação proxy</span><strong>${metric(current.participation)}</strong></div>
        <div><span>Volatilidade</span><strong>${metric(current.vol?.score)}</strong></div>
      </div>
      <div class="dms-context">${vix!=null?`VIX ${vix.toFixed(1)} · `:''}universo: ACWI, S&P 500, Nasdaq 100, small caps, desenvolvidos ex-EUA e emergentes.</div>
      <aside class="dms-explainer"><strong>O QUE ESTÁS A VER.</strong><p>Score 0–100 calculado com dados de preço: 35% tendência vs médias 50/200, 30% momentum 1/3 meses, 20% participação proxy destes seis mercados acima das médias e 15% VIX. Não usa breadth real, put/call, credit spreads ou COT enquanto essas fontes não estiverem ligadas de forma robusta.</p></aside>
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
    else if(mount.hero) mount.hero.insertAdjacentElement('afterend',next);
    else mount.dashboard.prepend(next);
    return true;
  }

  function cacheGet(){
    try{
      const row=JSON.parse(localStorage.getItem(CACHE_KEY)||'null');
      return row&&Date.now()-Number(row.ts||0)<CACHE_TTL_MS&&row.data?row.data:null;
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
      const tickers=[...RISK_ASSETS.map(x=>x.ticker),VIX_TICKER];
      const settled=await Promise.allSettled(tickers.map(t=>fetchDetail(base,t)));
      const details={};
      settled.forEach((row,i)=>{if(row.status==='fulfilled') details[tickers[i]]=row.value;});
      const current=computeSnapshot(details,0);
      if(!current) throw new Error('Dados insuficientes para calcular o score');
      const data={
        current,
        previousDay:computeSnapshot(details,1),
        previousWeek:computeSnapshot(details,5),
        generatedAt:new Date().toISOString(),
      };
      S.data=data;cacheSet(data);
    }catch(error){
      S.data=cacheGet();
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
    window.addEventListener('vestra:app-ready',()=>{render();scheduleLoad();});
    document.addEventListener('click',event=>{
      if(event.target?.closest?.('[data-dms-refresh]')){load(true);return;}
      if(event.target?.closest?.('[data-view="dashboard"]')) setTimeout(()=>{render();scheduleLoad();},60);
    });
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();

  window.VestraDashboardMarketSentiment=Object.freeze({
    version:'1.0',
    computeSnapshot,
    labelFor,
    load,
    render,
    riskAssets:RISK_ASSETS,
  });
})();
