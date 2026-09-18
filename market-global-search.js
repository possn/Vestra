/* Vestra Global Market Search v1.8 — global search with local + central learned universe. */
(() => {
  'use strict';

  const txt = v => String(v ?? '').trim();
  const esc = v => txt(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const n = v => { if (v === null || v === undefined || v === '') return null; const x = Number(v); return Number.isFinite(x) ? x : null; };
  const money = (v,c='USD') => n(v)==null?'—':new Intl.NumberFormat('pt-PT',{style:'currency',currency:c||'USD',maximumFractionDigits:2}).format(n(v));
  const pct = v => n(v)==null?'—':`${(Math.abs(n(v))<=1?n(v)*100:n(v)).toFixed(1)}%`;
  const num = v => n(v)==null?'—':new Intl.NumberFormat('pt-PT',{maximumFractionDigits:2}).format(n(v));
  const compact = v => n(v)==null?'—':new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1}).format(n(v));
  const REMOTE_FETCH_TIMEOUT_MS = 12000;
  const SEARCH_FETCH_TIMEOUT_MS = 6000;
  const LEARN_FETCH_TIMEOUT_MS = 8000;

  let timer = null;
  let seq = 0;
  let remoteOpenSeq = 0;
  let enterOpenSeq = 0;
  const cache = new Map();
  const learnedPosted = new Set();

  function workerBase(){
    try { return txt(window.state?.settings?.workerUrl).replace(/\/$/,''); } catch (_) { return ''; }
  }

  function learnedApi(){ return window.VestraLearnedUniverse || null; }
  function validTickerQuery(q){ return /^[A-Z0-9][A-Z0-9.\-]{0,14}$/i.test(txt(q)); }
  function invalidatePendingEnterOpen(){ enterOpenSeq += 1; }

  async function fetchRemoteWithDeadline(url,options={},timeoutMs=REMOTE_FETCH_TIMEOUT_MS,timeoutMessage='Timeout a carregar dados globais.'){
    const controller=typeof AbortController==='function'?new AbortController():null;
    let timeoutId=null;
    try{
      const request=fetch(url,controller?{...options,signal:controller.signal}:options);
      const timeout=new Promise((_,reject)=>{
        timeoutId=setTimeout(()=>{
          try{controller?.abort();}catch(_){}
          reject(new Error(timeoutMessage));
        },timeoutMs);
      });
      return await Promise.race([request,timeout]);
    }finally{
      if(timeoutId!==null)clearTimeout(timeoutId);
    }
  }

  async function learnCentral(row, timeoutMs=LEARN_FETCH_TIMEOUT_MS){
    const ticker = txt(row?.ticker || row?.symbol).toUpperCase();
    const base = workerBase();
    if (!base || !validTickerQuery(ticker) || learnedPosted.has(ticker)) return false;
    learnedPosted.add(ticker);
    try {
      const response = await fetchRemoteWithDeadline(`${base}/learned-universe`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ticker}),
        cache:'no-store',
      }, timeoutMs, 'Timeout a guardar ticker aprendido.');
      if (!response.ok) throw new Error(`learn ${response.status}`);
      return true;
    } catch (_) {
      learnedPosted.delete(ticker);
      return false;
    }
  }

  async function learn(row, source){
    try { await learnedApi()?.upsert?.(row, source); } catch (_) {}
    void learnCentral(row);
    return row;
  }

  async function validateExactTicker(q){
    const ticker = txt(q).toUpperCase();
    const base = workerBase();
    if (!base || !validTickerQuery(ticker)) return [];
    const key = `exact:${ticker}`;
    if (cache.has(key)) return cache.get(key);
    try {
      const r = await fetchRemoteWithDeadline(`${base}/quote?ticker=${encodeURIComponent(ticker)}`, {cache:'no-store'}, SEARCH_FETCH_TIMEOUT_MS, 'Timeout a validar ticker.');
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
      const r = await fetchRemoteWithDeadline(u, {cache:'no-store'}, SEARCH_FETCH_TIMEOUT_MS, 'Timeout na pesquisa global.');
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

  async function openRemoteTicker(ticker){
    invalidatePendingEnterOpen();
    const base=workerBase();
    ticker=txt(ticker).toUpperCase();
    if(!base || !validTickerQuery(ticker)) return false;
    const request=++remoteOpenSeq;

    try{
      await window.VestraMarket?.ensureLoaded?.();
      if(request!==remoteOpenSeq) return false;

      const r=await fetchRemoteWithDeadline(
        `${base}/market?ticker=${encodeURIComponent(ticker)}`,
        {cache:'no-store'},
        REMOTE_FETCH_TIMEOUT_MS,
        'Timeout a construir dossier global.'
      );
      if(request!==remoteOpenSeq) return false;
      if(!r.ok) throw new Error(`HTTP ${r.status}`);

      const d=await r.json();
      if(request!==remoteOpenSeq) return false;
      if(!d || d.error) throw new Error(d?.error||'Sem dados');

      const canonicalTicker=txt(d.ticker||ticker).toUpperCase();
      const stockData={
        ...d,
        ticker:canonicalTicker,
        name:txt(d.name||canonicalTicker),
        currency:txt(d.currency)||'USD',
        quote_type:txt(d.quote_type||'EQUITY').toUpperCase()||'EQUITY',
        _externalLive:true,
        _liveUpdated:true,
      };

      const market=window.VestraMarket;
      const stock=market?.registerExternalStock?.(stockData);
      if(!stock) throw new Error('Runtime de mercado indisponível');

      await learn({
        ticker:stock.ticker,
        name:stock.name,
        exchange:txt(stock.exchange),
        currency:txt(stock.currency),
        quote_type:txt(stock.quote_type||'EQUITY'),
        sector:txt(stock.sector),
        industry:txt(stock.industry),
        country:txt(stock.country),
      },'worker-market');

      if(request!==remoteOpenSeq) return false;
      const nav=window.VestraNavigation;
      if(!nav?.openCompany) throw new Error('Navegação de dossier indisponível');

      const opened=await nav.openCompany(stock.ticker,{origin:'market'});
      if(request!==remoteOpenSeq) return false;
      market?.refreshTickerDossier?.(stock.ticker);
      return opened!==false;
    }catch(e){
      if(request!==remoteOpenSeq) return false;
      const box=document.getElementById('marketSuggestions');
      if(box){
        let error=box.querySelector('.vestra-global-search__error');
        if(!error){
          error=document.createElement('div');
          error.className='vestra-global-search__error';
          box.appendChild(error);
        }
        error.textContent=`Não foi possível abrir ${ticker}: ${txt(e?.message)||'sem dados'}`;
        box.hidden=false;
      }
      return false;
    }
  }

  function style(){
    if(document.getElementById('vestra-global-search-style'))return;
    const link=document.createElement('link');
    link.id='vestra-global-search-style';
    link.rel='stylesheet';
    link.href='market-global-search.css?v=1.0';
    document.head.appendChild(link);
  }

  document.addEventListener('input',e=>{if(e.target?.id==='marketSearch'){invalidatePendingEnterOpen();schedule(e.target.value);}});
  document.addEventListener('focusin',e=>{if(e.target?.id==='marketSearch')schedule(e.target.value);});
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-vestra-global-ticker]');if(!b)return;e.preventDefault();openRemoteTicker(txt(b.dataset.vestraGlobalTicker).toUpperCase());});
  document.addEventListener('keydown',e=>{if(e.key!=='Enter'||e.target?.id!=='marketSearch')return;const input=e.target;const q=txt(input.value).toUpperCase();if(!validTickerQuery(q)||localExactPresent(q))return;const enterRequest=++enterOpenSeq;setTimeout(async()=>{const rows=await validateExactTicker(q);if(enterRequest!==enterOpenSeq||txt(input.value).toUpperCase()!==q)return;if(rows[0])openRemoteTicker(rows[0].ticker);},0);});
  style();
  window.VestraGlobalMarketSearch=Object.freeze({version:'1.8',validateExactTicker,openRemoteTicker,runSearch,learnCentral});
})();