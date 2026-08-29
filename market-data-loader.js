/* Vestra Market Data Loader v2.1 — lazy dossier hydration; opening delegated to canonical navigation when available. */
(() => {
  'use strict';

  const originalFetch = window.fetch.bind(window);
  const shardCache = new Map();
  let manifestPromise = null;
  let bypassClick = false;

  const txt = v => String(v ?? '').trim();
  const tickerKey = v => txt(v).toUpperCase();

  async function loadManifest(){
    if(manifestPromise) return manifestPromise;
    manifestPromise=(async()=>{
      const r=await originalFetch('data/dossiers-manifest.json',{cache:'no-store'});
      if(!r.ok) throw new Error(`dossiers-manifest ${r.status}`);
      const d=await r.json();
      return d?.tickers || {};
    })().catch(err=>{ manifestPromise=null; throw err; });
    return manifestPromise;
  }

  async function loadShard(name){
    const key=txt(name).toUpperCase()||'_';
    if(shardCache.has(key)) return shardCache.get(key);
    const work=(async()=>{
      const r=await originalFetch(`data/dossiers/${encodeURIComponent(key)}.json`,{cache:'no-store'});
      if(!r.ok) throw new Error(`dossier shard ${key} ${r.status}`);
      const d=await r.json();
      return d?.stocks || {};
    })().catch(err=>{ shardCache.delete(key); throw err; });
    shardCache.set(key,work);
    return work;
  }

  function resolveIndexStock(ticker){
    const api=window.VestraMarket;
    if(!api?.resolvePortfolioStock) return null;
    const key=tickerKey(ticker);
    try{
      return api.resolvePortfolioStock({ticker:key,yahooTicker:key,symbol:key,class:'Ações'});
    }catch(_){ return null; }
  }

  async function hydrateTicker(ticker){
    const key=tickerKey(ticker);
    if(!key) return null;
    const ref=resolveIndexStock(key);
    if(ref?._dossierHydrated) return ref;

    try{
      let shard=txt(ref?.dossier_shard);
      if(!shard){
        const manifest=await loadManifest();
        shard=txt(manifest[key]);
        if(!shard){
          const base=key.replace(/\.[A-Z]+$/,'');
          const candidate=Object.keys(manifest).find(k=>k.replace(/\.[A-Z]+$/,'')===base);
          if(candidate) shard=txt(manifest[candidate]);
        }
      }
      if(!shard) throw new Error('ticker sem shard');
      const rows=await loadShard(shard);
      let full=rows[key];
      if(!full){
        const base=key.replace(/\.[A-Z]+$/,'');
        const candidate=Object.keys(rows).find(k=>k.replace(/\.[A-Z]+$/,'')===base);
        if(candidate) full=rows[candidate];
      }
      if(!full) throw new Error('ticker ausente no shard');
      if(ref){ Object.assign(ref,full,{_dossierHydrated:true}); return ref; }
      return full;
    }catch(err){
      // Emergency compatibility fallback: only for the requested ticker. This is
      // deliberately not used during normal Market startup.
      try{
        const r=await originalFetch('data/stocks.json?full=1',{cache:'no-store'});
        if(!r.ok) throw err;
        const d=await r.json();
        const rows=Array.isArray(d?.stocks)?d.stocks:[];
        const base=key.replace(/\.[A-Z]+$/,'');
        const full=rows.find(x=>tickerKey(x?.ticker)===key)||rows.find(x=>tickerKey(x?.ticker).replace(/\.[A-Z]+$/,'')===base);
        if(full && ref){ Object.assign(ref,full,{_dossierHydrated:true,_dossierFallback:true}); return ref; }
        return full||ref;
      }catch(_){ return ref; }
    }
  }

  async function hydratePortfolio(){
    let assets=[];
    try{ assets=Array.isArray(window.state?.assets)?window.state.assets:[]; }catch(_){}
    const tickers=[...new Set(assets.filter(a=>{
      const c=txt(a?.class).toLowerCase();
      return !c.includes('cripto') && (c.includes('ações')||c.includes('acoes')||c.includes('etf')||c.includes('fund'));
    }).map(a=>tickerKey(a?.yahooTicker||a?.ticker||a?.symbol)).filter(Boolean))];
    // Shards are cached, so several holdings beginning with the same letter cost
    // only one network request.
    await Promise.allSettled(tickers.map(hydrateTicker));
  }

  function installApiWrapper(){
    const api=window.VestraMarket;
    if(!api || api.__lazyDossiersInstalled) return false;
    const rawOpen=api.openTicker?.bind(api);
    if(rawOpen){
      api.openTicker=async ticker=>{ await hydrateTicker(ticker); return rawOpen(ticker); };
    }
    const rawPortfolio=api.openPortfolioAsset?.bind(api);
    if(rawPortfolio){
      api.openPortfolioAsset=async asset=>{
        await hydrateTicker(asset?.yahooTicker||asset?.ticker||asset?.symbol);
        return rawPortfolio(asset);
      };
    }
    api.hydrateTicker=hydrateTicker;
    api.hydratePortfolio=hydratePortfolio;
    api.__lazyDossiersInstalled=true;
    return true;
  }

  function ensureApiWrapper(){
    if(installApiWrapper()) return;
    let tries=0;
    const id=setInterval(()=>{ if(installApiWrapper()||++tries>80) clearInterval(id); },50);
  }

  function openDossier(ticker,options={}){
    const tk=tickerKey(ticker);
    if(!tk) return Promise.resolve(false);
    const nav=window.VestraNavigation;
    if(nav?.openCompany) return Promise.resolve(nav.openCompany(tk,options));
    return hydrateTicker(tk).then(()=>window.VestraMarket?.openTicker?.(tk)).then(()=>true,()=>false);
  }

  // Capture dossier-opening clicks before market.js' bubble listener. Hydration is
  // owned by the wrapped Market API; origin/return state is owned by VestraNavigation.
  document.addEventListener('click',e=>{
    if(bypassClick) return;
    const row=e.target.closest?.('[data-market-ticker]');
    if(row){
      const ticker=tickerKey(row.dataset.marketTicker);
      if(!ticker) return;
      e.preventDefault(); e.stopImmediatePropagation();
      openDossier(ticker,{sourceNode:row});
      return;
    }

    const jump=e.target.closest?.('[data-decision-jump="ticker"]');
    if(jump?.dataset.decisionValue){
      const ticker=tickerKey(jump.dataset.decisionValue);
      e.preventDefault(); e.stopImmediatePropagation();
      openDossier(ticker,{origin:'market',sourceNode:jump});
      return;
    }

    const portfolio=e.target.closest?.('[data-market-tool="portfolio"]');
    if(portfolio){
      e.preventDefault(); e.stopImmediatePropagation();
      hydratePortfolio().finally(()=>{
        bypassClick=true;
        try{ portfolio.click(); } finally { bypassClick=false; }
      });
    }
  },true);

  document.addEventListener('keydown',e=>{
    if(e.key!=='Enter' || e.target?.id!=='marketSearch') return;
    const ticker=tickerKey(e.target.value);
    if(!ticker) return;
    e.preventDefault(); e.stopImmediatePropagation();
    openDossier(ticker,{origin:'market',sourceNode:e.target});
  },true);

  ensureApiWrapper();
  window.VestraMarketData={hydrateTicker,hydratePortfolio,loadManifest,openDossier,version:'2.1'};
})();