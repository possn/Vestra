/* Vestra Metals v1.2 — Winston-inspired editorial commodities dashboard + transparent sentiment. */
(() => {
  'use strict';

  const METALS = [
    { key:'gold', name:'Ouro', ticker:'GC=F', unit:'USD/oz', icon:'Au' },
    { key:'silver', name:'Prata', ticker:'SI=F', unit:'USD/oz', icon:'Ag' },
    { key:'copper', name:'Cobre', ticker:'HG=F', unit:'USD/lb', icon:'Cu' },
    { key:'platinum', name:'Platina', ticker:'PL=F', unit:'USD/oz', icon:'Pt' },
    { key:'palladium', name:'Paládio', ticker:'PA=F', unit:'USD/oz', icon:'Pd' },
    { key:'uranium', name:'Urânio', ticker:'UX=F', unit:'USD/lb', icon:'U' },
  ];
  const S = { selected:'gold', period:'3m', prices:{}, details:{}, news:null, loadingPrices:false, loadingDetail:false };
  const CACHE_PRICES='vestra-metals-prices-v1';
  const CACHE_DETAILS='vestra-metals-details-v1';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const x=Number(v);return Number.isFinite(x)?x:null};

  function workerBase(){
    try { return String(typeof state!=='undefined' && state?.settings?.workerUrl || '').trim().replace(/\/$/,''); }
    catch { return ''; }
  }
  function injectStyles(){
    if(document.getElementById('vestraMetalsStyles')) return;
    const link=document.createElement('link');
    link.id='vestraMetalsStyles';
    link.rel='stylesheet';
    link.href='market-metals.css?v=1.2';
    document.head.appendChild(link);
  }
  function injectModeButton(){
    const grid=document.querySelector('.market-mode-grid'); if(!grid || grid.querySelector('[data-market-mode="metals"]')) return;
    const btn=document.createElement('button'); btn.className='market-mode'; btn.dataset.marketMode='metals';
    btn.innerHTML='<span class="market-mode__icon">◇</span><strong>Metais</strong>';
    const funds=grid.querySelector('[data-market-mode="funds"]');
    if(funds?.nextSibling) grid.insertBefore(btn,funds.nextSibling); else grid.appendChild(btn);
  }
  function fmtPrice(v){ const x=num(v); return x==null?'—':new Intl.NumberFormat('pt-PT',{minimumFractionDigits:x<10?2:1,maximumFractionDigits:x<10?3:2}).format(x); }
  function fmtChange(v){ const x=num(v); return x==null?'—':`${x>=0?'+':''}${x.toFixed(2)}%`; }
  function cacheGet(key,maxAge){ try{const x=JSON.parse(localStorage.getItem(key)||'null'); return x&&Date.now()-Number(x.ts||0)<maxAge?x.data:null}catch{return null} }
  function cacheSet(key,data){ try{localStorage.setItem(key,JSON.stringify({ts:Date.now(),data}))}catch{} }

  async function loadPrices(force=false){
    if(S.loadingPrices) return;
    const base=workerBase();
    if(!force){ const c=cacheGet(CACHE_PRICES,5*60*1000); if(c){S.prices=c; return;} }
    if(!base) return;
    S.loadingPrices=true;
    try{
      const tickers=METALS.map(x=>x.ticker).join(',');
      const r=await fetch(`${base}/quotes?tickers=${encodeURIComponent(tickers)}`,{cache:'no-store'});
      if(!r.ok) throw new Error(`quotes ${r.status}`);
      const d=await r.json();
      const out={}; METALS.forEach(m=>{const q=d[m.ticker]; if(q&&!q.error) out[m.key]=q;});
      S.prices=out; cacheSet(CACHE_PRICES,out);
    }catch(e){ console.warn('[Metals] quotes',e); }
    finally{S.loadingPrices=false;}
  }

  async function loadDetail(key,force=false){
    const m=METALS.find(x=>x.key===key); if(!m) return;
    const cached=cacheGet(CACHE_DETAILS,30*60*1000)||{};
    if(!force && cached[key]){S.details={...cached}; return;}
    const base=workerBase(); if(!base) return;
    S.loadingDetail=true; renderCurrent();
    try{
      const r=await fetch(`${base}/market?ticker=${encodeURIComponent(m.ticker)}`,{cache:'no-store'});
      if(!r.ok) throw new Error(`market ${r.status}`);
      const d=await r.json(); if(d?.error) throw new Error(d.error);
      S.details={...cached,[key]:d}; cacheSet(CACHE_DETAILS,S.details);
    }catch(e){ console.warn('[Metals] detail',m.ticker,e); }
    finally{S.loadingDetail=false; renderCurrent();}
  }

  async function loadNews(){
    if(S.news) return;
    try{ const r=await fetch(`data/metals-news.json?ts=${Date.now()}`,{cache:'no-store'}); if(r.ok) S.news=await r.json(); }
    catch(e){ console.warn('[Metals] news',e); }
    renderCurrent();
  }

  function historyFor(detail){
    return (Array.isArray(detail?.price_history_1y)?detail.price_history_1y:[]).map(x=>({date:String(x?.date||x?.timestamp||''),close:num(x?.close)})).filter(x=>x.close!=null);
  }
  function sliceHistory(rows,period){
    const days={ '1m':31,'3m':93,'6m':186,'1y':370 }[period]||93;
    const cutoff=Date.now()-days*86400000;
    const filtered=rows.filter(x=>{const t=new Date(x.date).valueOf(); return Number.isFinite(t)?t>=cutoff:true;});
    return filtered.length>=2?filtered:rows.slice(-Math.min(rows.length,days));
  }
  function chartSvg(rows){
    if(rows.length<2) return '<div class="metals-empty">Histórico ainda indisponível para este contrato.</div>';
    const vals=rows.map(x=>x.close), lo=Math.min(...vals), hi=Math.max(...vals), rg=hi-lo||1;
    const pts=rows.map((x,i)=>`${(i/(rows.length-1)*100).toFixed(2)},${(90-(x.close-lo)/rg*76).toFixed(2)}`).join(' ');
    const area=`0,96 ${pts} 100,96`;
    return `<svg class="metal-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Evolução do preço"><line class="metal-chart-grid" x1="0" y1="20" x2="100" y2="20"/><line class="metal-chart-grid" x1="0" y1="55" x2="100" y2="55"/><line class="metal-chart-grid" x1="0" y1="90" x2="100" y2="90"/><polygon class="metal-chart-area" points="${area}"/><polyline class="metal-chart-line" points="${pts}"/></svg><div class="metal-chart-labels"><span>${fmtPrice(lo)}</span><span>${fmtPrice(hi)}</span></div>`;
  }

  function clamp(v,min=0,max=100){ return Math.max(min,Math.min(max,v)); }
  function avg(rows,count){
    const vals=rows.slice(-count).map(x=>num(x.close)).filter(x=>x!=null);
    return vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;
  }
  function returnPct(rows,count){
    if(rows.length<2) return null;
    const end=num(rows.at(-1)?.close);
    const start=num(rows[Math.max(0,rows.length-count-1)]?.close);
    return end!=null&&start>0?(end/start-1)*100:null;
  }
  function sentimentFor(detail,quote){
    const rows=historyFor(detail);
    const current=num(detail?.current_price??detail?.price??quote?.price??rows.at(-1)?.close);
    if(current==null) return {score:50,label:'Neutral',tone:'neutral',drivers:[],rows};
    const ma20=avg(rows,20), ma50=avg(rows,50);
    const r20=returnPct(rows,20), r60=returnPct(rows,60);
    const day=num(quote?.change_pct);
    const vals=rows.map(x=>num(x.close)).filter(x=>x!=null);
    const low=vals.length?Math.min(...vals):null, high=vals.length?Math.max(...vals):null;
    const rangePos=(low!=null&&high!=null&&high>low)?(current-low)/(high-low):.5;
    let score=50;
    const drivers=[];
    if(ma20!=null){ const d=(current/ma20-1)*100; score+=clamp(d*2,-12,12); drivers.push({name:'Tendência curta',value:d}); }
    if(ma50!=null){ const d=(current/ma50-1)*100; score+=clamp(d*1.4,-12,12); drivers.push({name:'Tendência 50d',value:d}); }
    if(r20!=null){ score+=clamp(r20*.8,-10,10); drivers.push({name:'Momentum 1m',value:r20}); }
    if(r60!=null){ score+=clamp(r60*.45,-8,8); drivers.push({name:'Momentum 3m',value:r60}); }
    score+=clamp((rangePos-.5)*20,-10,10);
    if(day!=null) score+=clamp(day*1.2,-5,5);
    score=Math.round(clamp(score));
    const label=score<=20?'Muito bearish':score<=40?'Bearish':score<60?'Neutral':score<80?'Bullish':'Muito bullish';
    const tone=score<40?'bearish':score>=60?'bullish':'neutral';
    return {score,label,tone,drivers,rows,current,low,high,rangePos,r20,r60,day};
  }
  function sentimentGauge(sentiment){
    const score=clamp(num(sentiment?.score)??50);
    const angle=(180+score*1.8)*Math.PI/180;
    const x=(110+69*Math.cos(angle)).toFixed(1);
    const y=(105+69*Math.sin(angle)).toFixed(1);
    return `<div class="metal-sentiment-gauge metal-sentiment-gauge--${sentiment.tone}">
      <svg viewBox="0 0 220 122" role="img" aria-label="Sentimento ${score} em 100">
        <path class="msg-arc msg-arc--bear" pathLength="100" d="M30 105 A80 80 0 0 1 190 105"/>
        <path class="msg-arc msg-arc--neutral" pathLength="100" d="M30 105 A80 80 0 0 1 190 105"/>
        <path class="msg-arc msg-arc--bull" pathLength="100" d="M30 105 A80 80 0 0 1 190 105"/>
        <line class="msg-needle" x1="110" y1="105" x2="${x}" y2="${y}"/>
        <circle class="msg-hub" cx="110" cy="105" r="6"/>
      </svg>
      <div class="metal-sentiment-scale"><span>Bearish</span><strong>${score}/100 · ${esc(sentiment.label)}</strong><span>Bullish</span></div>
    </div>`;
  }
  function editorialSummary(m,s){
    if(s.current==null) return `Ainda não há dados suficientes para interpretar ${esc(m.name)}.`;
    const bits=[];
    if(s.high!=null&&s.high>0) bits.push(`${((s.current/s.high-1)*100).toFixed(1)}% face ao máximo de 12 meses`);
    if(s.r20!=null) bits.push(`${s.r20>=0?'+':''}${s.r20.toFixed(1)}% no último mês`);
    if(s.r60!=null) bits.push(`${s.r60>=0?'+':''}${s.r60.toFixed(1)}% em três meses`);
    return `${esc(m.name)} está com leitura <strong>${esc(s.label.toLowerCase())}</strong>. ${bits.length?bits.join(' · ')+'.':''}`;
  }
  function driverRows(s){
    const rows=(s.drivers||[]).slice(0,4);
    if(!rows.length) return '<span>Sem componentes suficientes.</span>';
    return rows.map(d=>`<span><b>${esc(d.name)}</b><em class="${d.value>0?'is-positive':d.value<0?'is-negative':''}">${d.value>=0?'+':''}${d.value.toFixed(1)}%</em></span>`).join('');
  }
  function explainer(m){
    const copy={
      gold:'Combina tendência, momentum e posição do ouro no intervalo de 12 meses. Nesta primeira versão não inclui ainda COT, yields reais ou stocks físicos.',
      silver:'Mostra se a prata está a ganhar ou perder força através de tendência, momentum e posição no intervalo anual.',
      copper:'Resume a força cíclica do cobre através do comportamento do preço. Será enriquecido depois com sinais macro/industriais.',
      platinum:'Leitura técnica transparente baseada no comportamento recente do preço e no intervalo anual.',
      palladium:'Leitura técnica transparente baseada no comportamento recente do preço e no intervalo anual.',
      uranium:'Leitura técnica do contrato disponível. O indicador fica neutro quando o histórico é insuficiente.'
    };
    return copy[m.key]||'Leitura baseada nos dados de preço disponíveis.';
  }

  function renderCards(){
    return `<div class="metals-grid">${METALS.map(m=>{const q=S.prices[m.key]||{}; const ch=num(q.change_pct); return `<button type="button" class="metal-card ${S.selected===m.key?'is-active':''}" data-metal-select="${m.key}"><div class="metal-card__top"><span class="metal-card__name">${esc(m.name)}</span><span class="metal-card__symbol">${esc(m.icon)}</span></div><div class="metal-card__price">${fmtPrice(q.price)}</div><div class="metal-card__meta"><span>${esc(m.unit)}</span><span class="metal-change ${ch>0?'is-up':ch<0?'is-down':''}">${fmtChange(ch)}</span></div></button>`;}).join('')}</div>`;
  }
  function renderDetail(){
    const m=METALS.find(x=>x.key===S.selected)||METALS[0], d=S.details[m.key]||{}, q=S.prices[m.key]||{};
    const allRows=historyFor(d), rows=sliceHistory(allRows,S.period);
    const p=num(d.current_price??d.price??q.price), ch=num(q.change_pct);
    const sent=sentimentFor(d,q);
    return `<article class="metal-editorial">
      <header class="metal-editorial__headline">
        <div><div class="metal-editorial__kicker">METALS · VESTRA READ</div><h4>${esc(m.name)} · ${fmtPrice(p)} ${esc(m.unit)}</h4><p>${editorialSummary(m,sent)}</p></div>
        <span class="metal-change ${ch>0?'is-up':ch<0?'is-down':''}">${fmtChange(ch)}</span>
      </header>
      <section class="metal-sentiment-card">
        <div class="metal-section-title"><div><small>BARÓMETRO DE SENTIMENTO</small><h5>Qual é o tom do mercado?</h5></div><span class="metal-sentiment-pill metal-sentiment-pill--${sent.tone}">${esc(sent.label)}</span></div>
        ${sentimentGauge(sent)}
        <div class="metal-driver-grid">${driverRows(sent)}</div>
        <p class="metal-model-note">Modelo Vestra · preço, médias, momentum e posição no range de 12 meses. Não é uma recomendação.</p>
      </section>
      <section class="metal-chart-card">
        <div class="metal-section-title"><div><small>PREÇO</small><h5>${esc(m.name)} nos últimos ${S.period==='1y'?'12 meses':S.period.toUpperCase()}</h5></div></div>
        <div class="metal-periods">${[['1m','1M'],['3m','3M'],['6m','6M'],['1y','1A']].map(([k,l])=>`<button type="button" data-metal-period="${k}" class="${S.period===k?'is-active':''}">${l}</button>`).join('')}</div>
        ${S.loadingDetail?'<div class="metals-empty">A carregar histórico…</div>':chartSvg(rows)}
        <p class="metal-chart-caption">${sent.high!=null&&sent.current!=null?`Preço atual ${fmtPrice(sent.current)} · máximo 12m ${fmtPrice(sent.high)} · mínimo 12m ${fmtPrice(sent.low)}.`:''}</p>
      </section>
      <aside class="metal-explainer"><strong>O QUE ESTÁS A VER.</strong><p>${esc(explainer(m))}</p></aside>
      <div class="metal-source">Preço e histórico: Yahoo Finance via Worker Vestra. Contratos de futuros, não cotações spot.</div>
    </article>`;
  }

  function renderNews(){
    const rows=Array.isArray(S.news?.items)?S.news.items:[]; const selected=S.selected;
    const filtered=rows.filter(x=>!x.metal || x.metal===selected); const use=(filtered.length?filtered:rows).slice(0,8);
    return `<div class="metals-news"><h4>Notícias sobre metais</h4>${use.length?use.map(x=>`<a class="metal-news-row" href="${esc(x.url)}" target="_blank" rel="noopener noreferrer"><strong>${esc(x.title)}</strong><small>${esc([x.source,x.published_at?new Date(x.published_at).toLocaleDateString('pt-PT'):'' ].filter(Boolean).join(' · '))}</small></a>`).join(''):'<div class="metals-empty">Sem notícias recentes no snapshot.</div>'}<div class="metal-source">Headlines agregados periodicamente. Abre a fonte para ler a notícia completa.</div></div>`;
  }
  function renderCurrent(){
    const root=document.getElementById('marketPrimary'); if(!root || root.dataset.metalsActive!=='1') return;
    const base=workerBase();
    root.innerHTML=`<section class="market-section metals-shell"><div class="metals-head"><div><h3>Metais</h3><p>Preços, evolução e notícias de ouro, prata, cobre, platina, paládio e urânio.</p></div><button type="button" class="metals-refresh" data-metal-refresh>↻</button></div>${!base?'<div class="market-empty market-empty--error"><strong>Worker por configurar</strong><br><span>Configura o Worker em Mais → Preferências para preços e gráficos live.</span></div>':''}${renderCards()}${renderDetail()}${renderNews()}</section>`;
  }

  async function renderInto(root){
    injectStyles(); injectModeButton(); if(!root) return;
    root.dataset.metalsActive='1'; renderCurrent();
    await Promise.all([loadPrices(false),loadNews()]); renderCurrent();
    loadDetail(S.selected,false);
  }

  document.addEventListener('click',e=>{
    const m=e.target.closest?.('[data-metal-select]'); if(m){S.selected=m.dataset.metalSelect; renderCurrent(); loadDetail(S.selected,false); return;}
    const p=e.target.closest?.('[data-metal-period]'); if(p){S.period=p.dataset.metalPeriod; renderCurrent(); return;}
    const r=e.target.closest?.('[data-metal-refresh]'); if(r){cacheSet(CACHE_PRICES,{}); loadPrices(true).then(()=>renderCurrent()); loadDetail(S.selected,true); return;}
  });
  document.addEventListener('DOMContentLoaded',()=>{injectStyles();injectModeButton();});
  injectStyles(); injectModeButton();
  window.VestraMetals=Object.freeze({version:'1.2',renderInto,metals:METALS});
})();