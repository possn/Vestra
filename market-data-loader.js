/* Vestra Market Data Loader v2.3 — instant dossier/portfolio opening + background hydration. */
(() => {
  'use strict';

  const originalFetch = window.fetch.bind(window);
  const shardCache = new Map();
  const tickerHydrationCache = new Map();
  let manifestPromise = null;
  let bypassClick = false;

  const txt = v => String(v ?? '').trim();
  const tickerKey = v => txt(v).toUpperCase();
  const LIVE_FIELDS = [
    'current_price','currency','exchange','quote_type','sector','industry','country','business_summary',
    'market_cap','trailing_pe','forward_pe','price_to_book','enterprise_to_ebitda','dividend_yield',
    'roe','roa','revenue_growth','earnings_growth','eps_growth','profit_margin','operating_margin',
    'gross_margin','operating_cash_flow','free_cash_flow','fcf_yield','ebitda','total_debt',
    'cash_and_short_term_investments','net_cash','stockholders_equity','debt_to_equity','current_ratio',
    'quick_ratio','analyst_price_target_mean','analyst_price_target_upside_pct','analyst_strong_buy',
    'analyst_buy','analyst_hold','analyst_sell','analyst_strong_sell','analyst_eps_next_y_growth',
    'analyst_next_earnings_date','fifty_two_week_high','fifty_two_week_low','beta','revenue_latest',
    'net_income_latest','eps_latest','price_history_1y','updated','source','_liveUpdated'
  ];

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

  function mergeHydrated(ref,full,extra={}){
    if(!ref || !full) return ref || full || null;
    const live={};
    if(ref._liveUpdated){
      for(const key of LIVE_FIELDS){
        if(ref[key]!==undefined && ref[key]!==null && ref[key]!=='') live[key]=ref[key];
      }
    }
    Object.assign(ref,full,extra);
    if(Object.keys(live).length) Object.assign(ref,live);
    return ref;
  }

  async function hydrateTickerCore(ticker){
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
      if(ref) return mergeHydrated(ref,full,{_dossierHydrated:true,_dossierHydrationError:''});
      return full;
    }catch(err){
      // Never download the ~54 MB full market file while the user is opening a dossier.
      // The startup index is a valid fallback and keeps navigation responsive on iOS.
      if(ref){
        ref._dossierHydrationError=err?.message||'dossier indisponível';
        return ref;
      }
      return null;
    }
  }

  function hydrateTicker(ticker){
    const key=tickerKey(ticker);
    if(!key) return Promise.resolve(null);
    const ref=resolveIndexStock(key);
    if(ref?._dossierHydrated) return Promise.resolve(ref);
    if(tickerHydrationCache.has(key)) return tickerHydrationCache.get(key);
    const work=hydrateTickerCore(key).finally(()=>tickerHydrationCache.delete(key));
    tickerHydrationCache.set(key,work);
    return work;
  }

  function dossierSheetFor(ticker){
    const sh=document.getElementById('marketSheet');
    if(!sh || sh.hidden || tickerKey(sh.dataset.ticker)!==tickerKey(ticker)) return null;
    return sh;
  }

  function setHydrationBadge(ticker,state){
    const sh=dossierSheetFor(ticker); if(!sh) return;
    const head=sh.querySelector('.market-detail-head > div:first-child'); if(!head) return;
    let badge=head.querySelector('.market-dossier-hydration');
    if(state==='loading'){
      if(!badge){ badge=document.createElement('span'); badge.className='market-live-badge market-dossier-hydration'; head.appendChild(badge); }
      badge.textContent='◌ A carregar detalhe…';
      badge.setAttribute('aria-live','polite');
      return;
    }
    if(!badge) return;
    if(state==='ready'){
      badge.textContent='✓ Dossier completo';
      setTimeout(()=>{ if(badge?.isConnected) badge.remove(); },1400);
    }else{
      badge.textContent='Detalhe parcial';
      setTimeout(()=>{ if(badge?.isConnected) badge.remove(); },1800);
    }
  }

  function dossierSparkSvg(history){
    const arr=(Array.isArray(history)?history:[]).map(x=>typeof x==='number'?Number(x):Number(x?.close??x?.price)).filter(Number.isFinite);
    if(arr.length<2) return '';
    const vals=arr.slice(-120), min=Math.min(...vals), max=Math.max(...vals), range=max-min||1;
    const pts=vals.map((v,i)=>`${(i/(vals.length-1)*100).toFixed(2)},${(92-(v-min)/range*78).toFixed(2)}`).join(' ');
    return `<svg class="market-spark" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Preço 1 ano"><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="2" vector-effect="non-scaling-stroke" style="color:var(--vio)"/></svg>`;
  }

  function refreshOpenDossier(ticker,stock){
    const sh=dossierSheetFor(ticker); if(!sh || !stock) return;
    const scrollTop=sh.scrollTop;
    const content=document.getElementById('marketSheetContent');
    const spark=dossierSparkSvg(stock.price_history_1y);
    if(spark && content){
      const existing=content.querySelector('.market-spark');
      if(existing) existing.outerHTML=spark;
      else content.querySelector('.market-detail-head')?.insertAdjacentHTML('afterend',spark);
    }
    const active=sh.querySelector('.market-tab.is-active');
    if(active) active.click();
    requestAnimationFrame(()=>{ if(!sh.hidden){ sh.scrollTop=scrollTop; } });
    setHydrationBadge(ticker,stock._dossierHydrated?'ready':'partial');
  }

  function hydrateOpenDossier(ticker){
    const key=tickerKey(ticker);
    if(!key) return Promise.resolve(null);
    setHydrationBadge(key,'loading');
    return hydrateTicker(key).then(stock=>{
      refreshOpenDossier(key,stock);
      return stock;
    }).catch(()=>{
      setHydrationBadge(key,'partial');
      return resolveIndexStock(key);
    });
  }

  async function hydratePortfolio(){
    let assets=[];
    try{ assets=Array.isArray(window.state?.assets)?window.state.assets:[]; }catch(_){}
    const tickers=[...new Set(assets.filter(a=>{
      const c=txt(a?.class).toLowerCase();
      return !c.includes('cripto') && (c.includes('ações')||c.includes('acoes')||c.includes('etf')||c.includes('fund'));
    }).map(a=>tickerKey(a?.yahooTicker||a?.ticker||a?.symbol)).filter(Boolean))];
    await Promise.allSettled(tickers.map(hydrateTicker));
  }

  function installApiWrapper(){
    const api=window.VestraMarket;
    if(!api || api.__lazyDossiersInstalled) return false;
    const rawOpen=api.openTicker?.bind(api);
    if(rawOpen){
      api.openTicker=ticker=>{
        const result=rawOpen(ticker);
        hydrateOpenDossier(ticker);
        return result;
      };
    }
    const rawPortfolio=api.openPortfolioAsset?.bind(api);
    if(rawPortfolio){
      api.openPortfolioAsset=asset=>{
        const result=rawPortfolio(asset);
        hydrateTicker(asset?.yahooTicker||asset?.ticker||asset?.symbol).catch(()=>{});
        return result;
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
    try{
      const result=window.VestraMarket?.openTicker?.(tk);
      if(!window.VestraMarket?.__lazyDossiersInstalled) hydrateOpenDossier(tk);
      return Promise.resolve(result).then(()=>true,()=>false);
    }catch(_){ return Promise.resolve(false); }
  }

  // Capture dossier-opening clicks before market.js' bubble listener. The dossier
  // opens immediately; full shard hydration then continues in the background.
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
      // Portfolio navigation must never wait for every company shard. Open first,
      // then hydrate holdings opportunistically in the background.
      bypassClick=true;
      try{ portfolio.click(); } finally { bypassClick=false; }
      hydratePortfolio().catch(()=>{});
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
  window.VestraMarketData={hydrateTicker,hydratePortfolio,loadManifest,openDossier,refreshOpenDossier,hydrateOpenDossier,version:'2.3'};
})();