/* Vestra Global Market Search v1.2 — global search with local + central learned universe. */
(() => {
  'use strict';

  const txt = v => String(v ?? '').trim();
  const esc = v => txt(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n = v => { if (v === null || v === undefined || v === '') return null; const x = Number(v); return Number.isFinite(x) ? x : null; };
  const money = (v,c='USD') => n(v)==null?'—':new Intl.NumberFormat('pt-PT',{style:'currency',currency:c||'USD',maximumFractionDigits:2}).format(n(v));
  const pct = v => n(v)==null?'—':`${(Math.abs(n(v))<=1?n(v)*100:n(v)).toFixed(1)}%`;
  const num = v => n(v)==null?'—':new Intl.NumberFormat('pt-PT',{maximumFractionDigits:2}).format(n(v));
  const compact = v => n(v)==null?'—':new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1}).format(n(v));

  let timer = null;
  let seq = 0;
  const cache = new Map();
  const learnedPosted = new Set();

  function workerBase(){
    try { return txt(window.state?.settings?.workerUrl).replace(/\/$/,''); } catch (_) { return ''; }
  }

  function learnedApi(){ return window.VestraLearnedUniverse || null; }
  function validTickerQuery(q){ return /^[A-Z0-9][A-Z0-9.\-]{0,14}$/i.test(txt(q)); }

  async function learnCentral(row){
    const ticker = txt(row?.ticker || row?.symbol).toUpperCase();
    const base = workerBase();
    if (!base || !validTickerQuery(ticker) || learnedPosted.has(ticker)) return false;
    learnedPosted.add(ticker);
    try {
      const response = await fetch(`${base}/learned-universe`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ticker}),
        cache:'no-store',
      });
      if (!response.ok) throw new Error(`learn ${response.status}`);
      return true;
    } catch (_) {
      learnedPosted.delete(ticker);
      return false;
    }
  }

  async function learn(row, source){
    try { await learnedApi()?.upsert?.(row, source); } catch (_) {}
    await learnCentral(row);
    return row;
  }

  async function validateExactTicker(q){
    const ticker = txt(q).toUpperCase();
    const base = workerBase();
    if (!base || !validTickerQuery(ticker)) return [];
    const key = `exact:${ticker}`;
    if (cache.has(key)) return cache.get(key);
    try {
      const r = await fetch(`${base}/quote?ticker=${encodeURIComponent(ticker)}`, {cache:'no-store'});
      if (!r.ok) return [];
      const d = await r.json();
      if (!d || d.error || n(d.price)==null) return [];
      const type = txt(d.quote_type).toUpperCase();
      if (type && !['EQUITY','ETF','MUTUALFUND'].includes(type)) return [];
      const out = [{ticker:txt(d.ticker||ticker).toUpperCase(),name:txt(d.name||ticker),exchange:txt(d.exchange),quote_type:type||'EQUITY',currency:txt(d.currency),price:n(d.price)}];
      cache.set(key,out);
      await learn(out[0],'worker-quote');
      return out;
    } catch (_) { return []; }
  }

  async function yahooNameSearch(q){
    const text = txt(q); if (text.length < 2) return [];
    const key = `name:${text.toLowerCase()}`;
    if (cache.has(key)) return cache.get(key);
    try {
      const u = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(text)}&quotesCount=8&newsCount=0&listsCount=0`;
      const r = await fetch(u, {cache:'no-store'});
      if (!r.ok) return [];
      const d = await r.json();
      const rows = (d?.quotes||[]).filter(x=>['EQUITY','ETF','MUTUALFUND'].includes(txt(x.quoteType).toUpperCase())).map(x=>({
        ticker:txt(x.symbol).toUpperCase(), name:txt(x.longname||x.shortname||x.symbol), exchange:txt(x.exchange||x.exchDisp), quote_type:txt(x.quoteType).toUpperCase(), currency:txt(x.currency)
      })).filter(x=>x.ticker).slice(0,8);
      cache.set(key,rows); return rows;
    } catch (_) { return []; }
  }

  async function learnedSearch(q){
    try {
      const rows = await learnedApi()?.search?.(q,6);
      return (rows||[]).map(r=>({...r,_learned:true}));
    } catch (_) { return []; }
  }

  function localExactPresent(ticker){
    const box = document.getElementById('marketSuggestions');
    if (!box) return false;
    return [...box.querySelectorAll('[data-market-ticker]')].some(el=>txt(el.dataset.marketTicker).toUpperCase()===ticker);
  }

  function renderGlobalSuggestions(q, rows){
    const box = document.getElementById('marketSuggestions');
    if (!box) return;
    box.querySelector('.vestra-global-search')?.remove();
    const filtered = rows.filter((r,i,a)=>a.findIndex(x=>x.ticker===r.ticker)===i).filter(r=>!localExactPresent(r.ticker)).slice(0,6);
    if (!filtered.length) return;
    const hasLearned = filtered.some(r=>r._learned);
    const host = document.createElement('div');
    host.className = 'vestra-global-search';
    host.innerHTML = `<div class="vestra-global-search__label">${hasLearned?'UNIVERSO APRENDIDO + LIVE':'PESQUISA GLOBAL · LIVE'}</div>${filtered.map(r=>`<button type="button" class="vestra-global-search__row" data-vestra-global-ticker="${esc(r.ticker)}"><span><strong>${esc(r.ticker)}</strong><small>${esc(r.name)}</small></span><em>${esc([r.exchange,r.currency,r._learned?'Guardada':''].filter(Boolean).join(' · '))}</em></button>`).join('')}`;
    box.appendChild(host); box.hidden=false;
  }

  async function runSearch(q){
    const current = ++seq;
    const learned = await learnedSearch(q);
    if (current !== seq || txt(document.getElementById('marketSearch')?.value) !== txt(q)) return;
    if (learned.length) renderGlobalSuggestions(q,learned);

    const [exact,names] = await Promise.all([validateExactTicker(q),yahooNameSearch(q)]);
    if (current !== seq || txt(document.getElementById('marketSearch')?.value) !== txt(q)) return;
    renderGlobalSuggestions(q,[...learned,...exact,...names]);
  }

  function schedule(q){
    clearTimeout(timer);
    const text=txt(q); if(!text){document.querySelector('.vestra-global-search')?.remove();return;}
    timer=setTimeout(()=>runSearch(text),160);
  }

  function remoteMetric(label,value){ return `<div class="market-detail-kpi"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`; }

  async function openRemoteTicker(ticker){
    const base=workerBase(); if(!base) return;
    const sh=document.getElementById('marketSheet'), content=document.getElementById('marketSheetContent');
    if(!sh||!content)return;
    sh.dataset.ticker=ticker; sh.dataset.tool='remote-live';
    document.documentElement.classList.add('modal-open'); document.body.classList.add('modal-open');
    sh.hidden=false; sh.setAttribute('aria-hidden','false');
    content.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">DOSSIER LIVE</div><h2>${esc(ticker)}</h2><p>A obter dados globais…</p></div><button class="market-close" data-market-close>×</button></div><div class="market-detail-card"><p>Esta empresa não faz parte do catálogo diário pré-enriquecido. O dossier está a ser construído ao vivo.</p></div>`;
    try{
      const r=await fetch(`${base}/market?ticker=${encodeURIComponent(ticker)}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`HTTP ${r.status}`);
      const d=await r.json(); if(!d||d.error)throw new Error(d?.error||'Sem dados');
      const c=txt(d.currency)||'USD';
      await learn({
        ticker:txt(d.ticker||ticker).toUpperCase(), name:txt(d.name||ticker), exchange:txt(d.exchange), currency:c,
        quote_type:txt(d.quote_type||'EQUITY'), sector:txt(d.sector), industry:txt(d.industry), country:txt(d.country)
      },'worker-market');
      const target=n(d.analyst_price_target_mean); const upside=n(d.analyst_price_target_upside_pct);
      content.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">DOSSIER GLOBAL · LIVE</div><h2>${esc(d.ticker||ticker)}</h2><p>${esc(d.name||'')}</p><span class="market-live-badge">● Live</span></div><button class="market-close" data-market-close>×</button></div>
      <div class="market-detail-card"><h4>Visão rápida</h4><div class="market-detail-grid">${remoteMetric('Preço',money(d.current_price,c))}${remoteMetric('Market cap',compact(d.market_cap))}${remoteMetric('Forward P/E',num(d.forward_pe))}${remoteMetric('P/B',num(d.price_to_book))}${remoteMetric('ROE',pct(d.roe))}${remoteMetric('FCF yield',pct(d.fcf_yield))}</div><p>${esc([d.sector,d.industry,d.country,d.exchange].filter(Boolean).join(' · '))}</p></div>
      <div class="market-detail-card"><h4>Crescimento e rentabilidade</h4><div class="market-detail-grid">${remoteMetric('Receitas',pct(d.revenue_growth))}${remoteMetric('Lucros',pct(d.earnings_growth))}${remoteMetric('Margem operacional',pct(d.operating_margin))}${remoteMetric('Margem líquida',pct(d.profit_margin))}${remoteMetric('Dívida / capital',num(d.debt_to_equity))}${remoteMetric('Current ratio',num(d.current_ratio))}</div></div>
      <div class="market-detail-card"><h4>Valuation e expectativas</h4><div class="market-detail-grid">${remoteMetric('52w máximo',money(d.fifty_two_week_high,c))}${remoteMetric('52w mínimo',money(d.fifty_two_week_low,c))}${remoteMetric('Target analistas',target==null?'—':money(target,c))}${remoteMetric('Upside consenso',upside==null?'—':pct(upside))}</div><p>Não tem ainda Score Vestra pré-calculado. Após validação, fica guardada localmente e no catálogo central aprendido; o próximo pipeline diário promove-a para o universo oficial e passa a poder calcular Score Vestra, peers e valuation completos.</p></div>`;
    }catch(e){
      content.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">DOSSIER GLOBAL</div><h2>${esc(ticker)}</h2><p>Não foi possível carregar este ativo.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-detail-card"><p>${esc(e?.message||'Sem dados')}</p></div>`;
    }
  }

  function style(){
    if(document.getElementById('vestra-global-search-style'))return;
    const s=document.createElement('style');s.id='vestra-global-search-style';
    s.textContent='.vestra-global-search{border-top:1px solid var(--line);padding-top:6px}.vestra-global-search__label{padding:5px 12px 4px;font-size:8px;font-weight:900;letter-spacing:.12em;color:#0b8f8a}.vestra-global-search__row{width:100%;border:0;background:transparent;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;text-align:left;color:inherit}.vestra-global-search__row span{display:grid;gap:2px;min-width:0}.vestra-global-search__row strong{font-size:12px}.vestra-global-search__row small{font-size:10px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.vestra-global-search__row em{font-style:normal;font-size:9px;color:var(--text2);flex:0 0 auto}';document.head.appendChild(s);
  }

  document.addEventListener('input',e=>{if(e.target?.id==='marketSearch')schedule(e.target.value);});
  document.addEventListener('focusin',e=>{if(e.target?.id==='marketSearch')schedule(e.target.value);});
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-vestra-global-ticker]');if(!b)return;e.preventDefault();openRemoteTicker(txt(b.dataset.vestraGlobalTicker).toUpperCase());});
  document.addEventListener('keydown',e=>{if(e.key!=='Enter'||e.target?.id!=='marketSearch')return;const q=txt(e.target.value).toUpperCase();if(!validTickerQuery(q)||localExactPresent(q))return;setTimeout(async()=>{const rows=await validateExactTicker(q);if(rows[0])openRemoteTicker(rows[0].ticker);},0);});
  style();
  window.VestraGlobalMarketSearch=Object.freeze({version:'1.2',validateExactTicker,openRemoteTicker,runSearch,learnCentral});
})();
