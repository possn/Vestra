/* Vestra Metals v1.0 — lazy commodities dashboard for Market. */
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
    const s=document.createElement('style'); s.id='vestraMetalsStyles';
    s.textContent=`
      .metals-shell{display:grid;gap:14px}.metals-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.metals-head h3{margin:0;font-size:22px}.metals-head p{margin:5px 0 0;color:var(--muted);font-size:13px;line-height:1.45}.metals-refresh{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:9px 12px;font-weight:800;color:var(--ink)}
      .metals-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.metal-card{border:1px solid var(--line);background:var(--card);border-radius:17px;padding:13px;text-align:left;color:var(--ink);min-width:0}.metal-card.is-active{border-color:var(--teal,#178c88);box-shadow:0 0 0 1px color-mix(in srgb,var(--teal,#178c88) 45%,transparent);background:color-mix(in srgb,var(--teal,#178c88) 7%,var(--card))}.metal-card__top{display:flex;justify-content:space-between;gap:8px;align-items:center}.metal-card__symbol{font-weight:900;font-size:12px;color:var(--teal,#178c88);letter-spacing:.06em}.metal-card__name{font-weight:850;font-size:15px}.metal-card__price{font-size:21px;font-weight:900;margin-top:8px;white-space:nowrap}.metal-card__meta{display:flex;justify-content:space-between;gap:6px;color:var(--muted);font-size:11px;margin-top:5px}.metal-change{font-weight:850}.metal-change.is-up{color:#07845b}.metal-change.is-down{color:#b4473d}
      .metal-detail{border:1px solid var(--line);background:var(--card);border-radius:20px;padding:16px}.metal-detail__head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.metal-detail__head h4{margin:0;font-size:19px}.metal-detail__head small{color:var(--muted)}.metal-periods{display:flex;gap:6px;margin:12px 0 10px;overflow:auto}.metal-periods button{border:1px solid var(--line);background:var(--card2);color:var(--muted);border-radius:999px;padding:7px 11px;font-weight:800;white-space:nowrap}.metal-periods button.is-active{background:var(--ink);color:var(--card);border-color:var(--ink)}.metal-chart{height:190px;width:100%;display:block}.metal-chart-grid{stroke:color-mix(in srgb,var(--line) 85%,transparent);stroke-width:.6}.metal-chart-line{fill:none;stroke:var(--teal,#178c88);stroke-width:2.2;vector-effect:non-scaling-stroke}.metal-chart-area{fill:color-mix(in srgb,var(--teal,#178c88) 10%,transparent)}.metal-chart-labels{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;margin-top:5px}.metal-source{color:var(--muted);font-size:11px;line-height:1.45;margin-top:10px}
      .metals-news{border:1px solid var(--line);background:var(--card);border-radius:20px;padding:16px}.metals-news h4{margin:0 0 8px;font-size:18px}.metal-news-row{display:block;padding:11px 0;border-top:1px solid var(--line);text-decoration:none;color:var(--ink)}.metal-news-row:first-of-type{border-top:0}.metal-news-row strong{display:block;font-size:14px;line-height:1.35}.metal-news-row small{display:block;color:var(--muted);font-size:11px;margin-top:4px}.metals-empty{padding:18px;text-align:center;color:var(--muted);font-size:13px}
      @media(min-width:720px){.metals-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.metal-chart{height:230px}}
    `;
    document.head.appendChild(s);
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

  function renderCards(){
    return `<div class="metals-grid">${METALS.map(m=>{const q=S.prices[m.key]||{}; const ch=num(q.change_pct); return `<button type="button" class="metal-card ${S.selected===m.key?'is-active':''}" data-metal-select="${m.key}"><div class="metal-card__top"><span class="metal-card__name">${esc(m.name)}</span><span class="metal-card__symbol">${esc(m.icon)}</span></div><div class="metal-card__price">${fmtPrice(q.price)}</div><div class="metal-card__meta"><span>${esc(m.unit)}</span><span class="metal-change ${ch>0?'is-up':ch<0?'is-down':''}">${fmtChange(ch)}</span></div></button>`;}).join('')}</div>`;
  }
  function renderDetail(){
    const m=METALS.find(x=>x.key===S.selected)||METALS[0], d=S.details[m.key]||{}, q=S.prices[m.key]||{};
    const rows=sliceHistory(historyFor(d),S.period); const p=num(d.current_price??d.price??q.price), ch=num(q.change_pct);
    return `<div class="metal-detail"><div class="metal-detail__head"><div><small>${esc(m.ticker)} · contrato de futuros</small><h4>${esc(m.name)} · ${fmtPrice(p)} ${esc(m.unit)}</h4></div><span class="metal-change ${ch>0?'is-up':ch<0?'is-down':''}">${fmtChange(ch)}</span></div><div class="metal-periods">${[['1m','1M'],['3m','3M'],['6m','6M'],['1y','1A']].map(([k,l])=>`<button type="button" data-metal-period="${k}" class="${S.period===k?'is-active':''}">${l}</button>`).join('')}</div>${S.loadingDetail?'<div class="metals-empty">A carregar histórico…</div>':chartSvg(rows)}<div class="metal-source">Preço e histórico: Yahoo Finance via o Worker do Vestra. São contratos de futuros, não cotações spot. O urânio usa UX=F quando o Yahoo disponibiliza o contrato.</div></div>`;
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
  window.VestraMetals=Object.freeze({version:'1.0',renderInto,metals:METALS});
})();
