/* Vestra Market — integrates Finscanner datasets with progressive disclosure. */
(() => {
  'use strict';

  const M = {
    loaded: false,
    loading: null,
    data: null,
    stocks: [],
    byTicker: new Map(),
    news: null,
    mode: 'discover',
    query: '',
    sector: 'all',
    region: 'all',
    watchlist: new Set(),
    previousSnapshot: null,
    currentSnapshot: null,
    liveLoading: new Set(),
    congressLive: [],
    congressLoaded: false,
    congressLoading: null,
    congressError: ""
  };

  const $m = id => document.getElementById(id);
  const n = v => {
    // Missing fundamentals are not zero. Number(null) and Number('') are 0,
    // which previously made absent Yahoo fields look like real 0 values.
    if (v === null || v === undefined || v === '') return null;
    const x = Number(v);
    return Number.isFinite(x) ? x : null;
  };
  const txt = v => String(v ?? '').trim();
  const esc = v => txt(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct = v => n(v) == null ? '—' : `${(Math.abs(n(v)) <= 1 ? n(v)*100 : n(v)).toFixed(1)}%`;
  const num = v => n(v) == null ? '—' : new Intl.NumberFormat('pt-PT',{maximumFractionDigits:1}).format(n(v));
  const money = (v, c='USD') => n(v) == null ? '—' : new Intl.NumberFormat('pt-PT',{style:'currency',currency:c || 'USD',maximumFractionDigits:2}).format(n(v));
  const compact = v => n(v) == null ? '—' : new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1}).format(n(v));

  function portfolioAssets(){
    try { return (typeof state !== 'undefined' && state && Array.isArray(state.assets)) ? state.assets : []; }
    catch { return []; }
  }
  function researchEligibleAsset(a){
    const cls=txt(a?.class).toLowerCase();
    // Company/fund fundamentals only. Crypto can share symbols with listed companies
    // (e.g. ATOM), so never infer research eligibility from ticker alone.
    if(cls.includes('cripto')) return false;
    return cls.includes('ações') || cls.includes('acoes') || cls.includes('etf') || cls.includes('fund');
  }
  function assetTicker(a){ return txt(a?.yahooTicker||a?.ticker||a?.symbol).toUpperCase(); }
  function portfolioTickers(){
    return new Set(portfolioAssets().filter(researchEligibleAsset).map(assetTicker).filter(Boolean));
  }
  function portfolioValue(a){ return n(a?.value) ?? n(a?.marketValueEUR) ?? 0; }
  function euro(v){ return n(v)==null ? '—' : new Intl.NumberFormat('pt-PT',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(n(v)); }

  function workerBase(){
    try { return txt(typeof state!=='undefined' && state?.settings?.workerUrl).replace(/\/$/,''); } catch { return ''; }
  }
  function compactLiveBadge(s){
    return s?._liveUpdated ? `<span class="market-live-badge">● Live · ${esc(new Intl.DateTimeFormat('pt-PT',{hour:'2-digit',minute:'2-digit'}).format(new Date(s._liveUpdated)))}</span>` : '';
  }
  async function enrichTickerLive(s){
    const base=workerBase(), ticker=txt(s?.ticker).toUpperCase();
    if(!base||!ticker||M.liveLoading.has(ticker)) return;
    M.liveLoading.add(ticker);
    try{
      const r=await fetch(`${base}/market?ticker=${encodeURIComponent(ticker)}`,{cache:'no-store'});
      if(!r.ok) throw new Error(`market ${r.status}`);
      const live=await r.json();
      if(live && !live.error){
        const merge={};
        for(const [k,v] of Object.entries(live)){ if(v!==null && v!==undefined && v!=='') merge[k]=v; }
        Object.assign(s,merge,{_liveUpdated:live.updated||new Date().toISOString()});
        // v2.6 — never rebuild an open dossier when live data arrives.
        // Safari can lose the modal scroll/height when its whole DOM is replaced
        // asynchronously. Keep the open UI frozen; fresh data is used on the next
        // tab interaction or next opening. Only refresh the small Live badge.
        const sh=$m('marketSheet');
        if(sh && !sh.hidden && txt(sh.dataset.ticker).toUpperCase()===ticker){
          const head=sh.querySelector('.market-detail-head');
          let badge=head?.querySelector('.market-live-badge');
          if(!badge && head){
            const info=head.querySelector('.market-detail-head > div:first-child');
            if(info){
              const holder=document.createElement('span');
              holder.innerHTML=compactLiveBadge(s);
              badge=holder.firstElementChild;
              if(badge) info.appendChild(badge);
            }
          } else if(badge){
            const holder=document.createElement('span'); holder.innerHTML=compactLiveBadge(s);
            if(holder.firstElementChild) badge.replaceWith(holder.firstElementChild);
          }
          sh.dataset.liveReady='1';
        }
      }
    }catch(_){ /* dataset local remains the fallback */ }
    finally{ M.liveLoading.delete(ticker); }
  }



  function normalizeCongressLive(x){
    return {
      ticker: txt(x?.ticker).toUpperCase(),
      representative: txt(x?.representative||x?.member||x?.name)||'Membro do Congresso',
      chamber: txt(x?.chamber), state: txt(x?.state), type: txt(x?.type||x?.transaction)||'trade',
      amount: txt(x?.amount||x?.amount_range)||'—',
      transaction_date: txt(x?.transaction_date||x?.date), disclosure_date: txt(x?.disclosure_date||x?.filed_date)
    };
  }

  async function loadCongressLive(ticker=''){
    const tk=txt(ticker).toUpperCase().split('.')[0];
    const cacheKey=`vestra-congress-live-v2:${tk||'GLOBAL'}`;
    const maxAge=15*60*1000;

    // Reuse the global feed for a ticker when possible: one request instead of
    // burning the free API quota with one call per dossier.
    if(tk && M.congressLoaded && M.congressLive.length){
      const fromGlobal=M.congressLive.filter(x=>x.ticker===tk);
      if(fromGlobal.length) return fromGlobal;
    }
    if(!tk && M.congressLoaded) return M.congressLive;
    if(!tk && M.congressLoading) return M.congressLoading;

    const work=(async()=>{
      try{
        // Local cache makes Congress resilient to rate limits / temporary outages.
        try{
          const cached=JSON.parse(localStorage.getItem(cacheKey)||'null');
          if(cached && Array.isArray(cached.trades) && Date.now()-Number(cached.ts||0)<maxAge){
            const trades=cached.trades.map(normalizeCongressLive).filter(x=>x.ticker);
            if(!tk){ M.congressLive=trades; M.congressLoaded=true; M.congressError=''; }
            return trades;
          }
        }catch(_){}

        const from=new Date(Date.now()-120*86400000).toISOString().slice(0,10);
        const direct=`https://www.bargo.ai/free-apis/congress/v1/trades${tk?`/${encodeURIComponent(tk)}`:''}?from=${from}&limit=100`;
        const base=workerBase();
        const fallback=base?`${base}/congress?${tk?`ticker=${encodeURIComponent(tk)}&`:''}limit=100`:'';
        const urls=[direct,fallback].filter(Boolean);

        let lastErr='';
        let trades=[];
        for(const url of urls){
          try{
            const r=await fetch(url,{cache:'no-store',mode:'cors'});
            if(!r.ok){ lastErr=`HTTP ${r.status}`; continue; }
            const d=await r.json();
            trades=(Array.isArray(d)?d:(d?.trades||d?.data||[])).map(normalizeCongressLive).filter(x=>x.ticker);
            if(tk) trades=trades.filter(x=>x.ticker===tk);
            if(trades.length || !tk) break;
          }catch(e){ lastErr=e?.message||String(e); }
        }

        try{ localStorage.setItem(cacheKey,JSON.stringify({ts:Date.now(),trades})); }catch(_){}

        if(tk){
          const s=M.byTicker.get(txt(ticker).toUpperCase()) || [...M.byTicker.values()].find(x=>txt(x.ticker).toUpperCase().split('.')[0]===tk);
          if(s && trades.length) s.congress_trades=trades;
        }else{
          M.congressLive=trades; M.congressLoaded=true; M.congressError=trades.length?'':(lastErr||'Sem trades recentes');
          for(const tr of trades){
            const stock=M.byTicker.get(tr.ticker) || [...M.byTicker.values()].find(x=>txt(x.ticker).toUpperCase().split('.')[0]===tr.ticker);
            if(stock){
              const cur=Array.isArray(stock.congress_trades)?stock.congress_trades:[];
              const key=x=>`${txt(x.transaction_date||x.date)}|${txt(x.representative||x.member||x.name)}|${txt(x.type)}|${txt(x.amount||x.amount_range)}`;
              const seen=new Set(cur.map(key));
              const additions=trades.filter(t=>t.ticker===tr.ticker&&!seen.has(key(t)));
              stock.congress_trades=[...cur,...additions];
            }
          }
        }
        return trades;
      }catch(e){
        if(!tk) M.congressError=e?.message||'Congress feed indisponível';
        return [];
      }
      finally{ if(!tk) M.congressLoading=null; }
    })();
    if(!tk) M.congressLoading=work;
    return work;
  }

  const WATCH_KEY = 'vestra-market-watchlist-v1';
  function loadWatchlist(){
    try { M.watchlist = new Set(JSON.parse(localStorage.getItem(WATCH_KEY)||'[]').map(x=>txt(x).toUpperCase()).filter(Boolean)); }
    catch { M.watchlist = new Set(); }
  }
  function saveWatchlist(){
    try { localStorage.setItem(WATCH_KEY, JSON.stringify([...M.watchlist])); } catch {}
  }
  function isWatched(ticker){ return M.watchlist.has(txt(ticker).toUpperCase()); }
  function inPortfolio(ticker){
    const t=txt(ticker).toUpperCase(); const base=t.replace(/\.[A-Z]+$/,'');
    return [...portfolioTickers()].some(x=>x===t || x.replace(/\.[A-Z]+$/,'')===base);
  }
  function toggleWatch(ticker){
    const t=txt(ticker).toUpperCase(); if(!t) return;
    if(M.watchlist.has(t)) M.watchlist.delete(t); else M.watchlist.add(t);
    saveWatchlist(); if(M.loaded) syncSnapshots(); renderPrimary();
    const sh=$m('marketSheet');
    if(sh && sh.dataset.ticker && sh.dataset.ticker.toUpperCase()===t){
      const s=M.byTicker.get(t); if(s){ const active=sh.querySelector('.market-tab.is-active')?.dataset.detailTab||'overview'; $m('marketSheetContent').innerHTML=detailBase(s); renderDetailTab(s,active); const tab=sh.querySelector(`[data-detail-tab="${active}"]`); if(tab){sh.querySelectorAll('.market-tab').forEach(x=>x.classList.toggle('is-active',x===tab));} }
    }
  }


  const SNAP_LAST_KEY='vestra-market-snapshot-last-v1';
  const SNAP_PREV_KEY='vestra-market-snapshot-prev-v1';
  function snapshotStock(s){
    return {
      score:n(s.score), thesis_direction:txt(s.thesis_direction), thesis_type:txt(s.thesis_type),
      forward_pe_vs_sector_pct:n(s.forward_pe_vs_sector_pct), trailing_pe_vs_sector_pct:n(s.trailing_pe_vs_sector_pct),
      analyst_eps_revisions_up_30d:n(s.analyst_eps_revisions_up_30d)||0, analyst_eps_revisions_down_30d:n(s.analyst_eps_revisions_down_30d)||0,
      analyst_price_target_upside_pct:n(s.analyst_price_target_upside_pct), insider_buy_count_30d:n(s.insider_buy_count_30d)||0,
      insider_sell_count_30d:n(s.insider_sell_count_30d)||0, analyst_next_earnings_date:txt(s.analyst_next_earnings_date), current_price:n(s.current_price)
    };
  }
  function buildSnapshot(){
    const tracked=new Set([...M.watchlist,...portfolioTickers()]);
    const stocks={};
    for(const ticker of tracked){
      const t=txt(ticker).toUpperCase(); const base=t.replace(/\.[A-Z]+$/,'');
      const s=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===base);
      if(s) stocks[txt(s.ticker).toUpperCase()]=snapshotStock(s);
    }
    return {generatedAt:txt(M.data?.generated_at),savedAt:new Date().toISOString(),stocks};
  }
  function syncSnapshots(){
    try{
      const last=JSON.parse(localStorage.getItem(SNAP_LAST_KEY)||'null');
      const prev=JSON.parse(localStorage.getItem(SNAP_PREV_KEY)||'null');
      const current=buildSnapshot();
      if(last && last.generatedAt && current.generatedAt && last.generatedAt!==current.generatedAt){
        localStorage.setItem(SNAP_PREV_KEY,JSON.stringify(last));
        M.previousSnapshot=last;
        localStorage.setItem(SNAP_LAST_KEY,JSON.stringify(current));
      } else if(!last){
        localStorage.setItem(SNAP_LAST_KEY,JSON.stringify(current));
        M.previousSnapshot=prev;
      } else {
        M.previousSnapshot=prev;
        // enrich same-generation snapshot with newly watched/held tickers without changing baseline
        last.stocks={...(last.stocks||{}),...(current.stocks||{})};
        localStorage.setItem(SNAP_LAST_KEY,JSON.stringify(last));
      }
      M.currentSnapshot=current;
    }catch{ M.previousSnapshot=null; M.currentSnapshot=null; }
  }
  function previousFor(s){ return M.previousSnapshot?.stocks?.[txt(s.ticker).toUpperCase()]||null; }
  function daysUntil(v){ if(!v)return null; const d=new Date(v); if(Number.isNaN(d.valueOf()))return null; return Math.ceil((d-Date.now())/86400000); }
  function changeSignals(s){
    const out=[]; const prev=previousFor(s);
    if(prev){
      const ds=n(s.score)!=null&&n(prev.score)!=null?n(s.score)-n(prev.score):null;
      if(ds!=null&&Math.abs(ds)>=1) out.push({tone:ds>0?'up':'down',label:`Score ${ds>0?'+':''}${ds.toFixed(1)}`});
      if(txt(s.thesis_direction)&&txt(prev.thesis_direction)&&txt(s.thesis_direction)!==txt(prev.thesis_direction)) out.push({tone:txt(s.thesis_direction)==='up'?'up':txt(s.thesis_direction)==='down'?'down':'neutral',label:`Tese ${txt(s.thesis_direction_label)||txt(s.thesis_direction)}`});
      const rev=(n(s.analyst_eps_revisions_up_30d)||0)-(n(s.analyst_eps_revisions_down_30d)||0), prevRev=(n(prev.analyst_eps_revisions_up_30d)||0)-(n(prev.analyst_eps_revisions_down_30d)||0);
      if(Math.abs(rev-prevRev)>=2) out.push({tone:rev>prevRev?'up':'down',label:`Revisões EPS ${rev>prevRev?'melhoraram':'pioraram'}`});
      const val=n(s.forward_pe_vs_sector_pct)??n(s.trailing_pe_vs_sector_pct), pval=n(prev.forward_pe_vs_sector_pct)??n(prev.trailing_pe_vs_sector_pct);
      if(val!=null&&pval!=null&&Math.abs(val-pval)>=10) out.push({tone:val<pval?'up':'down',label:`Valuation ${val<pval?'mais favorável':'mais exigente'}`});
      if((n(s.insider_buy_count_30d)||0)>(n(prev.insider_buy_count_30d)||0)) out.push({tone:'up',label:'Novas compras insider'});
      if((n(s.insider_sell_count_30d)||0)>(n(prev.insider_sell_count_30d)||0)) out.push({tone:'down',label:'Novas vendas insider'});
    } else {
      const d7=n(s.thesis_score_delta_7d);
      if(d7!=null&&Math.abs(d7)>=1) out.push({tone:d7>0?'up':'down',label:`Score 7d ${d7>0?'+':''}${d7.toFixed(1)}`});
      if(txt(s.thesis_direction)==='up') out.push({tone:'up',label:'Tese a melhorar'});
      if(txt(s.thesis_direction)==='down') out.push({tone:'down',label:'Tese a piorar'});
      const up=n(s.analyst_eps_revisions_up_30d)||0, down=n(s.analyst_eps_revisions_down_30d)||0;
      if(up-down>=3) out.push({tone:'up',label:'Revisões EPS positivas'}); else if(down-up>=3) out.push({tone:'down',label:'Revisões EPS negativas'});
      if(n(s.insider_buy_count_30d)>0) out.push({tone:'up',label:'Insiders a comprar'});
    }
    const de=daysUntil(s.analyst_next_earnings_date); if(de!=null&&de>=0&&de<=14) out.push({tone:'event',label:`Resultados em ${de}d`});
    return out.slice(0,4);
  }
  function changeBadge(s){
    const c=changeSignals(s)[0]; if(!c)return '';
    return `<span class="market-change market-change--${c.tone}">${c.tone==='up'?'↗':c.tone==='down'?'↘':c.tone==='event'?'◷':'•'} ${esc(c.label)}</span>`;
  }
  function changePanel(s){
    const changes=changeSignals(s); const prev=previousFor(s);
    const label=prev?`Desde ${shortDate(M.previousSnapshot?.generatedAt||M.previousSnapshot?.savedAt)}`:'Sinais recentes';
    return `<div class="market-change-panel"><div class="market-change-panel__head"><div><small>O QUE MUDOU</small><h4>${esc(label)}</h4></div><span>${changes.length?`${changes.length} ${changes.length===1?'alteração':'alterações'}`:'Estável'}</span></div>${changes.length?`<div class="market-change-list">${changes.map(c=>`<div class="market-change-item market-change-item--${c.tone}"><b>${c.tone==='up'?'↗':c.tone==='down'?'↘':c.tone==='event'?'◷':'•'}</b><span>${esc(c.label)}</span></div>`).join('')}</div>`:'<p>Sem mudança material identificada desde a referência disponível.</p>'}</div>`;
  }

  function isFund(s){
    const q = txt(s.quote_type).toUpperCase();
    const name = txt(s.name).toUpperCase();
    return q === 'ETF' || q === 'MUTUALFUND' || /\bETF\b|ISHARES|VANGUARD|XTRACKERS|SPDR|LYXOR|AMUNDI|WISDOMTREE|INVESCO/.test(name);
  }

  function scoreClass(s){
    const x=n(s); return x==null?'market-score--soft':x>=70?'':x>=55?'market-score--soft':'market-score--risk';
  }

  function ageText(){
    const d = M.data?.generated_at ? new Date(M.data.generated_at) : null;
    if (!d || Number.isNaN(d.valueOf())) return '';
    return `Dados ${new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short'}).format(d)}`;
  }

  async function ensureLoaded(){
    if (M.loaded) return;
    if (M.loading) return M.loading;
    M.loading = (async()=>{
      const r = await fetch('data/stocks.json', {cache:'no-store'});
      if(!r.ok) throw new Error(`stocks.json ${r.status}`);
      M.data = await r.json();
      M.stocks = Array.isArray(M.data.stocks) ? M.data.stocks : [];
      M.byTicker = new Map(M.stocks.map(s=>[txt(s.ticker).toUpperCase(),s]));
      syncSnapshots();
      M.loaded = true;
      renderPrimary();
    })().catch(err=>{
      const el=$m('marketPrimary'); if(el) el.innerHTML=`<div class="market-empty market-empty--error"><strong>Mercado indisponível</strong><br><span>Não foi possível carregar os dados agora.</span><br><button class="btn btn--outline btn--sm" data-market-retry style="margin-top:12px">Tentar novamente</button><small class="market-error-detail">${esc(err.message)}</small></div>`;
    }).finally(()=>{M.loading=null});
    return M.loading;
  }

  function bestStocks(){
    return M.stocks.filter(s=>!isFund(s) && n(s.score)!=null && n(s.data_coverage_pct)>=65 && txt(s.zombie)!=='yes')
      .sort((a,b)=>{
        const dir = x => txt(x.thesis_direction)==='up'?5:txt(x.thesis_direction)==='down'?-5:0;
        return (n(b.score)||0)+dir(b)-(n(a.score)||0)-dir(a);
      }).slice(0,7);
  }

  function renderRow(s, meta=''){
    const thesis = txt(s.thesis_type) || txt(s.sector) || 'Sem classificação';
    const sub = meta || [txt(s.sector), thesis].filter(Boolean).join(' · ');
    const held=inPortfolio(s.ticker), watched=isWatched(s.ticker);
    return `<div class="market-row" data-market-ticker="${esc(s.ticker)}">
      <div><div class="market-row__title"><span class="market-row__ticker">${esc(s.ticker)}</span>${held?'<span class="market-held-badge">Carteira</span>':''}<span class="market-row__name">${esc(s.name||'')}</span></div><div class="market-row__meta">${esc(sub)}</div>${(held||watched)?changeBadge(s):''}</div>
      <div class="market-row__end"><button class="market-watch ${watched?'is-active':''}" data-market-watch="${esc(s.ticker)}" aria-label="${watched?'Remover da lista':'Guardar para acompanhar'}" title="${watched?'A acompanhar':'Acompanhar'}">${watched?'★':'☆'}</button><div class="market-score ${scoreClass(s.score)}">${n(s.score)==null?'—':Math.round(n(s.score))}</div></div>
    </div>`;
  }

  function renderDiscover(){
    const sectors = [...new Set(M.stocks.filter(s=>!isFund(s)&&s.sector).map(s=>s.sector))].sort();
    const preferred = ['Technology','Financial Services','Healthcare','Industrials','Consumer Cyclical','Basic Materials'];
    const visibleSectors = preferred.filter(x=>sectors.includes(x));
    for(const x of sectors){ if(visibleSectors.length>=6) break; if(!visibleSectors.includes(x)) visibleSectors.push(x); }
    const moreSectors = sectors.filter(x=>!visibleSectors.includes(x));
    const hiddenActive = M.sector!=='all' && !visibleSectors.includes(M.sector);
    const qs = M.query.toLowerCase();
    let rows = M.stocks.filter(s=>!isFund(s));
    if(qs) rows=rows.filter(s=>`${s.ticker} ${s.name} ${s.sector} ${s.industry}`.toLowerCase().includes(qs));
    else rows=rows.filter(s=>n(s.score)!=null && n(s.data_coverage_pct)>=65 && txt(s.zombie)!=='yes');
    if(M.sector!=='all') rows=rows.filter(s=>s.sector===M.sector);
    if(!qs){
      const dir=x=>txt(x.thesis_direction)==='up'?5:txt(x.thesis_direction)==='down'?-5:0;
      const rank=x=>n(x.opportunity_score)??((n(x.score)||0)+dir(x)); rows.sort((a,b)=>rank(b)-rank(a));
    } else rows.sort((a,b)=>(n(b.score)||0)-(n(a.score)||0));
    rows=rows.slice(0,20);
    return `<section class="market-section market-discover-section"><div class="market-section__head"><div><h3>${qs?'Resultados':'Melhores oportunidades'}</h3><p>${qs?'Pesquisa no universo global':'Ranking estrutural Vestra · score, confiança, moat, capital, QARP e value-trap risk'}</p></div><span class="market-data-age">${ageText()}</span></div>
      <div class="market-sector-grid" role="group" aria-label="Setores">
        <button class="market-chip ${M.sector==='all'?'is-active':''}" data-market-sector="all">Todos</button>
        ${visibleSectors.map(x=>`<button class="market-chip ${M.sector===x?'is-active':''}" data-market-sector="${esc(x)}" title="${esc(x)}">${esc(x)}</button>`).join('')}
        <label class="market-sector-more ${hiddenActive?'is-active':''}"><span>${hiddenActive?esc(M.sector):'Mais'}</span><select data-market-sector-select aria-label="Mais setores"><option value="">Mais setores</option>${moreSectors.map(x=>`<option value="${esc(x)}" ${M.sector===x?'selected':''}>${esc(x)}</option>`).join('')}</select></label>
      </div>
      <div class="market-list">${rows.length?rows.map(s=>renderRow(s)).join(''):'<div class="market-empty market-empty--filters"><strong>Sem resultados neste filtro.</strong><span>Experimenta outro setor ou remove a pesquisa.</span></div>'}</div></section>`;
  }


  function low52Stats(s){
    const hist=Array.isArray(s?.price_history_1y)?s.price_history_1y:[];
    const closes=hist.map(x=>n(x?.close)).filter(x=>x!=null&&x>0);
    const current=n(s?.current_price) ?? (closes.length?closes[closes.length-1]:null);
    if(!closes.length || current==null || current<=0) return null;
    const low=Math.min(...closes);
    const high=Math.max(...closes);
    if(!(low>0)) return null;
    const above=(current/low-1)*100;
    return {low,high,current,above};
  }

  function low52OpportunityRank(s,stats){
    const low=n(s.low52_score), recovery=n(s.recovery_score), quality=n(s.quality_pct), confidence=n(s.confidence_score);
    const rel=n(s.sector_relative_return_1y_pct), upside=n(s.fair_value_upside_pct);
    const risk=txt(s.risk_gate).toLowerCase(), lowStatus=txt(s.low52_status), rec=txt(s.recovery_status);
    let parts=[], weight=0;
    const add=(v,w)=>{ if(v!=null){ parts.push(Math.max(0,Math.min(100,v))*w); weight+=w; } };
    add(low,0.35); add(recovery,0.25); add(quality,0.15); add(confidence,0.05);
    if(upside!=null) add(Math.max(0,Math.min(100,50+upside)),0.10);
    if(rel!=null) add(Math.max(0,Math.min(100,50+rel)),0.10);
    let score=weight?parts.reduce((a,b)=>a+b,0)/weight:50;
    if(lowStatus==='opportunity') score+=7;
    if(lowStatus==='watch') score+=2;
    if(lowStatus==='value_trap_risk') score-=18;
    if(lowStatus==='structural_risk') score-=30;
    if(rec==='confirmed') score+=8;
    else if(rec==='recovering') score+=5;
    else if(rec==='stabilizing') score+=2;
    else if(rec==='bounce_only') score-=7;
    else if(rec==='failed') score-=16;
    if(risk==='high') score-=25; else if(risk==='severe') score-=40;
    const dist=stats?.above; if(dist!=null && dist<=2) score+=2;
    return Math.round(Math.max(0,Math.min(100,score)));
  }

  function renderLows(){
    let rows=M.stocks.filter(s=>!isFund(s)).map(s=>({s,stats:low52Stats(s)}))
      .filter(x=>x.stats && x.stats.above>=-0.5 && x.stats.above<=5)
      .map(x=>({...x,opportunityRank:low52OpportunityRank(x.s,x.stats)}))
      .sort((a,b)=>b.opportunityRank-a.opportunityRank||a.stats.above-b.stats.above);
    const total=rows.length;
    rows=rows.slice(0,30);
    const body=rows.length?rows.map(({s,stats,opportunityRank})=>{
      const currency=txt(s.currency)||'USD';
      const dist=Math.max(0,stats.above);
      const status=txt(s.low52_status), label=txt(s.low52_label)||'Sem classificação', lowScore=n(s.low52_score);
      const cause=txt(s.drawdown_primary_label), trend=txt(s.drawdown_driver_trend);
      const trendText=trend==='improving'?'causa a melhorar':trend==='deteriorating'?'causa a piorar':'';
      const recoveryLabel=txt(s.recovery_label), recoveryScore=n(s.recovery_score);
      const meta=[`Opportunity ${opportunityRank}/100`,`${dist.toFixed(1)}% acima do mínimo`,label,lowScore!=null?`Low52 ${Math.round(lowScore)}/100`:'',cause,trendText,recoveryLabel,recoveryScore!=null?`Recovery ${Math.round(recoveryScore)}/100`:'' ].filter(Boolean).join(' · ');
      return renderRow(s,meta);
    }).join(''):'<div class="market-empty"><strong>Sem empresas até 5% do mínimo de 52 semanas.</strong><br><span>O universo será recalculado quando os dados de mercado forem atualizados.</span></div>';
    return `<section class="market-section"><div class="market-section__head"><div><h3>Mínimos de 52 semanas</h3><p>Até 5% do mínimo, ordenados pelo Opportunity Rank: qualidade + valuation + causa da queda + setor + confirmação de recuperação.</p></div><span class="market-data-age">${total} ${total===1?'empresa':'empresas'}</span></div><div class="market-list">${body}</div></section>`;
  }

  function renderFunds(){
    const qs=M.query.toLowerCase();
    let funds=M.stocks.filter(isFund);
    if(qs) funds=funds.filter(s=>`${s.ticker} ${s.name} ${s.region||''} ${s.sector||''}`.toLowerCase().includes(qs));
    funds=funds.filter(s=>n(s.score)!=null||n(s.expense_ratio)!=null).sort((a,b)=>(n(b.score)||0)-(n(a.score)||0)).slice(0,24);
    return `<section class="market-section"><div class="market-section__head"><div><h3>ETFs</h3><p>Catálogo independente da tua carteira. Abre um fundo para ver custo, score e encaixe.</p></div><span class="market-data-age">${ageText()}</span></div><div class="market-list">${funds.length?funds.map(s=>renderRow(s,[n(s.expense_ratio)!=null?`TER ${pct(s.expense_ratio)}`:'',txt(s.region)].filter(Boolean).join(' · '))).join(''):'<div class="market-empty">Sem ETFs encontrados.</div>'}</div></section>`;
  }

  function smartRank(s){
    const buys=n(s.insider_buy_value_30d)||0, sells=n(s.insider_sell_value_30d)||0;
    const count=n(s.insider_buy_count_30d)||0;
    const congress=Array.isArray(s.congress_trades)?s.congress_trades.length:0;
    return (buys-sells)/100000 + count*3 + congress;
  }

  function renderWatch(){
    const rows=[...M.watchlist].map(t=>M.byTicker.get(t)).filter(Boolean)
      .sort((a,b)=>(n(b.score)||0)-(n(a.score)||0));
    return `<section class="market-section"><div class="market-section__head"><div><h3>A acompanhar</h3><p>Empresas e ETFs guardados neste dispositivo. A carteira mantém-se separada.</p></div><span class="market-data-age">${rows.length} ${rows.length===1?'ativo':'ativos'}</span></div><div class="market-list">${rows.length?rows.map(s=>renderRow(s,[txt(s.thesis_direction_label),n(s.analyst_price_target_upside_pct)!=null?`Target ${pct(s.analyst_price_target_upside_pct)}`:''].filter(Boolean).join(' · '))).join(''):'<div class="market-empty"><strong>A tua lista está vazia.</strong><br>Usa ☆ numa ideia ou num dossier para a guardar aqui.</div>'}</div></section>`;
  }

  function renderSmart(){
    let rows=M.stocks.filter(s=>!isFund(s)&&((n(s.insider_buy_count_30d)||0)>0 || (Array.isArray(s.congress_trades)&&s.congress_trades.length)))
      .sort((a,b)=>smartRank(b)-smartRank(a)).slice(0,20);
    const liveCount=M.congressLive.length;
    const status=liveCount?`Congresso live · ${liveCount}`:(M.congressError?'Congresso indisponível':ageText());
    const empty=M.congressError
      ? `<div class="market-empty"><strong>Não foi possível carregar Congresso.</strong><br><span>${esc(M.congressError)}</span><br><small>Insiders continuam disponíveis. Os trades do Congresso serão tentados novamente.</small></div>`
      : '<div class="market-empty">A carregar atividade recente…</div>';
    return `<section class="market-section"><div class="market-section__head"><div><h3>Smart money</h3><p>Compras de insiders e atividade declarada no Congresso dos EUA</p><p class="market-source-credit">Congresso: <a href="https://www.bargo.ai/free-apis/congress" target="_blank" rel="noopener">Bargo</a> · divulgações STOCK Act</p></div><span class="market-data-age">${status}</span></div><div class="market-list">${rows.map(s=>renderRow(s,`${n(s.insider_buy_count_30d)||0} compras insider · ${Array.isArray(s.congress_trades)?s.congress_trades.length:0} trades Congresso`)).join('')||empty}</div></section>`;
  }


  const SCANNER_STRATEGIES=[
    ['best_opportunities','Best Opportunities','Ranking estrutural com evidência forte'],
    ['qarp','QARP','Qualidade + valuation'],
    ['fallen_angels','Fallen Angels','Preço deprimido, tese intacta'],
    ['lows_intact','Mínimos intactos','52s sem red flags'],
    ['positive_revisions','Revisões +','Expectativas a melhorar'],
    ['insider_accumulation','Insiders','Compras open-market'],
    ['turnarounds','Turnarounds','Execução a recuperar'],
    ['dividend_growers','Dividend growers','Rendimento sustentável']
  ];
  function scannerResult(s,key){ return s?.scanner_results && typeof s.scanner_results==='object' ? s.scanner_results[key] : null; }
  function renderScanner(strategy='best_opportunities'){
    const meta=SCANNER_STRATEGIES.find(x=>x[0]===strategy)||SCANNER_STRATEGIES[0];
    let rows=M.stocks.filter(s=>!isFund(s)&&scannerResult(s,meta[0]))
      .sort((a,b)=>(n(scannerResult(b,meta[0])?.score)||0)-(n(scannerResult(a,meta[0])?.score)||0));
    const total=rows.length; rows=rows.slice(0,30);
    const chips=SCANNER_STRATEGIES.map(([key,label])=>`<button class="market-chip ${key===meta[0]?'is-active':''}" data-scanner-strategy="${key}">${esc(label)}</button>`).join('');
    const body=rows.length?rows.map(s=>{
      const r=scannerResult(s,meta[0])||{}; const reasons=Array.isArray(r.reasons)?r.reasons:[];
      const line=[`Scanner ${Math.round(n(r.score)||0)}/100`,...reasons.slice(0,2)].join(' · ');
      return renderRow(s,line);
    }).join(''):`<div class="market-empty"><strong>Sem candidatos robustos neste momento.</strong><br><span>O filtro prefere não mostrar nada a aceitar empresas com evidência insuficiente ou Risk Gate elevado.</span></div>`;
    return `<div class="market-detail-head"><div><div class="market-kicker">SCANNER VESTRA</div><h2>${esc(meta[1])}</h2><p>${esc(meta[2])}. Estratégias independentes do core score, com filtros de confiança e risco.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-chipbar" style="margin-bottom:12px">${chips}</div><section class="market-section"><div class="market-section__head"><div><h3>Candidatos</h3><p>Ordenados pelo score específico desta estratégia.</p></div><span class="market-data-age">${total} ${total===1?'empresa':'empresas'}</span></div><div class="market-list">${body}</div></section>`;
  }

  function renderPrimary(){
    const root=$m('marketPrimary'); if(!root || !M.loaded) return;
    root.innerHTML = M.mode==='funds'?renderFunds():M.mode==='smart'?renderSmart():M.mode==='watch'?renderWatch():M.mode==='lows'?renderLows():renderDiscover();
  }

  function marketSearchMatches(query, limit=7){
    const q=txt(query).toLowerCase();
    if(!q) return [];
    const scoreMatch=(x)=>{
      const t=txt(x.ticker).toLowerCase(), name=txt(x.name).toLowerCase();
      if(t===q) return 1000;
      if(t.startsWith(q)) return 800 - t.length;
      if(name.startsWith(q)) return 650 - name.length/100;
      if(t.includes(q)) return 500;
      if(name.includes(q)) return 350;
      return 0;
    };
    return M.stocks.map(x=>({x,rank:scoreMatch(x)})).filter(r=>r.rank>0)
      .sort((a,b)=>b.rank-a.rank || (n(b.x.score)||0)-(n(a.x.score)||0))
      .slice(0,limit).map(r=>r.x);
  }

  function hideSearchSuggestions(){
    const box=$m('marketSuggestions'); if(!box)return; box.hidden=true; box.innerHTML='';
  }

  function renderSearchSuggestions(){
    const box=$m('marketSuggestions'); if(!box || !M.loaded)return;
    const q=txt(M.query);
    if(!q){ hideSearchSuggestions(); return; }
    const rows=marketSearchMatches(q,7);
    if(!rows.length){
      box.innerHTML='<div class="market-suggestion-empty">Sem correspondências imediatas</div>';
      box.hidden=false; return;
    }
    box.innerHTML=rows.map(x=>`<button type="button" class="market-suggestion" role="option" data-market-ticker="${esc(x.ticker)}"><span class="market-suggestion__ticker">${esc(x.ticker)}</span><span class="market-suggestion__name">${esc(x.name||'')}</span><span class="market-suggestion__type">${esc(isFund(x)?'ETF/Fundo':x.sector||'Ação')}</span></button>`).join('');
    box.hidden=false;
  }

  function resolvePortfolioStock(asset){
    if(!researchEligibleAsset(asset)) return null;
    const raw=assetTicker(asset); if(!raw) return null;
    if(M.byTicker.has(raw)) return M.byTicker.get(raw);
    const base=raw.replace(/\.[A-Z]+$/,'');
    const exactBase=M.stocks.filter(x=>txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===base);
    if(exactBase.length===1) return exactBase[0];
    return null;
  }

  async function openPortfolioAsset(asset){
    await ensureLoaded();
    const stock=resolvePortfolioStock(asset);
    if(!stock) return false;
    hideSearchSuggestions();
    openTicker(stock.ticker);
    return true;
  }

  function sparkSvg(history){
    const arr=(Array.isArray(history)?history:[]).map(x=>typeof x==='number'?x:n(x.close??x.price)).filter(Number.isFinite);
    if(arr.length<2) return '';
    const vals=arr.slice(-120), min=Math.min(...vals), max=Math.max(...vals), range=max-min||1;
    const pts=vals.map((v,i)=>`${(i/(vals.length-1)*100).toFixed(2)},${(92-(v-min)/range*78).toFixed(2)}`).join(' ');
    return `<svg class="market-spark" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Preço 1 ano"><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="2" vector-effect="non-scaling-stroke" style="color:var(--vio)"/></svg>`;
  }

  function scoreDims(s){
    const mapped=[
      ['Qualidade',s.quality_pct],['Crescimento',s.growth_pct],['Balanço',s.balance_pct],['Cash flow',s.cashflow_pct],
      ['Valuation',s.value_pct],['Execução',s.execution_pct],['Qualidade dos lucros',s.earnings_quality_pct],
      ['Alocação de capital',s.capital_allocation_pct],['Estabilidade',s.stability_pct]
    ];
    return mapped.filter(([,v])=>v!=null);
  }

  function dimRows(s){
    const dims=scoreDims(s);
    return dims.map(([k,v])=>`<div class="market-dim"><div><div class="market-dim__label"><span>${k}</span><strong>${n(v)==null?'—':Math.round(v)}</strong></div><div class="market-bar"><span style="width:${Math.max(0,Math.min(100,n(v)||0))}%"></span></div></div><span></span></div>`).join('');
  }

  function vestraRead(s){
    const score=n(s.score);
    const dims=scoreDims(s);
    const strengths=dims.filter(([,v])=>n(v)!=null&&n(v)>=68).sort((a,b)=>n(b[1])-n(a[1])).slice(0,2).map(([k])=>k);
    const cautions=dims.filter(([,v])=>n(v)!=null&&n(v)<48).sort((a,b)=>n(a[1])-n(b[1])).slice(0,2).map(([k])=>k);
    const direction=txt(s.thesis_direction);
    let label='Acompanhar', cls='is-watch', copy='Perfil intermédio: vale a pena abrir os pilares antes de tirar conclusões.';
    const evidenceConfidence=n(s.confidence_score); const gate=txt(s.risk_gate);
    if(score!=null&&score>=72&&evidenceConfidence!=null&&evidenceConfidence>=60&&!['high','severe'].includes(gate)){label='Sinal forte';cls='';copy='Métricas fortes com evidência suficientemente robusta para justificar investigação aprofundada.';}
    else if(score!=null&&score>=72){label='Sinal quantitativo';cls='is-watch';copy='O score é elevado, mas a confiança dos dados ou o Risk Gate não permite tratar o sinal como forte.';}
    else if(score!=null&&score<52){label='Mais exigente';cls='is-risk';copy='Há fragilidades relevantes nas métricas; o score pede análise adicional antes de qualquer decisão.';}
    if(isFund(s)) copy='Leitura agregada do fundo com foco em custo, qualidade e encaixe — não substitui análise da composição.';
    const signals=[];
    strengths.forEach(x=>signals.push(`<span class="market-signal">↑ ${esc(x)}</span>`));
    cautions.forEach(x=>signals.push(`<span class="market-signal market-signal--warn">! ${esc(x)}</span>`));
    if(direction==='up') signals.push('<span class="market-signal">↗ Tese a melhorar</span>');
    if(direction==='down') signals.push('<span class="market-signal market-signal--warn">↘ Tese a piorar</span>');
    if(txt(s.estimate_signal)==='improving') signals.push('<span class="market-signal">↑ Expectativas a melhorar</span>');
    if(txt(s.estimate_signal)==='deteriorating') signals.push('<span class="market-signal market-signal--warn">↓ Expectativas a piorar</span>');
    if(n(s.insider_buy_count_30d)>0) signals.push('<span class="market-signal market-signal--gold">Insiders a comprar</span>');
    return `<div class="market-verdict"><div class="market-verdict__score ${cls}">${score==null?'—':Math.round(score)}</div><div class="market-verdict__copy"><small>Leitura Vestra</small><strong>${label}</strong><p>${copy}</p>${signals.length?`<div class="market-signal-row">${signals.slice(0,4).join('')}</div>`:''}</div></div>`;
  }

  function shortDate(v){
    if(!v) return '—'; const d=new Date(v); if(Number.isNaN(d.valueOf())) return esc(v);
    return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short',year:'numeric'}).format(d);
  }

  function catalystPanel(s){
    const events=Array.isArray(s.catalyst_events)?s.catalyst_events.slice(0,5):[];
    if(!events.length) return '';
    const icon=e=>e.tone==='risk'?'!':e.tone==='positive'?'↗':e.tone==='event'?'◷':'•';
    const tone=e=>e.tone==='risk'?'down':e.tone==='positive'?'up':e.tone==='event'?'event':'neutral';
    const when=e=>e.date?shortDate(e.date):(e.window?e.window:'Sem data');
    const next=s.catalyst_next_date?`Próximo · ${shortDate(s.catalyst_next_date)}`:`${events.length} sinais`;
    return `<div class="market-detail-card"><div class="market-perspective-head"><div><small>CATALYSTS & RISKS</small><h4>${esc(s.catalyst_summary||'Eventos a acompanhar')}</h4></div><span class="market-data-age">${esc(next)}</span></div><div class="market-change-list">${events.map(e=>`<div class="market-change-item market-change-item--${tone(e)}"><b>${icon(e)}</b><span><strong>${esc(e.label||'Evento')}</strong><small style="display:block;margin-top:2px">${esc(when(e))}${e.evidence?` · ${esc(e.evidence)}`:''}${e.source?` · ${esc(e.source)}`:''}</small></span></div>`).join('')}</div></div>`;
  }




  function recoveryPanel(s){
    const status=txt(s.recovery_status), label=txt(s.recovery_label), score=n(s.recovery_score);
    if(!status || status==='insufficient') return '';
    const r20=n(s.recovery_return_20d_pct), r60=n(s.recovery_return_60d_pct);
    const reasons=Array.isArray(s.recovery_reasons)?s.recovery_reasons:[];
    const tone=(status==='confirmed'||status==='recovering')?'is-positive':(status==='failed'||status==='bounce_only')?'is-risk':'';
    return `<div class="market-detail-card"><div class="market-perspective-head"><div><small>RECOVERY CONFIRMATION</small><h4>${esc(label||'Sem confirmação')}</h4></div><span class="market-data-age ${tone}">${score==null?'—':Math.round(score)+'/100'}</span></div><div class="market-mini-grid"><div><small>Preço 20d</small><strong>${r20==null?'—':`${r20>0?'+':''}${r20.toFixed(1)}%`}</strong></div><div><small>Preço 60d</small><strong>${r60==null?'—':`${r60>0?'+':''}${r60.toFixed(1)}%`}</strong></div><div><small>Confirmação preço</small><strong>${n(s.recovery_price_score)==null?'—':Math.round(n(s.recovery_price_score))+'/100'}</strong></div><div><small>Confirmação fundamental</small><strong>${n(s.recovery_fundamental_score)==null?'—':Math.round(n(s.recovery_fundamental_score))+'/100'}</strong></div></div>${reasons.length?`<p class="market-case-note">${reasons.slice(0,4).map(esc).join(' · ')}</p>`:''}<p class="market-case-note">Confirmação de recuperação combina preço recente e melhoria fundamental; não é sinal de entrada nem altera o Score Vestra.</p></div>`;
  }

  function drawdownPanel(s){
    const items=Array.isArray(s.drawdown_diagnosis)?s.drawdown_diagnosis:[];
    if(!items.length || txt(s.drawdown_diagnosis_status)==='not_material') return '';
    const trendLabel={improving:'a melhorar',deteriorating:'a piorar',stable:'estável'};
    const trendTone={improving:'is-positive',deteriorating:'is-risk',stable:''};
    const primary=items[0]||{};
    const mixed=txt(s.drawdown_diagnosis_status)==='mixed';
    const title=mixed?'Queda com causas mistas':(s.drawdown_primary_label||primary.label||'Causa não identificada');
    const dd=n(s.drawdown_from_high_pct);
    return `<div class="market-detail-card market-drawdown-panel"><div class="market-perspective-head"><div><small>PORQUE CAIU? · DIAGNÓSTICO</small><h4>${esc(title)}</h4></div><span class="market-data-age">${dd==null?'drawdown':`${dd.toFixed(0)}% vs máximo 52s`}</span></div><p class="market-case-note">Diagnóstico por evidência disponível; identifica drivers prováveis, não prova causalidade.</p>${txt(s.sector_relative_drawdown_label)?`<p class="market-case-note"><strong>${esc(s.sector_relative_drawdown_label)}</strong>${n(s.sector_relative_return_1y_pct)!=null?` · ${n(s.sector_relative_return_1y_pct)>0?'+':''}${n(s.sector_relative_return_1y_pct).toFixed(1)} pp vs mediana do setor · ${n(s.sector_relative_peer_count)||0} pares`:''}</p>`:''}<div class="market-drawdown-drivers">${items.slice(0,4).map((d,i)=>`<div class="market-drawdown-driver ${i===0?'is-primary':''}"><div><strong>${esc(d.label||d.key||'Driver')}</strong><small>${(d.evidence||[]).slice(0,2).map(esc).join(' · ')||'Evidência limitada'}</small></div><span><b>${Math.round(n(d.strength)||0)}</b><em class="${trendTone[txt(d.trend)]||''}">${esc(trendLabel[txt(d.trend)]||'estável')}</em></span></div>`).join('')}</div></div>`;
  }

  function investmentCase(s){
    const evidence=Array.isArray(s.thesis_evidence)?s.thesis_evidence.filter(Boolean):[];
    const drivers=Array.isArray(s.thesis_evolution_drivers)?s.thesis_evolution_drivers.filter(Boolean):[];
    const estimateDrivers=Array.isArray(s.earnings_intelligence_drivers)?s.earnings_intelligence_drivers.filter(Boolean):[];
    const risks=Array.isArray(s.thesis_risks)?s.thesis_risks.filter(Boolean):[];
    const dims=scoreDims(s);
    const weak=dims.filter(([,v])=>n(v)!=null&&n(v)<48).sort((a,b)=>n(a[1])-n(b[1])).map(([k,v])=>`${k} ${Math.round(n(v))}/100`);
    const fwdVs=n(s.forward_pe_vs_sector_pct), trailVs=n(s.trailing_pe_vs_sector_pct), evVs=n(s.ev_ebitda_vs_sector_pct);
    const valuationDelta=fwdVs??trailVs??evVs;
    let valuation='Sem leitura relativa suficiente', valuationClass='';
    if(n(s.fair_value_low)!=null&&n(s.fair_value_high)!=null){
      valuation=`Fair value ${money(s.fair_value_low,s.currency)} – ${money(s.fair_value_high,s.currency)} · ${n(s.fair_value_upside_pct)>=0?'+':''}${num(s.fair_value_upside_pct)}% ao centro`;
      valuationClass=txt(s.valuation_signal)==='undervalued'?'is-positive':txt(s.valuation_signal)==='overvalued'?'is-caution':'';
    } else if(valuationDelta!=null){
      if(valuationDelta<=-15){valuation=`Desconto de ${Math.abs(valuationDelta).toFixed(0)}% vs setor`;valuationClass='is-positive';}
      else if(valuationDelta>=20){valuation=`Prémio de ${valuationDelta.toFixed(0)}% vs setor`;valuationClass='is-caution';}
      else {valuation=`Próximo do setor (${valuationDelta>0?'+':''}${valuationDelta.toFixed(0)}%)`;}
    }
    const upside=n(s.analyst_price_target_upside_pct), revUp=n(s.analyst_eps_revisions_up_30d)||0, revDown=n(s.analyst_eps_revisions_down_30d)||0;
    const watch=[];
    if(s.analyst_next_earnings_date) watch.push(`Resultados · ${shortDate(s.analyst_next_earnings_date)}`);
    if(revUp||revDown) watch.push(`Revisões EPS · ${revUp} ↑ / ${revDown} ↓`);
    if(upside!=null) watch.push(`Target consenso · ${pct(upside)}`);
    if(n(s.insider_buy_count_30d)>0||n(s.insider_sell_count_30d)>0) watch.push(`Insiders 30d · ${n(s.insider_buy_count_30d)||0} compras / ${n(s.insider_sell_count_30d)||0} vendas`);
    if(txt(s.estimate_signal)==='improving') watch.push(`Expectativas a melhorar · ${n(s.estimate_momentum_score)==null?'—':Math.round(n(s.estimate_momentum_score))}/100`);
    if(txt(s.estimate_signal)==='deteriorating') watch.push(`Expectativas a deteriorar · ${n(s.estimate_momentum_score)==null?'—':Math.round(n(s.estimate_momentum_score))}/100`);
    if(txt(s.thesis_direction)==='up') watch.push('Tese quantitativa a melhorar');
    if(txt(s.thesis_direction)==='down') watch.push('Tese quantitativa a piorar');
    const why=evidence.length?evidence.slice(0,3):[s.thesis_summary||s.business_summary||'Ainda não existe evidência suficiente para resumir a tese.'];
    const catalystPool=[...estimateDrivers,...drivers];
    const catalysts=catalystPool.length?catalystPool.slice(0,3):[txt(s.thesis_evolution_summary)||'Sem catalisador quantitativo claro identificado nos dados atuais.'];
    const riskItems=[...risks.slice(0,3),...weak.slice(0,Math.max(0,3-risks.length))].slice(0,3);
    if(!riskItems.length) riskItems.push('Sem risco específico suficientemente forte identificado pelo modelo; rever métricas e negócio antes de decidir.');
    const list=arr=>`<ul class="market-case-list">${arr.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
    return `<div class="market-case">
      <div class="market-case__top"><div><small>INVESTMENT CASE</small><h4>${esc(s.thesis_type||'Leitura do ativo')}</h4><p>${esc(s.thesis_summary||s.business_summary||'Síntese ainda limitada pelos dados disponíveis.')}</p></div><span class="market-case__confidence">Confiança ${esc(txt(s.thesis_confidence)||'—')}</span></div>
      <div class="market-case-grid">
        <section><div class="market-case-label"><span>01</span> Porque interessa</div>${list(why)}</section>
        <section><div class="market-case-label"><span>02</span> O que pode correr bem</div>${list(catalysts)}</section>
        <section><div class="market-case-label"><span>03</span> O que pode quebrar a tese</div>${list(riskItems)}</section>
        <section><div class="market-case-label"><span>04</span> Está caro ou barato?</div><div class="market-value-call ${valuationClass}">${esc(valuation)}</div><p class="market-case-note">Leitura relativa; não é um valor intrínseco.</p></section>
      </div>
      <div class="market-watchpoints"><div class="market-case-label"><span>05</span> O que vigiar</div>${watch.length?watch.slice(0,4).map(x=>`<span>${esc(x)}</span>`).join(''):'<p class="market-case-note">Sem evento ou alteração quantitativa relevante identificada.</p>'}</div>
    </div>`;
  }

  function detailBase(s){
    const watched=isWatched(s.ticker), held=inPortfolio(s.ticker);
    return `<div class="market-detail-head"><div><div class="market-kicker">${esc(isFund(s)?'ETF / Fundo':s.sector||'Empresa')}</div><div class="market-title-line"><h2>${esc(s.ticker)}</h2>${held?'<span class="market-held-badge market-held-badge--detail">Na carteira</span>':''}</div><p>${esc(s.name||'')}</p>${compactLiveBadge(s)}</div><div class="market-detail-actions"><button class="market-watch market-watch--detail ${watched?'is-active':''}" data-market-watch="${esc(s.ticker)}" aria-label="${watched?'Remover da lista':'Guardar para acompanhar'}">${watched?'★':'☆'}</button><button class="market-close" data-market-close>×</button></div></div>
      ${sparkSvg(s.price_history_1y)}
      ${vestraRead(s)}
      <div class="market-metrics"><div class="market-metric"><small>Score Vestra</small><strong>${n(s.score)==null?'—':Math.round(s.score)}/100</strong></div><div class="market-metric"><small>Preço</small><strong>${money(s.current_price,s.currency)}</strong></div><div class="market-metric"><small>Forward P/E</small><strong>${num(s.forward_pe)}</strong></div><div class="market-metric"><small>ROE</small><strong>${pct(s.roe)}</strong></div><div class="market-metric"><small>Receita YoY</small><strong>${pct(s.revenue_growth)}</strong></div><div class="market-metric"><small>FCF yield</small><strong>${pct(s.fcf_yield)}</strong></div></div>
      <div class="market-tabs" role="tablist" aria-label="Dossier"><button class="market-tab is-active" data-detail-tab="overview">Resumo</button><button class="market-tab" data-detail-tab="perspective">Perspetiva</button><button class="market-tab" data-detail-tab="growth">Growth</button><button class="market-tab" data-detail-tab="valuation">Valuation</button><button class="market-tab" data-detail-tab="earnings">Resultados</button><button class="market-tab" data-detail-tab="financials">Financeiro</button><button class="market-tab" data-detail-tab="smart">Smart</button><button class="market-tab" data-detail-tab="news">Notícias</button></div><div id="marketDetailBody"></div>`;
  }

  function renderDetailTab(s,tab){
    const body=$m('marketDetailBody'); if(!body) return;
    if(tab==='overview') body.innerHTML=`${changePanel(s)}${recoveryPanel(s)}${drawdownPanel(s)}${catalystPanel(s)}${investmentCase(s)}<details class="market-detail-disclosure"><summary>Ver pilares e detalhe quantitativo</summary><div class="market-detail-card"><h4>Pilares</h4>${dimRows(s)}</div>${Array.isArray(s.thesis_risks)&&s.thesis_risks.length?`<div class="market-detail-card"><h4>Riscos adicionais</h4><ul>${s.thesis_risks.slice(0,6).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}</details>`;
    if(tab==='perspective') {
      const buys=(n(s.analyst_strong_buy)||0)+(n(s.analyst_buy)||0), holds=n(s.analyst_hold)||0, sells=(n(s.analyst_sell)||0)+(n(s.analyst_strong_sell)||0);
      const revUp=n(s.analyst_eps_revisions_up_30d)||0, revDown=n(s.analyst_eps_revisions_down_30d)||0;
      body.innerHTML=`<div class="market-detail-card market-perspective-card"><div class="market-perspective-head"><div><small>CONSENSO</small><h4>O que o mercado espera</h4></div><span class="market-consensus ${buys>sells?'is-positive':sells>buys?'is-negative':''}">${buys>sells?'Viés positivo':sells>buys?'Viés cauteloso':'Neutro'}</span></div><div class="market-metrics"><div class="market-metric"><small>Target médio</small><strong>${money(s.analyst_price_target_mean,s.currency)}</strong></div><div class="market-metric"><small>Upside target</small><strong>${pct(s.analyst_price_target_upside_pct)}</strong></div><div class="market-metric"><small>Próx. earnings</small><strong>${shortDate(s.analyst_next_earnings_date)}</strong></div><div class="market-metric"><small>EPS próximo ano</small><strong>${pct(s.analyst_eps_next_y_growth)}</strong></div><div class="market-metric"><small>Rev. EPS 30d</small><strong>${revUp} ↑ · ${revDown} ↓</strong></div><div class="market-metric"><small>Última surpresa</small><strong>${pct(s.analyst_latest_eps_surprise_pct)}</strong></div></div></div><div class="market-detail-card"><h4>Analistas</h4><div class="market-consensus-bar"><span class="is-buy" style="flex:${Math.max(0,buys)}"></span><span class="is-hold" style="flex:${Math.max(0,holds)}"></span><span class="is-sell" style="flex:${Math.max(0,sells)}"></span></div><div class="market-consensus-legend"><span>${buys} Comprar</span><span>${holds} Manter</span><span>${sells} Vender</span></div><p style="margin-top:10px">Estimativas são contexto, não recomendação. Dá mais peso à direção das revisões e à execução real do negócio do que ao target isolado.</p></div>`;
    }
    if(tab==='growth') body.innerHTML=`<div class="market-detail-card"><h4>Crescimento e resultados</h4><div class="market-metrics"><div class="market-metric"><small>Receita YoY</small><strong>${pct(s.revenue_yoy_latest??s.revenue_growth)}</strong></div><div class="market-metric"><small>Lucro YoY</small><strong>${pct(s.net_income_yoy_latest??s.earnings_growth)}</strong></div><div class="market-metric"><small>EPS YoY</small><strong>${pct(s.eps_yoy_latest??s.eps_growth)}</strong></div><div class="market-metric"><small>Margem líquida</small><strong>${pct(s.net_margin_latest??s.profit_margin)}</strong></div><div class="market-metric"><small>ROCE proxy</small><strong>${pct(s.roce_proxy)}</strong></div><div class="market-metric"><small>FCF</small><strong>${compact(s.free_cash_flow)}</strong></div></div></div>`;
    if(tab==='valuation') {
      const methods=Array.isArray(s.valuation_methods)?s.valuation_methods:[];
      const signalMap={undervalued:'Margem potencial',fair:'Próximo do fair value',overvalued:'Acima do fair value',uncertain:'Não acionável',insufficient:'Dados insuficientes'};
      body.innerHTML=`<div class="market-detail-card"><div class="market-perspective-head"><div><small>FAIR VALUE VESTRA</small><h4>${n(s.fair_value_low)==null?'Sem faixa robusta':`${money(s.fair_value_low,s.currency)} – ${money(s.fair_value_high,s.currency)}`}</h4></div><span class="market-consensus ${txt(s.valuation_signal)==='undervalued'?'is-positive':txt(s.valuation_signal)==='overvalued'?'is-negative':''}">${esc(signalMap[txt(s.valuation_signal)]||'—')}</span></div><div class="market-metrics"><div class="market-metric"><small>Fair value central</small><strong>${money(s.fair_value_mid,s.currency)}</strong></div><div class="market-metric"><small>Upside/downside</small><strong>${n(s.fair_value_upside_pct)==null?'—':`${n(s.fair_value_upside_pct)>=0?'+':''}${num(s.fair_value_upside_pct)}%`}</strong></div><div class="market-metric"><small>Margem segurança</small><strong>${n(s.margin_of_safety_pct)==null?'—':`${n(s.margin_of_safety_pct)>=0?'+':''}${num(s.margin_of_safety_pct)}%`}</strong></div><div class="market-metric"><small>Confiança valuation</small><strong>${esc(txt(s.valuation_confidence)||'—')}</strong></div><div class="market-metric"><small>Modelo</small><strong>${esc(txt(s.valuation_model)||txt(s.score_model)||'—')}</strong></div><div class="market-metric"><small>Métodos</small><strong>${methods.length}</strong></div></div><p>${esc(s.valuation_note||'Faixa peer-relative; não é target de analistas.')}</p>${methods.length?`<div class="market-watchpoints">${methods.slice(0,4).map(x=>`<span>${esc(x.method)} · ${money(x.fair_value,s.currency)}</span>`).join('')}</div>`:''}</div><div class="market-detail-card"><h4>Múltiplos</h4><div class="market-metrics"><div class="market-metric"><small>P/E</small><strong>${num(s.trailing_pe)}</strong></div><div class="market-metric"><small>Forward P/E</small><strong>${num(s.forward_pe)}</strong></div><div class="market-metric"><small>P/B</small><strong>${num(s.price_to_book)}</strong></div><div class="market-metric"><small>EV/EBITDA</small><strong>${num(s.enterprise_to_ebitda)}</strong></div><div class="market-metric"><small>vs sector P/E</small><strong>${pct(s.trailing_pe_vs_sector_pct)}</strong></div><div class="market-metric"><small>FCF yield</small><strong>${pct(s.fcf_yield)}</strong></div></div></div>`;
    }
    if(tab==='earnings') {
      const hist=Array.isArray(s.analyst_earnings_history_4q)?s.analyst_earnings_history_4q.slice(0,4):[];
      const estimateLabel={improving:'Expectativas a melhorar',deteriorating:'Expectativas a piorar',neutral:'Expectativas neutras',insufficient:'Cobertura insuficiente'}[txt(s.estimate_signal)]||'Cobertura insuficiente';
      const estimateCls=txt(s.estimate_signal)==='improving'?'is-positive':txt(s.estimate_signal)==='deteriorating'?'is-negative':'';
      const eDrivers=Array.isArray(s.earnings_intelligence_drivers)?s.earnings_intelligence_drivers:[];
      body.innerHTML=`<div class="market-detail-card market-perspective-card"><div class="market-perspective-head"><div><small>EXPECTATION MOMENTUM</small><h4>${estimateLabel}</h4></div><span class="market-consensus ${estimateCls}">${n(s.estimate_momentum_score)==null?'—':Math.round(n(s.estimate_momentum_score))+'/100'}</span></div><div class="market-metrics"><div class="market-metric"><small>Momentum</small><strong>${n(s.estimate_momentum_score)==null?'—':Math.round(n(s.estimate_momentum_score))+'/100'}</strong></div><div class="market-metric"><small>Breadth revisões</small><strong>${n(s.estimate_revision_breadth_pct)==null?'—':`${n(s.estimate_revision_breadth_pct)>=0?'+':''}${num(s.estimate_revision_breadth_pct)}%`}</strong></div><div class="market-metric"><small>Score revisões</small><strong>${n(s.estimate_revision_score)==null?'—':Math.round(n(s.estimate_revision_score))+'/100'}</strong></div><div class="market-metric"><small>Score surpresas</small><strong>${n(s.earnings_surprise_score)==null?'—':Math.round(n(s.earnings_surprise_score))+'/100'}</strong></div><div class="market-metric"><small>Confiança</small><strong>${esc(txt(s.estimate_confidence)||'—')}</strong></div><div class="market-metric"><small>Risco evento</small><strong>${esc(txt(s.earnings_event_risk)||'—')}</strong></div></div>${eDrivers.length?`<div class="market-watchpoints">${eDrivers.slice(0,5).map(x=>`<span>${esc(x)}</span>`).join('')}</div>`:''}<p>Overlay de expectativas; não altera diretamente o Score Vestra.</p></div><div class="market-detail-card"><h4>Resultados e catalisadores</h4><div class="market-metrics"><div class="market-metric"><small>Próx. resultados</small><strong>${shortDate(s.analyst_next_earnings_date)}</strong></div><div class="market-metric"><small>Dias até earnings</small><strong>${n(s.analyst_days_to_earnings)==null?'—':Math.round(n(s.analyst_days_to_earnings))}</strong></div><div class="market-metric"><small>Última surpresa EPS</small><strong>${pct(s.analyst_latest_eps_surprise_pct)}</strong></div><div class="market-metric"><small>Beats 4T</small><strong>${n(s.analyst_earnings_beats_4q)==null?'—':Math.round(n(s.analyst_earnings_beats_4q))}</strong></div><div class="market-metric"><small>Misses 4T</small><strong>${n(s.analyst_earnings_misses_4q)==null?'—':Math.round(n(s.analyst_earnings_misses_4q))}</strong></div><div class="market-metric"><small>Surpresa média 4T</small><strong>${pct(s.analyst_earnings_avg_surprise_4q)}</strong></div></div>${hist.length?`<div class="market-earnings-list">${hist.map(x=>`<div><span>${shortDate(x.date||x.earnings_date)}</span><strong>${pct(x.surprise_pct??x.eps_surprise_pct)}</strong></div>`).join('')}</div>`:''}</div>`;
    }
    if(tab==='financials') body.innerHTML=`<div class="market-detail-card"><h4>Saúde financeira</h4><div class="market-metrics"><div class="market-metric"><small>Margem bruta</small><strong>${pct(s.gross_margin)}</strong></div><div class="market-metric"><small>Margem operacional</small><strong>${pct(s.operating_margin)}</strong></div><div class="market-metric"><small>Margem líquida</small><strong>${pct(s.profit_margin)}</strong></div><div class="market-metric"><small>Debt / Equity</small><strong>${num(s.debt_to_equity)}</strong></div><div class="market-metric"><small>Current ratio</small><strong>${num(s.current_ratio)}</strong></div><div class="market-metric"><small>Quick ratio</small><strong>${num(s.quick_ratio)}</strong></div><div class="market-metric"><small>Cash flow operacional</small><strong>${compact(s.operating_cash_flow)}</strong></div><div class="market-metric"><small>Free cash flow</small><strong>${compact(s.free_cash_flow)}</strong></div><div class="market-metric"><small>Net cash / dívida</small><strong>${compact(s.net_cash)}</strong></div></div></div><div class="market-detail-card"><h4>Qualidade dos lucros</h4><div class="market-metrics"><div class="market-metric"><small>Score qualidade</small><strong>${n(s.earnings_quality_pct)==null?'—':Math.round(n(s.earnings_quality_pct))+'/100'}</strong></div><div class="market-metric"><small>Conversão caixa/lucro</small><strong>${n(s.cash_conversion_ratio)==null?'—':num(s.cash_conversion_ratio)+'×'}</strong></div><div class="market-metric"><small>Accrual ratio</small><strong>${pct(s.accrual_ratio)}</strong></div><div class="market-metric"><small>Margem FCF</small><strong>${pct(s.fcf_margin)}</strong></div></div><p style="margin-top:10px">Quanto maior a conversão de lucro em caixa e menor o accrual ratio, menor a dependência de resultados puramente contabilísticos.</p></div><div class="market-detail-card"><h4>Alocação de capital</h4><div class="market-metrics"><div class="market-metric"><small>Score alocação</small><strong>${n(s.capital_allocation_pct)==null?'—':Math.round(n(s.capital_allocation_pct))+'/100'}</strong></div><div class="market-metric"><small>Diluição YoY</small><strong>${pct(s.diluted_shares_yoy)}</strong></div><div class="market-metric"><small>Buybacks último T</small><strong>${compact(s.repurchases_last_quarter)}</strong></div><div class="market-metric"><small>ROCE proxy</small><strong>${pct(s.roce_proxy)}</strong></div><div class="market-metric"><small>Cobertura dividendo/FCF</small><strong>${n(s.dividend_fcf_coverage)==null?'—':num(s.dividend_fcf_coverage)+'×'}</strong></div></div></div><div class="market-detail-card"><h4>Qualidade dos dados</h4><div class="market-metrics"><div class="market-metric"><small>Cobertura</small><strong>${n(s.data_coverage_pct)==null?'—':Math.round(n(s.data_coverage_pct))+'%'}</strong></div><div class="market-metric"><small>Confiança</small><strong>${esc(txt(s.data_confidence)||'—')}</strong></div><div class="market-metric"><small>Modelo</small><strong>${esc(txt(s.score_model)||'general')}</strong></div></div><p style="margin-top:10px">O score só usa métricas disponíveis; valores ausentes não são tratados como zero. A confiança mede cobertura, não certeza do investimento.</p>${Array.isArray(s.data_sources)&&s.data_sources.length?`<p class="market-case-note" style="margin-top:8px">Fontes: ${s.data_sources.map(esc).join(' · ')}</p>`:''}${s.identity_source?`<p class="market-case-note" style="margin-top:6px">Identidade: ${esc(s.identity_source)}${s.isin?' · ISIN '+esc(s.isin):''}${s.lei?' · LEI '+esc(s.lei):''}</p>`:''}</div>`;
    if(tab==='smart') {
      const ins=Array.isArray(s.insider_transactions)?s.insider_transactions.slice(0,8):[];
      const con=Array.isArray(s.congress_trades)?s.congress_trades.slice(0,8):[];
      body.innerHTML=`<div class="market-detail-card"><h4>Insiders · 30 dias</h4><p>${n(s.insider_buy_count_30d)||0} compras (${money(s.insider_buy_value_30d,'USD')}) · ${n(s.insider_sell_count_30d)||0} vendas (${money(s.insider_sell_value_30d,'USD')})</p>${ins.length?`<ul>${ins.map(x=>`<li>${esc(x.name||x.insider||'Insider')} · ${esc(x.transaction_type||x.type||'')} · ${money(x.value||x.transaction_value,'USD')}</li>`).join('')}</ul>`:''}</div><div class="market-detail-card"><h4>Congresso</h4>${con.length?`<ul>${con.map(x=>`<li>${esc(x.representative||x.member||x.name||'')} · ${esc(x.type||x.transaction||'')} · ${esc(x.amount||x.amount_range||'—')}</li>`).join('')}</ul>`:'<p id="marketCongressEmpty">A verificar divulgações recentes…</p>'}</div>`;
      if(!con.length) loadCongressLive(s.ticker).then(trades=>{
        if(!$m('marketSheet')?.hidden && txt($m('marketSheet')?.dataset.ticker).toUpperCase()===txt(s.ticker).toUpperCase() && $m('marketCongressEmpty')){
          if(trades.length) renderDetailTab(s,'smart'); else $m('marketCongressEmpty').textContent='Sem operações recentes registadas.';
        }
      });
    }
    if(tab==='news') loadNewsFor(s);
  }

  async function loadNewsFor(s){
    const body=$m('marketDetailBody'); if(!body) return;
    body.innerHTML='<div class="market-loader"><span></span><div>A carregar notícias…</div></div>';
    try{
      if(!M.news){ const r=await fetch('data/news.json',{cache:'no-store'}); M.news=await r.json(); }
      const rawItems=M.news?.tickers?.[s.ticker]||[];
      const nameTokens=txt(s.name).toLowerCase().match(/[a-z0-9]{3,}/g)||[];
      const baseTicker=txt(s.ticker).toLowerCase().split('.')[0];
      const items=rawItems.filter(x=>{ const h=txt(x.title).toLowerCase(); return nameTokens.some(t=>h.includes(t)) || (baseTicker.length>=3 && new RegExp(`(^|[^a-z0-9])${baseTicker.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}([^a-z0-9]|$)`,'i').test(h)); });
      body.innerHTML=`<div class="market-detail-card"><h4>Notícias de ${esc(s.name||s.ticker)}</h4>${items.length?items.slice(0,10).map(x=>`<div class="market-news-item"><a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.title)}</a><small>${esc(x.source||'')} · ${esc(x.published||'')}</small></div>`).join(''):'<p>Sem notícias recentes confirmadas para este ativo.</p>'}</div>`;
    }catch{ body.innerHTML='<div class="market-empty">Não foi possível carregar notícias.</div>'; }
  }

  function sheetPanel(){ return $m('marketSheet')||null; }
  function scrollDossierTop(){
    const panel=sheetPanel(); if(!panel) return;
    panel.scrollTo ? panel.scrollTo({top:0,left:0,behavior:'auto'}) : (panel.scrollTop=0);
  }
  function resetDossierViewport(){
    const panel=sheetPanel(); if(!panel) return;
    panel.scrollTop=0; panel.scrollLeft=0;
    // One delayed reset after layout is enough; repeated RAF writes can fight iOS momentum.
    setTimeout(()=>{ if(!$m('marketSheet')?.hidden){ panel.scrollTop=0; panel.scrollLeft=0; } }, 35);
  }
  function refreshActiveTabFromLive(){
    const sh=$m('marketSheet'); if(!sh || sh.hidden || !sh.dataset.ticker || sh.dataset.liveReady!=='1') return;
    const s=M.byTicker.get(sh.dataset.ticker.toUpperCase()); if(!s) return;
    sh.dataset.liveReady='0';
    const active=sh.querySelector('.market-tab.is-active')?.dataset.detailTab||'overview';
    renderDetailTab(s,active);
  }

  function openTicker(ticker){
    const s=M.byTicker.get(txt(ticker).toUpperCase()); if(!s) return;
    hideSearchSuggestions();
    try{ window.scrollTo({left:0,top:window.scrollY,behavior:'auto'}); }catch(_){ window.scrollTo(0,window.scrollY); }
    const sh=$m('marketSheet'), content=$m('marketSheetContent'); if(!sh||!content)return;
    // Fully close/reset the previous modal state before constructing a new dossier.
    sh.hidden=true; sh.setAttribute('aria-hidden','true'); sh.dataset.liveReady='0';
    try{
      const html=detailBase(s);
      content.innerHTML=html;
      sh.dataset.ticker=s.ticker;
      renderDetailTab(s,'overview');
    }catch(err){
      console.error('Vestra dossier render',err);
      content.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">DOSSIER</div><h2>${esc(s.ticker||'Ativo')}</h2><p>${esc(s.name||'')}</p></div><button class="market-close" data-market-close>×</button></div><div class="market-detail-card"><h4>Não foi possível apresentar este dossier</h4><p>Os dados deste ativo têm um formato inesperado. Fecha e tenta novamente.</p></div>`;
      sh.dataset.ticker=s.ticker;
    }
    document.documentElement.classList.add('modal-open');
    document.body.classList.add('modal-open');
    sh.hidden=false; sh.setAttribute('aria-hidden','false');
    resetDossierViewport();
    enrichTickerLive(s);
  }
  function closeSheet(){
    const sh=$m('marketSheet'); if(!sh)return;
    const returnView=txt(sh.dataset.returnView);
    sh.hidden=true; sh.setAttribute('aria-hidden','true'); sh.dataset.liveReady='0'; sh.dataset.tool=''; sh.dataset.returnView='';
    document.documentElement.classList.remove('modal-open'); document.body.classList.remove('modal-open');
    const panel=sheetPanel(); if(panel){panel.scrollTop=0;panel.scrollLeft=0;}
    if(returnView==='assets' && typeof setView==='function') setView('assets');
  }

  function portfolioConviction(s){
    const score=n(s?.score), conf=n(s?.confidence_score), est=n(s?.estimate_momentum_score);
    const valMap={undervalued:85,fair:65,overvalued:25,uncertain:40,insufficient:45};
    const val=valMap[txt(s?.valuation_signal)] ?? 50;
    const parts=[];
    if(score!=null) parts.push([score,.55]);
    if(conf!=null) parts.push([conf,.20]);
    if(est!=null) parts.push([est,.10]);
    parts.push([val,.15]);
    if(!parts.length) return null;
    let x=parts.reduce((a,[v,w])=>a+v*w,0)/parts.reduce((a,[,w])=>a+w,0);
    if(txt(s?.thesis_direction)==='up') x+=4;
    if(txt(s?.thesis_direction)==='down') x-=7;
    if(txt(s?.estimate_signal)==='deteriorating') x-=7;
    const gate=txt(s?.risk_gate);
    if(gate==='watch') x=Math.min(x,64);
    if(gate==='high') x=Math.min(x,49);
    if(gate==='severe') x=Math.min(x,35);
    return Math.max(0,Math.min(100,x));
  }

  function holdingSymbol(h){
    return txt(h?.symbol||h?.ticker||h?.holdingSymbol||h?.holding_symbol).toUpperCase().replace(/\.[A-Z]+$/,'');
  }
  function holdingWeight(h){
    let w=n(h?.weight??h?.holdingPercent??h?.holding_percent??h?.percent??h?.percentage);
    if(w==null) return null;
    if(Math.abs(w)<=1) w*=100;
    return w;
  }

  function indirectExposurePct(stock, etfs){
    const symbol=txt(stock?.ticker).toUpperCase().replace(/\.[A-Z]+$/,'');
    if(!symbol) return 0;
    let exposure=0;
    for(const e of etfs||[]){
      const portfolioWeight=n(e.portfolioPct)||0;
      for(const h of (e.stock?.top_holdings||[])){
        if(holdingSymbol(h)!==symbol) continue;
        const hw=holdingWeight(h);
        if(hw!=null) exposure += portfolioWeight*(hw/100);
      }
    }
    return exposure;
  }

  function portfolioFit(r, sectorRows, analysed, etfs){
    const positionPct=analysed>0?r.value/analysed*100:0;
    const sector=txt(r.stock?.sector)||'Sem setor';
    const sectorPct=sectorRows.find(x=>x.sector===sector)?.pct||0;
    const indirectPct=isFund(r.stock)?0:indirectExposurePct(r.stock,etfs);
    const flags=[];
    if(positionPct>=15) flags.push(`posição ${positionPct.toFixed(0)}%`);
    else if(positionPct>=10) flags.push(`posição já relevante ${positionPct.toFixed(0)}%`);
    if(sectorPct>=35) flags.push(`setor concentrado ${sectorPct.toFixed(0)}%`);
    else if(sectorPct>=28) flags.push(`setor já elevado ${sectorPct.toFixed(0)}%`);
    if(indirectPct>=2) flags.push(`+${indirectPct.toFixed(1)}% indireto via ETFs`);
    let fit='balanced';
    if(positionPct>=15||sectorPct>=35||indirectPct>=4) fit='concentrated';
    else if(positionPct>=10||sectorPct>=28||indirectPct>=2) fit='watch';
    return {positionPct,sectorPct,indirectPct,fit,flags};
  }

  function portfolioAction(stock, alternativesByTicker, context){
    const conviction=portfolioConviction(stock);
    const gate=txt(stock?.risk_gate);
    const valuation=txt(stock?.valuation_signal);
    const thesis=txt(stock?.thesis_direction);
    const estimates=txt(stock?.estimate_signal);
    const conf=n(stock?.confidence_score);
    const alt=alternativesByTicker?.get?.(txt(stock?.ticker).toUpperCase())||null;
    const ctx=context||{};
    const reasons=[];
    if(gate==='severe'||gate==='high') reasons.push(`Risk Gate ${gate}`);
    if(thesis==='down') reasons.push('tese a deteriorar');
    if(estimates==='deteriorating') reasons.push('expectativas a piorar');
    if(valuation==='overvalued') reasons.push('valuation exigente');
    if(valuation==='undervalued') reasons.push('margem de segurança');
    if(thesis==='up') reasons.push('tese a melhorar');
    if(estimates==='improving') reasons.push('expectativas a melhorar');
    if(conf!=null&&conf<60) reasons.push('confiança limitada');
    if(ctx.indirectPct>=2) reasons.push(`overlap indireto ${ctx.indirectPct.toFixed(1)}%`);
    if(ctx.positionPct>=10) reasons.push(`peso ${ctx.positionPct.toFixed(0)}%`);
    if(ctx.sectorPct>=28) reasons.push(`setor ${ctx.sectorPct.toFixed(0)}%`);
    if(alt && alt.portfolioFit!=='worse' && (gate==='high'||gate==='severe'||(conviction!=null&&conviction<50))) {
      const fitNote=alt.portfolioFit==='better'?' · melhora diversificação':'';
      return {key:'replace',label:'Substituir',tone:'risk',reason:`${reasons[0]||'convicção fraca'} · alternativa ${alt.to.ticker} superior${fitNote}`};
    }
    if(gate==='high'||gate==='severe'||thesis==='down'||estimates==='deteriorating'||(conviction!=null&&conviction<50)) return {key:'review',label:'Rever',tone:'risk',reason:reasons.slice(0,2).join(' · ')||'convicção baixa'};
    if(conviction!=null&&conviction>=70&&conf!=null&&conf>=60&&!['overvalued','uncertain'].includes(valuation)) {
      if(ctx.fit==='concentrated') return {key:'hold',label:'Manter',tone:'neutral',reason:`boa tese · não reforçar por ${ctx.flags?.[0]||'concentração'}`};
      return {key:'reinforce',label:'Reforçar',tone:'positive',reason:reasons.slice(0,2).join(' · ')||'convicção elevada'};
    }
    return {key:'hold',label:'Manter',tone:'neutral',reason:reasons.slice(0,2).join(' · ')||'tese sem alteração material'};
  }

  const PORTFOLIO_TARGETS_KEY='vestra_portfolio_targets_v1';
  function defaultPortfolioTargets(){ return {maxPosition:10,maxSector:25,maxFactor:45,maxCurrency:70,maxRegion:70,overlap:'reduce',tilt:'balanced'}; }
  function loadPortfolioTargets(){
    try{ const raw=JSON.parse(localStorage.getItem(PORTFOLIO_TARGETS_KEY)||'{}'); return {...defaultPortfolioTargets(),...raw}; }
    catch{return defaultPortfolioTargets();}
  }
  function savePortfolioTargets(t){ try{ localStorage.setItem(PORTFOLIO_TARGETS_KEY,JSON.stringify(t)); }catch{} return t; }
  function portfolioTiltBonus(stock,tilt){
    if(tilt==='quality') return ((n(stock?.quality_pct)||50)-50)*.10 + ((n(stock?.cashflow_pct)||50)-50)*.05;
    if(tilt==='growth') return ((n(stock?.growth_pct)||50)-50)*.10 + ((n(stock?.estimate_momentum_score)||50)-50)*.05;
    if(tilt==='dividend'){
      const y=n(stock?.dividend_yield); const q=n(stock?.quality_pct)||50; const cf=n(stock?.cashflow_pct)||50;
      return (y!=null?Math.min(8,Math.max(0,y*100))*0.7:0)+(q-50)*.035+(cf-50)*.035;
    }
    return 0;
  }


  function stockCurrency(stock){
    const explicit=txt(stock?.currency||stock?.financial_currency||stock?.financialCurrency).toUpperCase();
    if(explicit) return explicit;
    const t=txt(stock?.ticker).toUpperCase();
    if(t.endsWith('.L')) return 'GBP'; if(/\.(DE|PA|AS|MI|MC|LS)$/.test(t)) return 'EUR';
    if(t.endsWith('.SW')) return 'CHF'; if(/\.(TO|V)$/.test(t)) return 'CAD'; if(t.endsWith('.T')) return 'JPY';
    if(t.endsWith('.HK')) return 'HKD'; if(t.endsWith('.AX')) return 'AUD'; if(t.endsWith('.ST')) return 'SEK';
    if(t.endsWith('.CO')) return 'DKK'; if(t.endsWith('.OL')) return 'NOK';
    return t.includes('.')?'Outra':'USD';
  }
  function stockRegion(stock){
    const c=txt(stock?.country||stock?.country_name||stock?.region).toLowerCase();
    if(/united states|usa|canada|mexico/.test(c)) return 'Am. Norte';
    if(/portugal|spain|france|germany|italy|netherlands|belgium|switzerland|austria|ireland|united kingdom|uk|sweden|norway|denmark|finland|poland/.test(c)) return 'Europa';
    if(/china|hong kong|japan|korea|taiwan|india|singapore|indonesia|thailand|malaysia/.test(c)) return 'Ásia';
    if(/australia|new zealand/.test(c)) return 'Pacífico';
    const t=txt(stock?.ticker).toUpperCase();
    if(/\.(L|DE|PA|AS|MI|MC|LS|SW|ST|CO|OL)$/.test(t)) return 'Europa';
    if(/\.(T|HK)$/.test(t)) return 'Ásia'; if(t.endsWith('.AX')) return 'Pacífico'; if(/\.(TO|V)$/.test(t)||!t.includes('.')) return 'Am. Norte';
    return 'Outra';
  }
  function stockRiskTags(stock){
    const tags=[]; const growth=n(stock?.growth_pct), value=n(stock?.value_pct), y=n(stock?.dividend_yield), cap=n(stock?.market_cap??stock?.marketCap);
    const model=txt(stock?.score_model).toLowerCase(), sec=txt(stock?.sector).toLowerCase(), ind=txt(stock?.industry).toLowerCase();
    if(model==='growth'||growth>=65||((n(stock?.revenue_growth)||0)>.20)) tags.push('Growth');
    if(value>=65) tags.push('Value');
    if(y!=null&&y>=.025) tags.push('Dividendos');
    if(cap!=null&&cap>0&&cap<2e9) tags.push('Small caps');
    if(model==='reit'||/real estate|reit|utilities|utility/.test(sec+' '+ind)||model==='growth') tags.push('Sensível a taxas');
    return [...new Set(tags)];
  }
  function riskMapAdd(map,key,value){ if(!key||!Number.isFinite(value)) return; map.set(key,(map.get(key)||0)+value); }
  function portfolioRiskProfile(rows,totalOverride){
    const total=totalOverride||rows.reduce((a,r)=>a+(n(r.value)||0),0)||1;
    const factors=new Map(), currencies=new Map(), regions=new Map();
    for(const r of rows){
      const v=n(r.value)||0; if(v<=0) continue;
      stockRiskTags(r.stock).forEach(tag=>riskMapAdd(factors,tag,v));
      riskMapAdd(currencies,stockCurrency(r.stock),v); riskMapAdd(regions,stockRegion(r.stock),v);
    }
    const pctRows=m=>[...m.entries()].map(([name,value])=>({name,value,pct:value/total*100})).sort((a,b)=>b.pct-a.pct);
    return {total,factors:pctRows(factors),currencies:pctRows(currencies),regions:pctRows(regions)};
  }
  function riskBudgetPenalty(stock,rows,amount,totalAfter,sourceStock=null){
    const targets=loadPortfolioTargets(); const maxFactor=n(targets.maxFactor)||45, maxCurrency=n(targets.maxCurrency)||70, maxRegion=n(targets.maxRegion)||70;
    const prof=portfolioRiskProfile(rows,totalAfter); const a=Math.max(0,n(amount)||0), delta=a/(totalAfter||1)*100;
    let penalty=0; const factors=stockRiskTags(stock), srcFactors=sourceStock?stockRiskTags(sourceStock):[];
    for(const tag of factors){ const now=prof.factors.find(x=>x.name===tag)?.pct||0; const after=now+delta-(srcFactors.includes(tag)?delta:0); if(after>maxFactor) penalty+=(after-maxFactor)*.65; }
    const cur=stockCurrency(stock), srcCur=sourceStock?stockCurrency(sourceStock):null, curNow=prof.currencies.find(x=>x.name===cur)?.pct||0;
    const curAfter=curNow+delta-(srcCur===cur?delta:0); if(curAfter>maxCurrency) penalty+=(curAfter-maxCurrency)*.55;
    const reg=stockRegion(stock), srcReg=sourceStock?stockRegion(sourceStock):null, regNow=prof.regions.find(x=>x.name===reg)?.pct||0;
    const regAfter=regNow+delta-(srcReg===reg?delta:0); if(regAfter>maxRegion) penalty+=(regAfter-maxRegion)*.45;
    return penalty;
  }
  function renderRiskBudget(rows){
    const profile=portfolioRiskProfile(rows), t=loadPortfolioTargets();
    const maxFactor=n(t.maxFactor)||45, maxCurrency=n(t.maxCurrency)||70, maxRegion=n(t.maxRegion)||70;
    const breaches=[...profile.factors.filter(x=>x.pct>maxFactor).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxFactor}%`),...profile.currencies.filter(x=>x.pct>maxCurrency).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxCurrency}%`),...profile.regions.filter(x=>x.pct>maxRegion).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxRegion}%`)];
    const excess=profile.factors.reduce((a,x)=>a+Math.max(0,x.pct-maxFactor),0)+profile.currencies.reduce((a,x)=>a+Math.max(0,x.pct-maxCurrency),0)+profile.regions.reduce((a,x)=>a+Math.max(0,x.pct-maxRegion),0);
    const fit=Math.max(0,Math.min(100,Math.round(100-excess*1.4))), tone=fit>=85?'is-positive':fit>=65?'is-warn':'is-risk';
    const statusLabel=fit>=85?'Boa diversificação':fit>=65?'Atenção':'Concentração elevada';
    const riskRows=(items,limit,max)=>items.slice(0,limit).map(x=>{
      const over=x.pct>max, width=Math.max(2,Math.min(100,x.pct));
      return `<div class="market-risk-item ${over?'is-over':''}"><div class="market-risk-item__head"><strong>${esc(x.name)}</strong><span>${x.pct.toFixed(0)}%${over?` · limite ${max}%`:''}</span></div><div class="market-risk-bar"><i style="width:${width}%"></i></div></div>`;
    }).join('');
    const html=`<div class="market-detail-card market-risk-budget"><div class="market-perspective-head"><div><small>PORTFOLIO RISK BUDGET · PROXY</small><h4>Diversificação da carteira</h4></div><div class="market-risk-score ${tone}"><strong>${fit}/100</strong><small>${statusLabel}</small></div></div><p class="market-risk-intro">Mostra onde a carteira está mais dependente do mesmo fator, moeda ou região. Quanto maior a concentração, maior o impacto se esse risco correr mal.</p><div class="market-risk-grid"><section class="market-risk-group"><div class="market-risk-group__title"><strong>Fatores</strong><small>máx. ${maxFactor}%</small></div><div>${riskRows(profile.factors,5,maxFactor)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section><section class="market-risk-group"><div class="market-risk-group__title"><strong>Moedas</strong><small>máx. ${maxCurrency}%</small></div><div>${riskRows(profile.currencies,4,maxCurrency)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section><section class="market-risk-group"><div class="market-risk-group__title"><strong>Regiões</strong><small>máx. ${maxRegion}%</small></div><div>${riskRows(profile.regions,4,maxRegion)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section></div>${breaches.length?`<div class="market-risk-alert"><strong>${breaches.length} ${breaches.length===1?'excesso a acompanhar':'excessos a acompanhar'}</strong><ul>${breaches.slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:'<div class="market-risk-ok"><strong>Dentro dos limites definidos</strong><span>Não há concentrações acima dos teus Portfolio Targets.</span></div>'}<p class="market-risk-footnote">Leitura de exposição, não previsão de volatilidade. Usa os dados disponíveis e pode conter proxies quando moeda/região não vêm explicitamente da fonte.</p></div>`;
    return {fit,html,profile};
  }

  const PORTFOLIO_STRESS_SCENARIOS={
    rates:{label:'Taxas +100 bps',note:'Choque de taxas. Penaliza sobretudo REITs, utilities e growth de duration longa.'},
    nasdaq:{label:'Nasdaq -20%',note:'Choque risk-off tecnológico. Usa Growth/Technology/beta como proxies de sensibilidade.'},
    oil:{label:'Petróleo -25%',note:'Choque de energia. Penaliza Energy; alguns consumidores intensivos em combustível recebem pequeno amortecedor.'},
    usd:{label:'USD -10%',note:'Choque cambial visto de uma carteira em EUR. Afeta diretamente ativos classificados em USD.'},
    europe:{label:'Recessão europeia',note:'Choque regional/cíclico. Penaliza Europa e setores mais sensíveis ao ciclo económico.'}
  };
  function stressImpactPct(stock,key){
    const tags=stockRiskTags(stock), sec=txt(stock?.sector).toLowerCase(), ind=txt(stock?.industry).toLowerCase();
    const beta=n(stock?.beta); let x=0;
    if(key==='rates'){
      if(tags.includes('Sensível a taxas')) x-=10;
      if(tags.includes('Growth')) x-=4;
      if(/real estate|reit/.test(sec+' '+ind)) x-=4;
      if(/utilities|utility/.test(sec+' '+ind)) x-=3;
      if(/bank|banks/.test(sec+' '+ind)) x+=2;
    }
    if(key==='nasdaq'){
      if(tags.includes('Growth')) x-=14;
      if(/technology|software|semiconductor|internet|cloud|cyber/.test(sec+' '+ind)) x-=7;
      if(beta!=null&&beta>1) x-=Math.min(5,(beta-1)*4);
      if(!x) x=-4;
    }
    if(key==='oil'){
      if(/energy|oil|gas|exploration|petroleum/.test(sec+' '+ind)) x-=18;
      else if(/airline|transport|logistics/.test(sec+' '+ind)) x+=3;
      else x-=1;
    }
    if(key==='usd') x=stockCurrency(stock)==='USD'?-10:0;
    if(key==='europe'){
      if(stockRegion(stock)==='Europa') x-=10;
      if(/financial|industrial|consumer cyclical|materials|automotive|bank/.test(sec+' '+ind)) x-=5;
      if(/utilities|healthcare|consumer defensive/.test(sec+' '+ind)) x+=2;
      if(!x) x=-2;
    }
    return Math.max(-35,Math.min(8,x));
  }
  function portfolioStress(rows,key){
    const total=rows.reduce((a,r)=>a+(n(r.value)||0),0)||1;
    const detail=rows.map(r=>{
      const impact=stressImpactPct(r.stock,key), weight=(n(r.value)||0)/total*100, contribution=impact*weight/100;
      return {...r,impact,weight,contribution};
    });
    const portfolioImpact=detail.reduce((a,r)=>a+r.contribution,0);
    const downside=Math.abs(Math.min(0,portfolioImpact));
    const resilience=Math.max(0,Math.min(100,Math.round(100-downside*4.2)));
    const exposedWeight=detail.filter(r=>r.impact<=-8).reduce((a,r)=>a+r.weight,0);
    const top=detail.filter(r=>r.impact<0).sort((a,b)=>a.contribution-b.contribution).slice(0,6);
    return {key,portfolioImpact,resilience,exposedWeight,top};
  }
  function renderStressScenario(rows,key){
    const sc=PORTFOLIO_STRESS_SCENARIOS[key], r=portfolioStress(rows,key);
    const tone=r.resilience>=75?'is-positive':r.resilience>=55?'is-warn':'is-risk';
    return `<div class="market-stress-result" data-stress-panel="${key}" ${key==='rates'?'':'hidden'}><div class="market-stress-kpis"><div><small>Impacto proxy</small><strong>${r.portfolioImpact>=0?'+':''}${r.portfolioImpact.toFixed(1)}%</strong></div><div><small>Resiliência</small><strong class="${tone}">${r.resilience}/100</strong></div><div><small>Exposição forte</small><strong>${r.exposedWeight.toFixed(0)}%</strong></div></div><p class="market-case-note">${esc(sc.note)}</p>${r.top.length?`<div class="market-stress-list">${r.top.map(x=>`<button type="button" data-market-ticker="${esc(x.stock.ticker)}"><span><strong>${esc(x.stock.ticker)}</strong><small>peso ${x.weight.toFixed(1)}% · choque ${x.impact.toFixed(0)}%</small></span><em>${x.contribution.toFixed(2)} pp</em></button>`).join('')}</div>`:'<p class="market-case-note">Sem exposição negativa material identificada neste cenário.</p>'}<p class="market-case-note">Stress proxy, não previsão: não modela correlações dinâmicas, opções, hedges, impostos nem liquidez.</p></div>`;
  }
  function renderPortfolioStressTest(rows){
    return `<div class="market-detail-card market-stress-test"><div class="market-perspective-head"><div><small>PORTFOLIO STRESS TEST · PROXY</small><h4>Como reage a carteira?</h4></div><span class="market-data-age">cenários</span></div><div class="market-stress-tabs">${Object.entries(PORTFOLIO_STRESS_SCENARIOS).map(([k,v],i)=>`<button type="button" data-stress-scenario="${k}" class="${i===0?'is-active':''}">${esc(v.label)}</button>`).join('')}</div>${Object.keys(PORTFOLIO_STRESS_SCENARIOS).map(k=>renderStressScenario(rows,k)).join('')}</div>`;
  }

  const PORTFOLIO_HEALTH_KEY='vestra_portfolio_health_v1';
  function portfolioHealthDay(d=new Date()){
    const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0');
    return `${y}-${m}-${day}`;
  }
  function loadPortfolioHealth(){
    try{ const x=JSON.parse(localStorage.getItem(PORTFOLIO_HEALTH_KEY)||'[]'); return Array.isArray(x)?x:[]; }
    catch{return [];}
  }
  function savePortfolioHealthSnapshot(snapshot){
    try{
      const day=portfolioHealthDay();
      const rows=loadPortfolioHealth().filter(x=>x&&x.day!==day);
      rows.push({...snapshot,day,ts:Date.now()});
      rows.sort((a,b)=>String(a.day).localeCompare(String(b.day)));
      const trimmed=rows.slice(-120);
      localStorage.setItem(PORTFOLIO_HEALTH_KEY,JSON.stringify(trimmed));
      return trimmed;
    }catch{return loadPortfolioHealth();}
  }
  function healthDeltaLabel(value,prev,inverse=false,suffix=''){
    if(value==null||prev==null) return '—';
    const d=value-prev; if(Math.abs(d)<0.05) return '≈ estável';
    const good=inverse?d<0:d>0; return `${good?'↑':'↓'} ${d>0?'+':''}${d.toFixed(1)}${suffix}`;
  }
  function renderPortfolioHealthTimeline(history){
    if(!history?.length) return '';
    const latest=history[history.length-1], prev=history.length>1?history[history.length-2]:null;
    const rows=history.slice(-8);
    const trend=prev?`${healthDeltaLabel(latest.targetFit,prev.targetFit,false,'')} fit · ${healthDeltaLabel(latest.conviction,prev.conviction,false,'')} conv.`:'Primeiro snapshot criado';
    return `<div class="market-detail-card market-health-timeline"><div class="market-perspective-head"><div><small>PORTFOLIO HEALTH · HISTÓRICO</small><h4>A carteira está a melhorar?</h4></div><span class="market-data-age">${history.length} ${history.length===1?'dia':'dias'}</span></div><div class="market-health-kpis"><div><small>Target Fit</small><strong>${Math.round(latest.targetFit)}</strong><em>${prev?healthDeltaLabel(latest.targetFit,prev.targetFit):'baseline'}</em></div><div><small>Convicção</small><strong>${latest.conviction.toFixed(1)}</strong><em>${prev?healthDeltaLabel(latest.conviction,prev.conviction):'baseline'}</em></div><div><small>Maior posição</small><strong>${latest.topPosition.toFixed(1)}%</strong><em>${prev?healthDeltaLabel(latest.topPosition,prev.topPosition,true,' pp'):'baseline'}</em></div><div><small>Rever/Substituir</small><strong>${latest.riskPositions}</strong><em>${prev?healthDeltaLabel(latest.riskPositions,prev.riskPositions,true):'baseline'}</em></div></div><div class="market-health-trend">${esc(trend)}</div><div class="market-health-history">${rows.map(x=>`<div class="market-health-row"><span>${esc(x.day.slice(5))}</span><div><i style="width:${Math.max(3,Math.min(100,x.targetFit))}%"></i></div><strong>${Math.round(x.targetFit)}</strong><small>conv ${x.conviction.toFixed(0)} · pos ${x.topPosition.toFixed(0)}% · setor ${x.topSector.toFixed(0)}% · overlap ${x.overlapCount} · risco ${x.riskPositions}</small></div>`).join('')}</div>${history.length<2?'<p class="market-case-note">A partir do próximo dia a Vestra começa a mostrar a direção das métricas. O snapshot do mesmo dia é atualizado, não duplicado.</p>':''}</div>`;
  }

  const RESEARCH_QUEUE_KEY='vestra_research_queue_v1';
  function loadResearchQueue(){
    try{ const x=JSON.parse(localStorage.getItem(RESEARCH_QUEUE_KEY)||'{}'); return x&&typeof x==='object'?x:{}; }
    catch{return {};}
  }
  function saveResearchQueue(x){ try{localStorage.setItem(RESEARCH_QUEUE_KEY,JSON.stringify(x||{}));}catch{} }
  function researchQueueState(ticker){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(), x=all[key]||{};
    if(x.status==='snoozed'&&Number(x.snoozeUntil||0)<=Date.now()) return {...x,status:'new',snoozeUntil:0};
    return {status:x.status||'new',snoozeUntil:Number(x.snoozeUntil||0),updatedAt:Number(x.updatedAt||0),checkpoint:txt(x.checkpoint),note:txt(x.note),checkpointAt:Number(x.checkpointAt||0)};
  }
  function setResearchQueueState(ticker,status){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(); if(!key)return;
    const prev=all[key]||{}; all[key]={...prev,status,updatedAt:Date.now(),snoozeUntil:status==='snoozed'?Date.now()+7*86400000:0};
    saveResearchQueue(all);
  }
  function saveResearchCheckpoint(ticker,checkpoint,note){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(); if(!key)return;
    const prev=all[key]||{};
    all[key]={...prev,checkpoint:txt(checkpoint),note:txt(note).slice(0,500),checkpointAt:Date.now(),updatedAt:Date.now()};
    saveResearchQueue(all);
  }
  function researchCheckpointEditor(ticker,state){
    const cp=txt(state?.checkpoint)||'';
    return `<div class="market-research-checkpoint" data-checkpoint-ticker="${esc(ticker)}"><select data-checkpoint-select><option value="" ${!cp?'selected':''}>Checkpoint…</option><option value="maintain" ${cp==='maintain'?'selected':''}>Mantém</option><option value="deteriorated" ${cp==='deteriorated'?'selected':''}>Deteriorou</option><option value="wait_earnings" ${cp==='wait_earnings'?'selected':''}>Aguardar earnings</option><option value="improving" ${cp==='improving'?'selected':''}>A melhorar</option><option value="exit_review" ${cp==='exit_review'?'selected':''}>Rever saída</option></select><input type="text" maxlength="500" data-checkpoint-note placeholder="Nota curta de research" value="${esc(state?.note||'')}"><button type="button" data-checkpoint-save>Guardar</button></div>`;
  }

  function renderResearchQueue(review){
    const rank={new:0,in_review:1,snoozed:2,reviewed:3};
    const items=review.map(r=>({r,state:researchQueueState(r.stock.ticker)})).sort((a,b)=>(rank[a.state.status]??9)-(rank[b.state.status]??9)||(a.r.conviction??999)-(b.r.conviction??999));
    const counts=items.reduce((a,x)=>{a[x.state.status]=(a[x.state.status]||0)+1;return a;},{});
    const visible=items.filter(x=>x.state.status!=='reviewed'&&x.state.status!=='snoozed').slice(0,12);
    const label={new:'Novo',in_review:'Em revisão',reviewed:'Revisto',snoozed:'Adiado'};
    const tone={new:'is-risk',in_review:'is-warn',reviewed:'is-positive',snoozed:''};
    const rows=visible.length?visible.map(({r,state})=>`<div class="market-research-queue-row" data-queue-ticker="${esc(r.stock.ticker)}"><button type="button" class="market-research-queue-main" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${r.conviction==null?'convicção insuficiente':`convicção ${Math.round(r.conviction)}/100`} · ${esc(txt(r.stock.risk_gate)||'clear')}</small></span><em class="${tone[state.status]||''}">${label[state.status]||'Novo'}</em></button><div class="market-research-queue-actions"><button type="button" data-queue-status="in_review">Em revisão</button><button type="button" data-queue-status="reviewed">Revisto</button><button type="button" data-queue-status="snoozed">Adiar 7d</button></div>${state.status==='in_review'||state.checkpoint?researchCheckpointEditor(r.stock.ticker,state):''}</div>`).join(''):'<p class="market-case-note">Sem revisões ativas pendentes. Itens adiados regressam automaticamente após 7 dias.</p>';
    return `<div class="market-detail-card market-research-queue"><div class="market-perspective-head"><div><small>RESEARCH QUEUE · LOCAL</small><h4>Fila de revisão</h4></div><span class="market-data-age">${(counts.new||0)+(counts.in_review||0)} pendentes</span></div><div class="market-action-context"><span>${counts.new||0} novos</span><span>${counts.in_review||0} em revisão</span><span>${counts.snoozed||0} adiados</span><span>${counts.reviewed||0} revistos</span></div><p class="market-case-note">Memória operacional: organiza o research sem alterar Score Vestra, Action Map ou carteira.</p><div class="market-research-queue-list">${rows}</div>${items.length>12?`<p class="market-case-note">A mostrar as 12 prioridades ativas mais urgentes de ${items.length} posições sinalizadas.</p>`:''}</div>`;
  }

  function renderPortfolioDecisionCenter(rows,total){
    const analysed=rows.reduce((a,r)=>a+(n(r.value)||0),0)||1;
    const ranked=rows.map(r=>({...r,conviction:portfolioConviction(r.stock)}));
    const convRows=ranked.filter(r=>r.conviction!=null&&r.value>0);
    const convWeight=convRows.reduce((a,r)=>a+r.value,0)||1;
    const conviction=convRows.reduce((a,r)=>a+r.value*r.conviction,0)/convWeight;
    const targets=loadPortfolioTargets();
    const riskBudget=renderRiskBudget(ranked);
    const stresses=Object.keys(PORTFOLIO_STRESS_SCENARIOS).map(k=>portfolioStress(ranked,k)).sort((a,b)=>a.resilience-b.resilience);
    const worst=stresses[0];
    const sectors=new Map(); ranked.forEach(r=>{const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value)});
    const topSector=[...sectors.entries()].map(([name,value])=>({name,pct:value/analysed*100})).sort((a,b)=>b.pct-a.pct)[0];
    const topPosition=ranked.slice().sort((a,b)=>b.value-a.value)[0];
    const topPositionPct=topPosition?topPosition.value/analysed*100:0;
    const review=ranked.filter(r=>['high','severe'].includes(txt(r.stock.risk_gate))||txt(r.stock.thesis_direction)==='down'||txt(r.stock.estimate_signal)==='deteriorating'||(r.conviction!=null&&r.conviction<50)).sort((a,b)=>(a.conviction??999)-(b.conviction??999));
    const reinforce=ranked.filter(r=>r.conviction!=null&&r.conviction>=70&&n(r.stock.confidence_score)>=60&&!['high','severe'].includes(txt(r.stock.risk_gate))&&!['overvalued','uncertain'].includes(txt(r.stock.valuation_signal))&&txt(r.stock.estimate_signal)!=='deteriorating').sort((a,b)=>b.conviction-a.conviction);
    let health=100; health-=Math.max(0,topPositionPct-targets.maxPosition)*1.4; health-=Math.max(0,(topSector?.pct||0)-targets.maxSector)*1.1; health-=review.length*2.2; health-=(100-riskBudget.fit)*.25; health-=(100-(worst?.resilience||100))*.20; health=Math.max(0,Math.min(100,Math.round(health)));
    const tone=health>=80?'is-positive':health>=60?'is-warn':'is-risk';
    const priorities=[];
    if(review[0]) priorities.push({label:`Rever ${review[0].stock.ticker}: ${review[0].conviction==null?'convicção insuficiente':`convicção ${Math.round(review[0].conviction)}/100`}`,kind:'ticker',value:review[0].stock.ticker});
    if(topPositionPct>targets.maxPosition&&topPosition) priorities.push({label:`${topPosition.stock.ticker} está acima do objetivo por posição (${topPositionPct.toFixed(1)}%)`,kind:'ticker',value:topPosition.stock.ticker});
    if(topSector&&topSector.pct>targets.maxSector) priorities.push({label:`${topSector.name} está acima do objetivo setorial (${topSector.pct.toFixed(1)}%)`,kind:'targets',value:'targets'});
    if(worst&&worst.resilience<70) priorities.push({label:`Stress mais exigente: ${PORTFOLIO_STRESS_SCENARIOS[worst.key].label} · resiliência ${worst.resilience}/100`,kind:'stress',value:worst.key});
    if(!priorities.length&&reinforce[0]) priorities.push({label:`Carteira sem alerta dominante; ${reinforce[0].stock.ticker} é o reforço com maior convicção atual`,kind:'ticker',value:reinforce[0].stock.ticker});
    const next=review[0]?{label:`Abrir ${review[0].stock.ticker} e rever a tese`,kind:'ticker',value:review[0].stock.ticker}:topPositionPct>targets.maxPosition?{label:'Usar o Rebalancer para reduzir concentração',kind:'rebalancer',value:'rebalancer'}:reinforce[0]?{label:`Avaliar reforço em ${reinforce[0].stock.ticker}`,kind:'ticker',value:reinforce[0].stock.ticker}:{label:'Manter e acompanhar',kind:'health',value:'health'};
    const jumpAttrs=x=>`data-decision-jump="${esc(x.kind)}" data-decision-value="${esc(x.value||'')}"`;
    return `<div class="market-detail-card market-decision-center"><div class="market-perspective-head"><div><small>PORTFOLIO DECISION CENTER</small><h4>O que merece atenção agora?</h4></div><span class="market-target-fit-score ${tone}">${health}/100</span></div><div class="market-decision-kpis"><button type="button" ${jumpAttrs({kind:'actionmap',value:'all'})}><small>Convicção</small><strong>${conviction.toFixed(1)}</strong></button><button type="button" ${jumpAttrs({kind:'riskbudget',value:'riskbudget'})}><small>Risk Budget</small><strong>${riskBudget.fit}</strong></button><button type="button" ${jumpAttrs({kind:'stress',value:worst?.key||'rates'})}><small>Pior stress</small><strong>${worst?worst.resilience:'—'}</strong></button><button type="button" ${jumpAttrs({kind:'actionmap',value:'review'})}><small>Rever/Substituir</small><strong>${review.length}</strong></button></div><button type="button" class="market-decision-next" ${jumpAttrs(next)}><small>PRÓXIMA AÇÃO DE RESEARCH</small><strong>${esc(next.label)}</strong><span>→</span></button><div class="market-decision-priorities">${priorities.slice(0,4).map(x=>`<button type="button" ${jumpAttrs(x)}><span>${esc(x.label)}</span><b>→</b></button>`).join('')}</div><p class="market-case-note">Síntese executiva: toca num sinal para abrir diretamente o detalhe correspondente. Não cria um novo score de investimento.</p></div>${renderResearchQueue(review)}`;
  }

  function portfolioIntelligence(rows,total){
    if(!rows.length) return '';
    const analysed=rows.reduce((a,r)=>a+r.value,0)||1;
    const ranked=rows.map(r=>({...r,conviction:portfolioConviction(r.stock)}));
    const heldTickers=new Set(ranked.map(r=>txt(r.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')));

    const sectors=new Map();
    for(const r of ranked){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const sectorRows=[...sectors.entries()].map(([sector,value])=>({sector,value,pct:value/analysed*100})).sort((a,b)=>b.value-a.value);
    const topPosition=ranked.slice().sort((a,b)=>b.value-a.value)[0];
    const topPosPct=topPosition?topPosition.value/analysed*100:0;

    const reinforce=ranked.filter(r=>r.conviction!=null&&r.conviction>=70&&n(r.stock.confidence_score)>=60&&!['high','severe'].includes(txt(r.stock.risk_gate))&&!['overvalued','uncertain'].includes(txt(r.stock.valuation_signal))&&txt(r.stock.estimate_signal)!=='deteriorating')
      .sort((a,b)=>b.conviction-a.conviction).slice(0,3);
    const review=ranked.filter(r=>['high','severe'].includes(txt(r.stock.risk_gate))||txt(r.stock.thesis_direction)==='down'||txt(r.stock.estimate_signal)==='deteriorating'||(r.conviction!=null&&r.conviction<50))
      .sort((a,b)=>(a.conviction??999)-(b.conviction??999)).slice(0,3);

    const etfsForFit=ranked.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/analysed*100}));
    for(const r of ranked) r.portfolioFit=portfolioFit(r,sectorRows,analysed,etfsForFit);

    const weak=ranked.slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999)).slice(0,5);
    const alternatives=[];
    for(const r of weak){
      const curScore=n(r.stock.score); if(!txt(r.stock.sector)||curScore==null) continue;
      const candidates=M.stocks.filter(x=>!isFund(x)&&!heldTickers.has(txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,''))&&txt(x.sector)===txt(r.stock.sector)&&n(x.score)!=null&&n(x.score)>=curScore+8&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating');
      const currentIndirect=r.portfolioFit?.indirectPct||0;
      const cand=candidates.map(x=>({stock:x,indirect:indirectExposurePct(x,etfsForFit)}))
        .sort((a,b)=>((portfolioConviction(b.stock)||0)-b.indirect*4)-((portfolioConviction(a.stock)||0)-a.indirect*4))[0];
      if(cand){
        const fit=cand.indirect+1<currentIndirect?'better':cand.indirect>currentIndirect+2?'worse':'neutral';
        alternatives.push({from:r.stock,to:cand.stock,delta:n(cand.stock.score)-curScore,portfolioFit:fit,currentIndirect,candidateIndirect:cand.indirect});
      }
      if(alternatives.length>=3) break;
    }
    const alternativesByTicker=new Map(alternatives.map(a=>[txt(a.from.ticker).toUpperCase(),a]));
    const actionRows=ranked.map(r=>({...r,action:portfolioAction(r.stock,alternativesByTicker,r.portfolioFit)}));
    const actionOrder={replace:0,review:1,reinforce:2,hold:3};
    actionRows.sort((a,b)=>(actionOrder[a.action.key]??9)-(actionOrder[b.action.key]??9)||(b.value-a.value));
    const actionCounts=actionRows.reduce((acc,r)=>{acc[r.action.key]=(acc[r.action.key]||0)+1;return acc;},{});

    const overlaps=[];
    const etfs=etfsForFit;
    for(let i=0;i<etfs.length;i++) for(let j=i+1;j<etfs.length;j++){
      const a=new Map(etfs[i].stock.top_holdings.map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null));
      const b=new Map(etfs[j].stock.top_holdings.map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null));
      let common=0, names=[];
      for(const [k,w] of a){ if(b.has(k)){ common+=Math.min(w,b.get(k)); names.push(k); } }
      if(common>=5) overlaps.push(`${etfs[i].stock.ticker} × ${etfs[j].stock.ticker} · ~${common.toFixed(0)}% top-holdings comuns${names.length?` (${names.slice(0,3).join(', ')})`:''}`);
    }
    for(const e of etfs){
      for(const h of e.stock.top_holdings){
        const sym=holdingSymbol(h), w=holdingWeight(h);
        if(sym&&w!=null&&w>=2&&heldTickers.has(sym)&&sym!==txt(e.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')) overlaps.push(`${sym} também está dentro de ${e.stock.ticker} · ~${w.toFixed(1)}% do ETF`);
      }
    }

    const concentration=[];
    if(topPosPct>=15) concentration.push(`${topPosition.stock.ticker} representa ~${topPosPct.toFixed(0)}% da parte analisável`);
    if(sectorRows[0]?.pct>=30) concentration.push(`${sectorRows[0].sector} concentra ~${sectorRows[0].pct.toFixed(0)}% da parte analisável`);
    concentration.push(...overlaps.slice(0,3));

    const compactRows=(arr,metaFn)=>arr.length?`<div class="market-list">${arr.map(r=>renderRow(r.stock,metaFn(r))).join('')}</div>`:'<p class="market-case-note">Nenhuma posição cumpre este filtro com os dados atuais.</p>';
    const altHtml=alternatives.length?`<div class="market-list">${alternatives.map(a=>renderRow(a.to,`Alternativa a ${a.from.ticker} · Score +${a.delta.toFixed(0)} · ${a.portfolioFit==='better'?'reduz overlap':a.portfolioFit==='worse'?'aumenta overlap':'impacto neutro'}`)).join('')}</div>`:'<p class="market-case-note">Sem alternativa claramente superior identificada no mesmo setor.</p>';
    const concHtml=concentration.length?`<ul class="market-case-list">${[...new Set(concentration)].slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="market-case-note">Sem concentração material detetada com os dados disponíveis.</p>';

    const convRows=ranked.filter(r=>r.conviction!=null&&r.value>0);
    const convictionWeight=convRows.reduce((sum,r)=>sum+r.value,0)||1;
    const portfolioConvictionNow=convRows.reduce((sum,r)=>sum+r.value*r.conviction,0)/convictionWeight;
    const scenarioRows=alternatives.map(a=>{
      const fromRow=ranked.find(r=>txt(r.stock.ticker).toUpperCase()===txt(a.from.ticker).toUpperCase());
      if(!fromRow) return null;
      const oldConv=portfolioConviction(a.from), newConv=portfolioConviction(a.to);
      if(oldConv==null||newConv==null) return null;
      const w=fromRow.value/convictionWeight;
      const after=portfolioConvictionNow+(newConv-oldConv)*w;
      const overlapBefore=n(a.currentIndirect)||0, overlapAfter=n(a.candidateIndirect)||0;
      const convDelta=after-portfolioConvictionNow, overlapDelta=overlapAfter-overlapBefore;
      let impact='Neutro';
      if(convDelta>=.5||overlapDelta<=-1) impact='Melhora';
      if(convDelta<0||overlapDelta>=2) impact='Piora';
      return {from:a.from,to:a.to,before:portfolioConvictionNow,after,convDelta,overlapBefore,overlapAfter,overlapDelta,impact};
    }).filter(Boolean).slice(0,3);
    const scenarioHtml=scenarioRows.length?`<div class="market-detail-card market-scenario-preview"><div class="market-perspective-head"><div><small>SCENARIO PREVIEW</small><h4>Se substituíres pelo mesmo valor</h4></div><span class="market-data-age">simulação</span></div><p class="market-case-note">Mantém o valor da posição e o setor; estima apenas o efeito na convicção ponderada e no overlap indireto.</p><div class="market-scenario-list">${scenarioRows.map(x=>`<div class="market-scenario-row"><div><strong>${esc(x.from.ticker)} → ${esc(x.to.ticker)}</strong><small>Convicção carteira ${x.before.toFixed(1)} → ${x.after.toFixed(1)} · overlap ${x.overlapBefore.toFixed(1)}% → ${x.overlapAfter.toFixed(1)}%</small></div><em class="${x.impact==='Melhora'?'is-positive':x.impact==='Piora'?'is-risk':''}">${x.impact}</em></div>`).join('')}</div></div>`:'';

    const rebalSourceRows=actionRows.filter(r=>r.value>0&&r.conviction!=null).slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999));
    const defaultSource=rebalSourceRows[0]||null;
    const rebalancerHtml=defaultSource?`<div class="market-detail-card market-rebalancer" data-rebalancer-card><div class="market-perspective-head"><div><small>ASSISTED REBALANCER</small><h4>Onde melhora mais este capital?</h4></div><span class="market-data-age">simulação</span></div><p class="market-case-note">Escolhe a posição de origem e o montante. A Vestra mantém o valor total da carteira e compara destinos elegíveis por convicção, concentração, overlap e valuation.</p><div class="market-rebalancer-controls"><label><span>Libertar de</span><select data-rebalance-source>${rebalSourceRows.map(r=>`<option value="${esc(r.stock.ticker)}">${esc(r.stock.ticker)} · ${euro(r.value)} · conv. ${Math.round(r.conviction)}</option>`).join('')}</select></label><label><span>Montante</span><input data-rebalance-amount type="number" min="1" max="${Math.max(1,Math.floor(defaultSource.value))}" step="1" value="${Math.max(1,Math.min(1000,Math.round(defaultSource.value)||1))}"></label><button type="button" data-rebalance-run>Simular</button></div><div class="market-rebalancer-results" data-rebalance-results><p class="market-case-note">Toca em Simular para comparar os melhores destinos.</p></div><p class="market-case-note">Research assistido; não considera fiscalidade, custos de transação, liquidez pessoal ou ordens reais.</p></div>`:'';
    const targets=loadPortfolioTargets();
    const targetPositionBreaches=ranked.map(r=>({ticker:r.stock.ticker,pct:r.value/analysed*100})).filter(x=>x.pct>targets.maxPosition).sort((a,b)=>b.pct-a.pct);
    const targetSectorBreaches=sectorRows.filter(x=>x.pct>targets.maxSector);
    const targetOverlapBreaches=targets.overlap==='reduce'?ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2):[];
    const posExcess=targetPositionBreaches.reduce((a,x)=>a+(x.pct-targets.maxPosition),0);
    const sectorExcess=targetSectorBreaches.reduce((a,x)=>a+(x.pct-targets.maxSector),0);
    const overlapExcess=targetOverlapBreaches.reduce((a,r)=>a+Math.max(0,(r.portfolioFit?.indirectPct||0)-2),0);
    const targetFit=Math.max(0,Math.min(100,Math.round(100-posExcess*1.5-sectorExcess*1.15-overlapExcess*2.5)));
    const targetTone=targetFit>=85?'is-positive':targetFit>=65?'is-warn':'is-risk';
    const targetIssues=[];
    targetPositionBreaches.slice(0,3).forEach(x=>targetIssues.push(`${x.ticker} ${x.pct.toFixed(1)}% > objetivo ${targets.maxPosition}%`));
    targetSectorBreaches.slice(0,2).forEach(x=>targetIssues.push(`${x.sector} ${x.pct.toFixed(1)}% > objetivo ${targets.maxSector}%`));
    if(targetOverlapBreaches.length) targetIssues.push(`${targetOverlapBreaches.length} posições com overlap indireto ≥2%`);
    const targetFitHtml=`<div class="market-detail-card market-target-fit"><div class="market-perspective-head"><div><small>TARGET FIT</small><h4>Aderência aos objetivos</h4></div><span class="market-target-fit-score ${targetTone}">${targetFit}/100</span></div><div class="market-action-context"><span>${targetPositionBreaches.length} posições acima</span><span>${targetSectorBreaches.length} setores acima</span><span>${targetOverlapBreaches.length} overlap</span></div>${targetIssues.length?`<ul class="market-case-list">${targetIssues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="market-case-note">A parte analisável da carteira está dentro dos objetivos definidos.</p>'}</div>`;
    const riskBudget=renderRiskBudget(ranked);
    const riskBudgetHtml=riskBudget.html;
    const stressTestHtml=renderPortfolioStressTest(ranked);
    const healthSnapshot={targetFit,conviction:portfolioConvictionNow,topPosition:topPosPct,topSector:sectorRows[0]?.pct||0,overlapCount:ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length,riskPositions:(actionCounts.review||0)+(actionCounts.replace||0),riskFit:riskBudget.fit};
    const healthHistory=savePortfolioHealthSnapshot(healthSnapshot);
    const healthTimelineHtml=renderPortfolioHealthTimeline(healthHistory);
    const targetHtml=`<div class="market-detail-card market-target-engine" data-target-engine><div class="market-perspective-head"><div><small>PORTFOLIO TARGETS</small><h4>Objetivos da carteira</h4></div><span class="market-data-age">guardado localmente</span></div><p class="market-case-note">Estes objetivos passam a orientar o Rebalancer e o plano multi-movimento. Não alteram a carteira por si só.</p><div class="market-target-grid"><label><span>Máx. por posição</span><div><input data-target-position type="number" min="3" max="30" step="1" value="${targets.maxPosition}"><em>%</em></div></label><label><span>Máx. por setor</span><div><input data-target-sector type="number" min="10" max="60" step="1" value="${targets.maxSector}"><em>%</em></div></label><label><span>Máx. fator</span><div><input data-target-factor type="number" min="20" max="80" step="5" value="${targets.maxFactor}"><em>%</em></div></label><label><span>Máx. moeda</span><div><input data-target-currency type="number" min="30" max="100" step="5" value="${targets.maxCurrency}"><em>%</em></div></label><label><span>Máx. região</span><div><input data-target-region type="number" min="30" max="100" step="5" value="${targets.maxRegion}"><em>%</em></div></label><label><span>Overlap ETF</span><select data-target-overlap><option value="reduce" ${targets.overlap==='reduce'?'selected':''}>Reduzir</option><option value="neutral" ${targets.overlap==='neutral'?'selected':''}>Neutro</option></select></label><label><span>Prioridade</span><select data-target-tilt><option value="balanced" ${targets.tilt==='balanced'?'selected':''}>Equilibrado</option><option value="quality" ${targets.tilt==='quality'?'selected':''}>Quality</option><option value="growth" ${targets.tilt==='growth'?'selected':''}>Growth</option><option value="dividend" ${targets.tilt==='dividend'?'selected':''}>Dividendos</option></select></label></div><button type="button" class="market-plan-run" data-target-save>Guardar objetivos</button><span class="market-target-status" data-target-status></span></div>`;
    const freshCapitalHtml=`<div class="market-detail-card market-fresh-capital" data-fresh-capital-card><div class="market-perspective-head"><div><small>FRESH CAPITAL PLANNER</small><h4>Entrou capital novo. Onde reforçar?</h4></div><span class="market-data-age">sem vendas</span></div><p class="market-case-note">Distribui novo capital por até 3 destinos elegíveis, respeitando os Portfolio Targets e sem vender posições existentes.</p><div class="market-fresh-controls"><label><span>Novo capital</span><div><input data-fresh-amount type="number" min="50" step="50" value="1000"><em>€</em></div></label><button type="button" data-fresh-run>Distribuir</button></div><div data-fresh-results><p class="market-case-note">A simulação privilegia convicção, margem de segurança, espaço dentro dos limites e a prioridade da carteira.</p></div></div>`;
    const planHtml=`<div class="market-detail-card market-rebalance-plan" data-rebalance-plan-card><div class="market-perspective-head"><div><small>MULTI-MOVE PLAN · TARGET AWARE</small><h4>Plano de rebalanceamento</h4></div><span class="market-data-age">até 3 movimentos</span></div><p class="market-case-note">Gera um plano a partir das posições mais frágeis e respeita os objetivos guardados acima.</p><button type="button" class="market-plan-run" data-rebalance-plan>Gerar plano</button><div data-rebalance-plan-results><p class="market-case-note">Nenhuma alteração é aplicada à carteira.</p></div></div>`;
    const concentratedCount=ranked.filter(r=>r.portfolioFit?.fit==='concentrated').length;
    const overlapCount=ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length;
    const actionMapHtml=`<div class="market-detail-card market-action-map"><div class="market-perspective-head"><div><small>ACTION MAP · PORTFOLIO FIT</small><h4>Mapa da carteira</h4></div><span class="market-data-age">${actionRows.length} posições</span></div><div class="market-action-context"><span>${concentratedCount} concentração</span><span>${overlapCount} overlap indireto</span><span>${sectorRows[0]?`${esc(sectorRows[0].sector)} ${sectorRows[0].pct.toFixed(0)}%`:'setor —'}</span></div><div class="market-action-summary"><button type="button" class="is-positive" data-action-filter="reinforce">Reforçar ${actionCounts.reinforce||0}</button><button type="button" data-action-filter="hold">Manter ${actionCounts.hold||0}</button><button type="button" class="is-warn" data-action-filter="review">Rever ${actionCounts.review||0}</button><button type="button" class="is-risk" data-action-filter="replace">Substituir ${actionCounts.replace||0}</button></div><div class="market-action-filter-status" data-action-filter-status>Mostrar todas as posições</div><div class="market-action-list">${actionRows.slice(0,12).map(r=>`<button type="button" class="market-action-row" data-action-key="${esc(r.action.key)}" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${esc(r.action.reason)}</small></span><em class="market-action-badge market-action-badge--${r.action.tone}">${esc(r.action.label)}</em></button>`).join('')}</div>${actionRows.length>12?`<details class="market-detail-disclosure"><summary>Ver mais ${actionRows.length-12} posições</summary><div class="market-action-list">${actionRows.slice(12).map(r=>`<button type="button" class="market-action-row" data-action-key="${esc(r.action.key)}" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${esc(r.action.reason)}</small></span><em class="market-action-badge market-action-badge--${r.action.tone}">${esc(r.action.label)}</em></button>`).join('')}</div></details>`:''}<p class="market-case-note">Classificação de research baseada em dados atuais; não é uma ordem automática de compra ou venda.</p></div>`;

    return `${renderPortfolioDecisionCenter(rows,total)}
      <div class="market-detail-card"><div class="market-perspective-head"><div><small>PORTFOLIO INTELLIGENCE</small><h4>Prioridades da carteira</h4></div><span class="market-data-age">${Math.round(analysed/(total||analysed)*100)}% coberto</span></div><p>Convicção combina Score Vestra, confiança, valuation, expectativas e Risk Gate. É uma priorização de research — não uma ordem de compra ou venda.</p></div>
      ${actionMapHtml}
      <div class="market-detail-card"><h4>Candidatos a reforço</h4>${compactRows(reinforce,r=>`Convicção ${Math.round(r.conviction)}/100 · ${txt(r.stock.valuation_signal)||'valuation sem sinal'}`)}</div>
      <div class="market-detail-card"><h4>Posições a rever</h4>${compactRows(review,r=>`Convicção ${r.conviction==null?'—':Math.round(r.conviction)}/100 · ${txt(r.stock.risk_gate)||'clear'} · ${txt(r.stock.estimate_signal)||'expectativas —'}`)}</div>
      <div class="market-detail-card"><h4>Concentração e overlap</h4>${concHtml}</div>
      <div class="market-detail-card"><h4>Alternativas no mesmo setor</h4><p class="market-case-note">Só aparecem quando há uma empresa não detida com score pelo menos 8 pontos superior, confiança ≥60 e sem Risk Gate alto/severo.</p>${altHtml}</div>
      ${scenarioHtml}
      ${targetFitHtml}
      ${healthTimelineHtml}
      ${riskBudgetHtml}
      ${stressTestHtml}
      ${targetHtml}
      ${freshCapitalHtml}
      ${rebalancerHtml}
      ${planHtml}`;
  }

  function buildMultiMovePlan(){
    const assets=portfolioAssets().slice();
    const eligible=assets.filter(researchEligibleAsset);
    const rowMap=new Map();
    for(const a of eligible){
      const t=assetTicker(a); if(!t) continue; const base=t.replace(/\.[A-Z]+$/,'');
      const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===base);
      if(!stock) continue;
      const key=txt(stock.ticker).toUpperCase(); const prev=rowMap.get(key)||{stock,value:0}; prev.value+=portfolioValue(a); rowMap.set(key,prev);
    }
    const rows=[...rowMap.values()].map(r=>({...r,conviction:portfolioConviction(r.stock)})).filter(r=>r.conviction!=null&&r.value>0);
    const sources=rows.filter(r=>['high','severe'].includes(txt(r.stock.risk_gate))||txt(r.stock.thesis_direction)==='down'||txt(r.stock.estimate_signal)==='deteriorating'||r.conviction<55).sort((a,b)=>a.conviction-b.conviction||b.value-a.value);
    const fallback=rows.slice().sort((a,b)=>a.conviction-b.conviction||b.value-a.value);
    const queue=(sources.length?sources:fallback).slice(0,5);
    const usedDest=new Set(), moves=[]; let totalConvDelta=0, totalOverlapDelta=0, totalMoved=0;
    for(const src of queue){
      if(moves.length>=3) break;
      const amount=Math.max(100,Math.min(1000,Math.round((src.value*.25)/50)*50||100));
      const sim=rebalanceSimulation(src.stock.ticker,amount); if(sim.error||!sim.results?.length) continue;
      const dest=sim.results.find(r=>!usedDest.has(txt(r.stock.ticker).toUpperCase())&&r.convDelta>0&&r.overlapDelta<3) || sim.results.find(r=>!usedDest.has(txt(r.stock.ticker).toUpperCase()));
      if(!dest) continue;
      usedDest.add(txt(dest.stock.ticker).toUpperCase());
      totalConvDelta+=dest.convDelta; totalOverlapDelta+=dest.overlapDelta; totalMoved+=sim.amount;
      moves.push({from:sim.source,to:dest.stock,amount:sim.amount,convDelta:dest.convDelta,overlapDelta:dest.overlapDelta,fitScore:dest.fitScore});
    }
    return {moves,totalConvDelta,totalOverlapDelta,totalMoved};
  }

  function renderMultiMovePlan(plan){
    if(!plan?.moves?.length) return '<p class="market-case-note">Não encontrei um plano automático robusto. Experimenta o Rebalancer manual: a Vestra agora mostra candidatos aceitáveis com alertas em vez de esconder tudo.</p>';
    const impact=plan.totalConvDelta>0&&plan.totalOverlapDelta<=1?'Melhora':plan.totalConvDelta<0||plan.totalOverlapDelta>=4?'Piora':'Neutro';
    return `<div class="market-plan-summary"><strong>${impact}</strong><span>${euro(plan.totalMoved)} realocados · Δ convicção ${plan.totalConvDelta>=0?'+':''}${plan.totalConvDelta.toFixed(2)} · Δ overlap ${plan.totalOverlapDelta>=0?'+':''}${plan.totalOverlapDelta.toFixed(1)} pp</span></div><div class="market-plan-list">${plan.moves.map((m,i)=>`<div class="market-plan-row"><span class="market-rebalance-rank">${i+1}</span><div><strong>${esc(m.from.ticker)} → ${esc(m.to.ticker)} · ${euro(m.amount)}</strong><small>Δ convicção ${m.convDelta>=0?'+':''}${m.convDelta.toFixed(2)} · overlap ${m.overlapDelta>=0?'+':''}${m.overlapDelta.toFixed(1)} pp · fit ${m.fitScore.toFixed(0)}</small></div></div>`).join('')}</div><p class="market-case-note">Plano indicativo: não considera impostos, spreads, comissões, liquidez nem preferências pessoais.</p>`;
  }

  function rebalanceSimulation(sourceTicker, amount){
    const source=txt(sourceTicker).toUpperCase();
    const assets=portfolioAssets().slice();
    const eligible=assets.filter(researchEligibleAsset);
    const rowMap=new Map();
    for(const a of eligible){
      const t=assetTicker(a); if(!t) continue; const base=t.replace(/\.[A-Z]+$/,'');
      const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===base);
      if(!stock) continue;
      const key=txt(stock.ticker).toUpperCase();
      const prev=rowMap.get(key)||{stock,value:0}; prev.value+=portfolioValue(a); rowMap.set(key,prev);
    }
    const rows=[...rowMap.values()];
    const analysed=rows.reduce((sum,r)=>sum+r.value,0)||1;
    const src=rows.find(r=>txt(r.stock.ticker).toUpperCase()===source); if(!src) return {error:'Posição de origem não encontrada.'};
    const move=Math.max(0,Math.min(n(amount)||0,src.value)); if(move<=0) return {error:'Indica um montante válido.'};
    const srcConv=portfolioConviction(src.stock); if(srcConv==null) return {error:'A posição de origem não tem convicção calculável.'};
    const sectors=new Map(); for(const r of rows){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const etfs=rows.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/analysed*100}));
    const held=new Map(rows.map(r=>[txt(r.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,''),r]));
    const srcSector=txt(src.stock.sector)||'Sem setor';
    const srcIndirect=isFund(src.stock)?0:indirectExposurePct(src.stock,etfs);
    const universe=M.stocks.filter(x=>!isFund(x)&&txt(x.ticker).toUpperCase()!==source&&n(x.score)!=null&&!['high','severe'].includes(txt(x.risk_gate)));
    const ranked=universe.map(stock=>{
      const conv=portfolioConviction(stock); if(conv==null) return null;
      const base=txt(stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,'');
      const existing=held.get(base); const existingValue=existing?.value||0;
      const destSector=txt(stock.sector)||'Sem setor';
      let sectorValue=sectors.get(destSector)||0;
      if(destSector===srcSector) sectorValue-=move;
      sectorValue+=move;
      const sectorPct=sectorValue/analysed*100;
      const positionPct=(existingValue+move)/analysed*100;
      const indirect=isFund(stock)?0:indirectExposurePct(stock,etfs);
      const convDelta=(conv-srcConv)*(move/analysed);
      const targets=loadPortfolioTargets();
      const maxPos=Math.max(3,Math.min(30,n(targets.maxPosition)||10));
      const maxSector=Math.max(10,Math.min(60,n(targets.maxSector)||25));
      let penalty=0;
      if(positionPct>maxPos) penalty+=(positionPct-maxPos)*1.7;
      else if(positionPct>maxPos*.85) penalty+=(positionPct-maxPos*.85)*.55;
      if(sectorPct>maxSector) penalty+=(sectorPct-maxSector)*1.2;
      else if(sectorPct>maxSector*.88) penalty+=(sectorPct-maxSector*.88)*.45;
      if(targets.overlap==='reduce'&&indirect>1.5) penalty+=(indirect-1.5)*2.4;
      const diversityBonus=(destSector!==srcSector && (sectors.get(destSector)||0)/analysed*100<Math.min(20,maxSector*.75))?3:0;
      const valuationBonus=txt(stock.valuation_signal)==='undervalued'?3:0;
      const tiltBonus=portfolioTiltBonus(stock,targets.tilt);
      const riskPenalty=riskBudgetPenalty(stock,rows,move,analysed,src.stock);
      const conf=n(stock.confidence_score), valuation=txt(stock.valuation_signal), estimates=txt(stock.estimate_signal);
      const strict=conf!=null&&conf>=60&&valuation!=='overvalued'&&estimates!=='deteriorating';
      const acceptable=(conf==null||conf>=45)&&!(valuation==='overvalued'&&estimates==='deteriorating');
      let evidencePenalty=0; const warnings=[];
      if(conf==null){ evidencePenalty+=7; warnings.push('confiança sem score'); }
      else if(conf<60){ evidencePenalty+=(60-conf)*.35+3; warnings.push(`confiança ${Math.round(conf)}`); }
      if(valuation==='overvalued'){ evidencePenalty+=9; warnings.push('valuation exigente'); }
      else if(valuation==='uncertain'){ evidencePenalty+=3; warnings.push('valuation incerto'); }
      if(estimates==='deteriorating'){ evidencePenalty+=8; warnings.push('expectativas a piorar'); }
      const tier=strict?'preferred':acceptable?'acceptable':'research';
      if(tier==='research') evidencePenalty+=12;
      const fitScore=conv-penalty-riskPenalty+diversityBonus+valuationBonus+tiltBonus-evidencePenalty;
      return {stock,conv,convDelta,fitScore,positionPct,sectorPct,indirect,overlapDelta:indirect-srcIndirect,existing:!!existing,targets,tier,warnings};
    }).filter(Boolean).sort((a,b)=>{ const rank={preferred:0,acceptable:1,research:2}; return (rank[a.tier]-rank[b.tier])||b.fitScore-a.fitScore; }).slice(0,5);
    return {source:src.stock,amount:move,sourceConv:srcConv,results:ranked};
  }

  function renderRebalanceResults(sim){
    if(sim?.error) return `<p class="market-case-note">${esc(sim.error)}</p>`;
    if(!sim?.results?.length) return '<p class="market-case-note">Sem candidatos sequer para research. Revê o universo de dados ou os Portfolio Targets.</p>';
    const t=loadPortfolioTargets();
    const tierLabel=r=>r.tier==='preferred'?'Preferido':r.tier==='acceptable'?'Aceitável':'Research';
    return `<div class="market-target-summary">Limites: posição ${t.maxPosition}% · setor ${t.maxSector}% · ${t.overlap==='reduce'?'reduzir overlap':'overlap neutro'} · ${esc(t.tilt)}</div><div class="market-rebalance-list">${sim.results.map((r,i)=>`<button type="button" class="market-rebalance-row" data-market-ticker="${esc(r.stock.ticker)}"><span class="market-rebalance-rank">${i+1}</span><span><strong>${esc(r.stock.ticker)} · ${esc(r.stock.name||'')}</strong><small>${tierLabel(r)} · ${r.existing?'já em carteira':'nova posição'} · conv. ${Math.round(r.conv)} · peso após ${r.positionPct.toFixed(1)}% · setor ${r.sectorPct.toFixed(0)}%</small><small>Δ convicção ${r.convDelta>=0?'+':''}${r.convDelta.toFixed(2)} · overlap ${r.overlapDelta>=0?'+':''}${r.overlapDelta.toFixed(1)} pp${r.warnings?.length?' · ⚠ '+esc(r.warnings.slice(0,2).join(' · ')):''}</small></span><em>${r.fitScore.toFixed(0)}</em></button>`).join('')}</div>`;
  }

  function freshCapitalPlan(amount){
    const fresh=Math.max(0,n(amount)||0); if(fresh<50) return {error:'Indica pelo menos 50 € de novo capital.'};
    const assets=portfolioAssets().slice().filter(researchEligibleAsset);
    const rowMap=new Map();
    for(const a of assets){
      const t=assetTicker(a); if(!t) continue; const base=t.replace(/\.[A-Z]+$/,'');
      const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===base); if(!stock) continue;
      const key=txt(stock.ticker).toUpperCase(); const prev=rowMap.get(key)||{stock,value:0}; prev.value+=portfolioValue(a); rowMap.set(key,prev);
    }
    const rows=[...rowMap.values()]; const analysed=rows.reduce((sum,r)=>sum+r.value,0)||1; const afterTotal=analysed+fresh;
    const sectors=new Map(); for(const r of rows){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const held=new Map(rows.map(r=>[txt(r.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,''),r]));
    const etfs=rows.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/analysed*100}));
    const targets=loadPortfolioTargets(), maxPos=Math.max(3,Math.min(30,n(targets.maxPosition)||10)), maxSector=Math.max(10,Math.min(60,n(targets.maxSector)||25));
    const universe=M.stocks.filter(x=>!isFund(x)&&n(x.score)!=null&&!['high','severe'].includes(txt(x.risk_gate)));
    const candidates=universe.map(stock=>{
      const conv=portfolioConviction(stock); if(conv==null) return null;
      const base=txt(stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,''); const existing=held.get(base); const existingValue=existing?.value||0;
      const sector=txt(stock.sector)||'Sem setor', sectorValue=sectors.get(sector)||0, indirect=isFund(stock)?0:indirectExposurePct(stock,etfs);
      const strictPosCapacity=Math.max(0,afterTotal*maxPos/100-existingValue), strictSectorCapacity=Math.max(0,afterTotal*maxSector/100-sectorValue);
      const softPosCapacity=Math.max(0,afterTotal*(maxPos+3)/100-existingValue), softSectorCapacity=Math.max(0,afterTotal*(maxSector+5)/100-sectorValue);
      let capacity=Math.min(strictPosCapacity,strictSectorCapacity,fresh), budgetMode='within targets';
      if(capacity<50){ capacity=Math.min(softPosCapacity,softSectorCapacity,fresh); budgetMode='soft budget'; }
      if(capacity<50) return null;
      const conf=n(stock.confidence_score), valuation=txt(stock.valuation_signal), estimates=txt(stock.estimate_signal);
      const strict=conf!=null&&conf>=60&&valuation!=='overvalued'&&estimates!=='deteriorating'&&budgetMode==='within targets';
      const acceptable=(conf==null||conf>=45)&&!(valuation==='overvalued'&&estimates==='deteriorating');
      const tier=strict?'preferred':acceptable?'acceptable':'research';
      const warnings=[]; let score=conv+portfolioTiltBonus(stock,targets.tilt);
      if(conf==null){ score-=7; warnings.push('confiança sem score'); } else if(conf<60){ score-=(60-conf)*.35+3; warnings.push(`confiança ${Math.round(conf)}`); }
      if(valuation==='overvalued'){ score-=9; warnings.push('valuation exigente'); }
      if(estimates==='deteriorating'){ score-=8; warnings.push('expectativas a piorar'); }
      if(budgetMode==='soft budget'){ score-=6; warnings.push('excede objetivo ligeiramente'); }
      if(tier==='research') score-=12;
      if(valuation==='undervalued') score+=4; else if(valuation==='fair') score+=1;
      const sectorNow=sectorValue/analysed*100; if(sectorNow<maxSector*.55) score+=3; else if(sectorNow>maxSector*.85) score-=3;
      if(existing&&existingValue/analysed*100<maxPos*.65) score+=2;
      if(targets.overlap==='reduce'&&indirect>1.5) score-=(indirect-1.5)*2.5;
      score-=riskBudgetPenalty(stock,rows,Math.min(capacity,fresh),afterTotal);
      return {stock,conv,score,capacity,existingValue,sector,sectorValue,indirect,tier,warnings,budgetMode};
    }).filter(Boolean).sort((a,b)=>{ const rank={preferred:0,acceptable:1,research:2}; return (rank[a.tier]-rank[b.tier])||b.score-a.score; });
    const allocations=[], used=new Set(); let remaining=fresh; const shares=[.5,.3,.2];
    for(let i=0;i<shares.length&&remaining>=50;i++){
      const cand=candidates.find(c=>!used.has(txt(c.stock.ticker).toUpperCase())&&c.capacity>=50); if(!cand) break;
      let desired=i===shares.length-1?remaining:Math.max(50,Math.round((fresh*shares[i])/50)*50);
      let alloc=Math.min(remaining,cand.capacity,desired); alloc=Math.floor(alloc/50)*50; if(alloc<50){used.add(txt(cand.stock.ticker).toUpperCase()); i--; continue;}
      used.add(txt(cand.stock.ticker).toUpperCase()); remaining-=alloc;
      const positionPct=(cand.existingValue+alloc)/afterTotal*100, sectorPct=(cand.sectorValue+alloc)/afterTotal*100;
      allocations.push({...cand,amount:alloc,positionPct,sectorPct});
    }
    if(remaining>=50){
      for(const cand of candidates){
        if(remaining<50) break; if(used.has(txt(cand.stock.ticker).toUpperCase())) continue;
        let alloc=Math.min(remaining,cand.capacity); alloc=Math.floor(alloc/50)*50; if(alloc<50) continue;
        used.add(txt(cand.stock.ticker).toUpperCase()); remaining-=alloc;
        allocations.push({...cand,amount:alloc,positionPct:(cand.existingValue+alloc)/afterTotal*100,sectorPct:(cand.sectorValue+alloc)/afterTotal*100});
        if(allocations.length>=5) break;
      }
    }
    const currentConvRows=rows.map(r=>({...r,conv:portfolioConviction(r.stock)})).filter(r=>r.conv!=null&&r.value>0), convBase=currentConvRows.reduce((a,r)=>a+r.value,0)||1;
    const currentConv=currentConvRows.reduce((a,r)=>a+r.value*r.conv,0)/convBase;
    const added=allocations.reduce((a,x)=>a+x.amount,0), afterConv=(currentConv*convBase+allocations.reduce((a,x)=>a+x.amount*x.conv,0))/(convBase+added||1);
    return {fresh,allocated:added,remaining:fresh-added,currentConv,afterConv,allocations,targets};
  }

  function renderFreshCapitalPlan(plan){
    if(plan?.error) return `<p class="market-case-note">${esc(plan.error)}</p>`;
    if(!plan?.allocations?.length) return '<p class="market-case-note">Não encontrei candidatos mesmo após relaxar os filtros. Revê os objetivos ou a cobertura do universo.</p>';
    const tierLabel=x=>x.tier==='preferred'?'Preferido':x.tier==='acceptable'?'Aceitável':'Research';
    return `<div class="market-fresh-summary"><strong>${euro(plan.allocated)} distribuídos</strong><span>Convicção ponderada ${plan.currentConv.toFixed(1)} → ${plan.afterConv.toFixed(1)}${plan.remaining>=50?` · ${euro(plan.remaining)} ficam por alocar`:''}</span></div><div class="market-fresh-list">${plan.allocations.map((x,i)=>`<button type="button" class="market-fresh-row" data-market-ticker="${esc(x.stock.ticker)}"><span class="market-rebalance-rank">${i+1}</span><span><strong>${esc(x.stock.ticker)} · ${euro(x.amount)}</strong><small>${tierLabel(x)} · ${x.existingValue>0?'reforço existente':'nova posição'} · conv. ${Math.round(x.conv)} · ${esc(x.sector)}</small><small>Peso ${x.positionPct.toFixed(1)}% · setor ${x.sectorPct.toFixed(1)}% · fit ${x.score.toFixed(0)}${x.warnings?.length?' · ⚠ '+esc(x.warnings.slice(0,2).join(' · ')):''}</small></span></button>`).join('')}</div><p class="market-case-note">Preferido = cumpre filtros ideais; Aceitável/Research aparecem com alertas em vez de serem escondidos. Risk Gate high/severe continua excluído.</p>`;
  }

  function openTool(tool){
    ensureLoaded().then(()=>{
      const sh=$m('marketSheet'), c=$m('marketSheetContent'); if(!sh||!c)return;
      sh.hidden=false; sh.setAttribute('aria-hidden','false'); document.body.classList.add('modal-open'); sh.dataset.ticker='';
      sh.dataset.tool=tool||''; sh.dataset.returnView=tool==='portfolio'?'assets':'';
      scrollDossierTop();
      if(tool==='portfolio'){
        const assets=portfolioAssets().slice().sort((a,b)=>portfolioValue(b)-portfolioValue(a));
        const eligible=assets.filter(researchEligibleAsset);
        const crypto=assets.filter(a=>txt(a?.class).toLowerCase().includes('cripto'));
        const other=assets.filter(a=>!researchEligibleAsset(a)&&!txt(a?.class).toLowerCase().includes('cripto'));
        const rowMap=new Map();
        for(const a of eligible){
          const t=assetTicker(a); if(!t) continue; const base=t.replace(/\.[A-Z]+$/,'');
          const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===base);
          if(!stock) continue;
          const key=txt(stock.ticker).toUpperCase();
          const prev=rowMap.get(key)||{stock,value:0,classes:new Set()};
          prev.value+=portfolioValue(a); prev.classes.add(txt(a.class)||'Ações/ETFs'); rowMap.set(key,prev);
        }
        const rows=[...rowMap.values()].sort((a,b)=>b.value-a.value);
        const total=assets.reduce((sum,a)=>sum+portfolioValue(a),0);
        const analysed=rows.reduce((sum,r)=>sum+r.value,0);
        const first=rows.slice(0,8), rest=rows.slice(8);
        const researchRows = first.map(r=>renderRow(r.stock,`${[...r.classes].join(' · ')} · ${euro(r.value)}${r.stock.thesis_direction_label?' · '+r.stock.thesis_direction_label:''}`)).join('');
        const restRows = rest.length?`<details class="market-detail-disclosure"><summary>Ver mais ${rest.length} posições analisáveis</summary><div class="market-list" style="margin-top:7px">${rest.map(r=>renderRow(r.stock,`${[...r.classes].join(' · ')} · ${euro(r.value)}`)).join('')}</div></details>`:'';
        const aggregateAssets=(list)=>{ const m=new Map(); for(const a of list){ const key=assetTicker(a)||`${txt(a.class)}|${txt(a.name)}`; const prev=m.get(key)||{...a,value:0}; prev.value+=portfolioValue(a); m.set(key,prev); } return [...m.values()].sort((a,b)=>portfolioValue(b)-portfolioValue(a)); };
        const cryptoGrouped=aggregateAssets(crypto), otherGrouped=aggregateAssets(other);
        const assetPlainRow=(a,tone='other')=>`<div class="market-asset-row"><div><div class="market-asset-row__title"><strong>${esc(a.name||assetTicker(a)||'Ativo')}</strong><span class="market-class-badge market-class-badge--${tone}">${esc(a.class||'Outro')}</span></div><div class="market-asset-row__meta">${assetTicker(a)?esc(assetTicker(a))+' · ':''}${tone==='crypto'?'Criptoativo — métricas empresariais não se aplicam.':'Gerido na Carteira, fora do scanner fundamental.'}</div></div><div class="market-asset-row__value">${euro(portfolioValue(a))}</div></div>`;
        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">CARTEIRA × MERCADO</div><h2>As minhas posições</h2><p>Primeiro o que é analisável. Cripto e outros ativos ficam separados para não serem confundidos com empresas.</p></div><button class="market-close" data-market-close>×</button></div>
          <div class="market-portfolio-summary"><div class="market-portfolio-kpi"><small>Posições</small><strong>${assets.length}</strong></div><div class="market-portfolio-kpi"><small>Com research</small><strong>${rows.length}</strong></div><div class="market-portfolio-kpi"><small>Cobertura</small><strong>${total>0?Math.round(analysed/total*100):0}%</strong></div></div>
          ${portfolioIntelligence(rows,total)}
          <div class="market-portfolio-section"><div class="market-portfolio-section__head"><h3>Ações, ETFs e fundos</h3><span>${rows.length} reconhecidas</span></div><div class="market-asset-note">Ordenadas pelo valor que tens em carteira. Toca numa posição para abrir o Investment Case e ver o que mudou.</div><div class="market-list">${researchRows||'<div class="market-empty">Ainda não encontrei posições elegíveis no universo do scanner.</div>'}</div>${restRows}</div>
          ${cryptoGrouped.length?`<div class="market-portfolio-section"><div class="market-portfolio-section__head"><h3>Criptoativos</h3><span>${cryptoGrouped.length}</span></div><div class="market-asset-note">Separados de empresas de propósito. Um símbolo como ATOM não será interpretado como uma ação com o mesmo ticker.</div>${cryptoGrouped.slice(0,6).map(a=>assetPlainRow(a,'crypto')).join('')}${cryptoGrouped.length>6?`<details class="market-detail-disclosure"><summary>Ver mais ${cryptoGrouped.length-6} criptoativos</summary><div style="margin-top:7px">${cryptoGrouped.slice(6).map(a=>assetPlainRow(a,'crypto')).join('')}</div></details>`:''}</div>`:''}
          ${otherGrouped.length?`<details class="market-detail-disclosure"><summary>Outros ativos da carteira · ${otherGrouped.length}</summary><div class="market-asset-note">Depósitos, imobiliário, metais, liquidez e outros ativos continuam no património, mas não entram no research de empresas.</div>${otherGrouped.slice(0,12).map(a=>assetPlainRow(a,'other')).join('')}${otherGrouped.length>12?`<div class="market-asset-note">+ ${otherGrouped.length-12} ativos adicionais na Carteira.</div>`:''}</details>`:''}`;
      }
      if(tool==='theses'){
        const rows=M.stocks.filter(s=>!isFund(s)&&n(s.score)!=null&&['up','down'].includes(txt(s.thesis_direction))).sort((a,b)=>(txt(a.thesis_direction)==='up'?-1:1)-(txt(b.thesis_direction)==='up'?-1:1)||(n(b.thesis_score_delta_30d)||0)-(n(a.thesis_score_delta_30d)||0)).slice(0,30);
        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">TESES</div><h2>O que está a mudar</h2><p>Trajetória da tese, sem ocupar o ecrã principal.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-list">${rows.map(s=>renderRow(s,`${s.thesis_direction==='up'?'↑ A melhorar':'↓ A piorar'} · Δ30d ${num(s.thesis_score_delta_30d)}`)).join('')}</div>`;
      }
      if(tool==='compare'){
        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">COMPARAR</div><h2>Empresas lado a lado</h2><p>Escreve até 4 tickers, separados por vírgulas.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-compare-input"><input id="marketCompareInput" placeholder="MSFT, ASML.AS, NOVO-B.CO"><button class="btn btn--primary" id="marketCompareGo">Comparar</button></div><div id="marketCompareResult" style="margin-top:10px"></div>`;
      }
      if(tool==='news'){
        const p=portfolioTickers(); const picks=[...p].map(t=>M.byTicker.get(t)).filter(Boolean).slice(0,12);
        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">NOTÍCIAS</div><h2>Notícias das tuas posições</h2><p>Abre uma posição para ver o feed específico.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-list">${picks.length?picks.map(s=>renderRow(s,'Abrir notícias e dossier')).join(''):'<div class="market-empty">Sem posições reconhecidas.</div>'}</div>`;
      }
      if(tool==='scanner') c.innerHTML=renderScanner('best_opportunities');
    });
  }

  function compareNow(){
    const input=$m('marketCompareInput'), out=$m('marketCompareResult'); if(!input||!out)return;
    const ss=input.value.split(',').map(x=>M.byTicker.get(x.trim().toUpperCase())).filter(Boolean).slice(0,4);
    if(!ss.length){out.innerHTML='<div class="market-empty">Não encontrei esses tickers.</div>';return;}
    const metrics=[['Score','score',v=>num(v)],['Qualidade','quality_pct',v=>num(v)],['Growth','growth_pct',v=>num(v)],['Valuation','value_pct',v=>num(v)],['Forward P/E','forward_pe',v=>num(v)],['ROE','roe',v=>pct(v)],['Receita YoY','revenue_growth',v=>pct(v)]];
    out.innerHTML=`<div class="market-detail-card" style="overflow:auto"><table class="market-table"><thead><tr><th>Métrica</th>${ss.map(s=>`<th>${esc(s.ticker)}</th>`).join('')}</tr></thead><tbody>${metrics.map(([l,k,f])=>`<tr><td>${l}</td>${ss.map(s=>`<td>${f(s[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  function wireHorizontalRail(root){
    if(!root || root.dataset.railWired==='1') return;
    root.dataset.railWired='1';
    let sx=0, sy=0, sl=0, dragging=false, horizontal=false;
    root.addEventListener('touchstart',e=>{
      const t=e.touches&&e.touches[0]; if(!t)return;
      sx=t.clientX; sy=t.clientY; sl=root.scrollLeft; dragging=true; horizontal=false;
    },{passive:true});
    root.addEventListener('touchmove',e=>{
      if(!dragging)return; const t=e.touches&&e.touches[0]; if(!t)return;
      const dx=t.clientX-sx, dy=t.clientY-sy;
      if(!horizontal && Math.abs(dx)>8 && Math.abs(dx)>Math.abs(dy)*1.15) horizontal=true;
      if(horizontal){ root.scrollLeft=sl-dx; if(e.cancelable)e.preventDefault(); }
    },{passive:false});
    root.addEventListener('touchend',()=>{dragging=false;horizontal=false},{passive:true});
    root.addEventListener('touchcancel',()=>{dragging=false;horizontal=false},{passive:true});
  }
  function wireVisibleRails(){
    document.querySelectorAll('.market-chipbar,.market-tabs').forEach(wireHorizontalRail);
  }
  // v2.6: bounded grids no longer need custom touch interception.

  document.addEventListener('click', e=>{
    const marketNav=e.target.closest('[data-view="market"]'); if(marketNav) setTimeout(ensureLoaded,0);
    const mode=e.target.closest('[data-market-mode]'); if(mode){M.mode=mode.dataset.marketMode; document.querySelectorAll('[data-market-mode]').forEach(x=>x.classList.toggle('is-active',x===mode)); renderPrimary(); if(M.mode==='smart') loadCongressLive().then(()=>renderPrimary());}
    const sec=e.target.closest('[data-market-sector]'); if(sec){M.sector=sec.dataset.marketSector;renderPrimary();}
    const watch=e.target.closest('[data-market-watch]'); if(watch){e.preventDefault();e.stopPropagation();toggleWatch(watch.dataset.marketWatch);return;}
    const row=e.target.closest('[data-market-ticker]'); if(row){ hideSearchSuggestions(); ensureLoaded().then(()=>openTicker(row.dataset.marketTicker)); }
    const saveTargets=e.target.closest('[data-target-save]');
    if(saveTargets){
      const card=saveTargets.closest('[data-target-engine]');
      const targets={maxPosition:Math.max(3,Math.min(30,n(card?.querySelector('[data-target-position]')?.value)||10)),maxSector:Math.max(10,Math.min(60,n(card?.querySelector('[data-target-sector]')?.value)||25)),maxFactor:Math.max(20,Math.min(80,n(card?.querySelector('[data-target-factor]')?.value)||45)),maxCurrency:Math.max(30,Math.min(100,n(card?.querySelector('[data-target-currency]')?.value)||70)),maxRegion:Math.max(30,Math.min(100,n(card?.querySelector('[data-target-region]')?.value)||70)),overlap:card?.querySelector('[data-target-overlap]')?.value||'reduce',tilt:card?.querySelector('[data-target-tilt]')?.value||'balanced'};
      savePortfolioTargets(targets);
      const status=card?.querySelector('[data-target-status]'); if(status) status.textContent='Guardado · a recalcular';
      setTimeout(()=>openTool('portfolio'),120);
      return;
    }
    const stressBtn=e.target.closest('[data-stress-scenario]');
    if(stressBtn){
      const card=stressBtn.closest('.market-stress-test'), key=stressBtn.dataset.stressScenario;
      card?.querySelectorAll('[data-stress-scenario]').forEach(b=>b.classList.toggle('is-active',b===stressBtn));
      card?.querySelectorAll('[data-stress-panel]').forEach(p=>p.hidden=p.dataset.stressPanel!==key);
      return;
    }
    const freshRun=e.target.closest('[data-fresh-run]');
    if(freshRun){
      const card=freshRun.closest('[data-fresh-capital-card]'), out=card?.querySelector('[data-fresh-results]'), amount=card?.querySelector('[data-fresh-amount]')?.value;
      if(out) out.innerHTML=renderFreshCapitalPlan(freshCapitalPlan(amount));
      return;
    }
    const plan=e.target.closest('[data-rebalance-plan]');
    if(plan){
      const card=plan.closest('[data-rebalance-plan-card]'); const out=card?.querySelector('[data-rebalance-plan-results]');
      if(out) out.innerHTML=renderMultiMovePlan(buildMultiMovePlan());
      return;
    }
    const reb=e.target.closest('[data-rebalance-run]');
    if(reb){
      const card=reb.closest('[data-rebalancer-card]');
      const source=card?.querySelector('[data-rebalance-source]')?.value;
      const amount=card?.querySelector('[data-rebalance-amount]')?.value;
      const out=card?.querySelector('[data-rebalance-results]');
      if(out) out.innerHTML=renderRebalanceResults(rebalanceSimulation(source,amount));
      return;
    }
    const close=e.target.closest('[data-market-close]'); if(close) closeSheet();
    const sh=$m('marketSheet'); if(sh&&e.target===sh) closeSheet();
    const tab=e.target.closest('[data-detail-tab]'); if(tab&&sh?.dataset.ticker){
      sh.querySelectorAll('.market-tab').forEach(x=>x.classList.toggle('is-active',x===tab));
      const s=M.byTicker.get(sh.dataset.ticker.toUpperCase());
      if(s){ sh.dataset.liveReady='0'; renderDetailTab(s,tab.dataset.detailTab); }
    }
    const strat=e.target.closest('[data-scanner-strategy]'); if(strat){ const c=$m('marketSheetContent'); if(c)c.innerHTML=renderScanner(strat.dataset.scannerStrategy); return; }
    const tool=e.target.closest('[data-market-tool]'); if(tool) openTool(tool.dataset.marketTool);
    if(e.target.closest('#marketCompareGo')) compareNow();
    if(e.target.closest('[data-market-retry]')) { M.loaded=false; M.loading=null; ensureLoaded(); }
  });

  document.addEventListener('keydown', e=>{
    if(e.key==='Escape') closeSheet();
    if(e.key==='Enter' && e.target?.id==='marketSearch' && M.query){
      ensureLoaded().then(()=>{
        const exact=M.byTicker.get(M.query.toUpperCase());
        if(exact) openTicker(exact.ticker);
      });
    }
  });

  document.addEventListener('change', e=>{
    if(e.target.matches('[data-market-sector-select]') && e.target.value){ M.sector=e.target.value; renderPrimary(); }
  });

  document.addEventListener('input', e=>{
    if(e.target.id==='marketSearch'){
      M.query=e.target.value.trim(); ensureLoaded().then(()=>{ renderSearchSuggestions(); renderPrimary(); });
    }
  });


  document.addEventListener('focusin', e=>{
    if(e.target?.id==='marketSearch' && M.query) ensureLoaded().then(renderSearchSuggestions);
  });
  document.addEventListener('focusout', e=>{
    if(e.target?.id==='marketSearch') setTimeout(()=>{
      const active=document.activeElement;
      if(!active?.closest?.('#marketSuggestions')) hideSearchSuggestions();
    },140);
  });

  loadWatchlist();
  window.VestraMarket={ensureLoaded,openTicker,openPortfolioAsset,resolvePortfolioStock,toggleWatch};

  // v6.1 — Decision Center is a navigation surface, not a passive summary.
  document.addEventListener('click', e=>{
    const btn=e.target.closest?.('[data-decision-jump]');
    if(!btn) return;
    const kind=btn.dataset.decisionJump||'', value=btn.dataset.decisionValue||'';
    e.preventDefault();
    const scrollTo=el=>{ if(el) el.scrollIntoView?.({behavior:'smooth',block:'start'}); };
    if(kind==='ticker'&&value){ openTicker(value); return; }
    if(kind==='riskbudget'){ scrollTo(document.querySelector('.market-risk-budget')); return; }
    if(kind==='targets'){ scrollTo(document.querySelector('.market-target-fit')||document.querySelector('.market-target-engine')); return; }
    if(kind==='rebalancer'){ scrollTo(document.querySelector('.market-rebalancer')); return; }
    if(kind==='health'){ scrollTo(document.querySelector('.market-health-timeline')); return; }
    if(kind==='stress'){
      const box=document.querySelector('.market-stress-test'); scrollTo(box);
      const tab=box?.querySelector(`[data-stress-scenario="${CSS.escape(value||'rates')}"]`); tab?.click(); return;
    }
    if(kind==='actionmap'){
      const map=document.querySelector('.market-action-map'); scrollTo(map);
      if(value&&value!=='all'){ const filter=map?.querySelector(`[data-action-filter="${CSS.escape(value)}"]`); if(filter && !filter.classList.contains('is-active')) filter.click(); }
      return;
    }
  });

  // v6.2 — Research Queue state is local operational memory.
  document.addEventListener('click', e=>{
    const btn=e.target.closest?.('[data-queue-status]'); if(!btn)return;
    const row=btn.closest('.market-research-queue-row'); if(!row)return;
    e.preventDefault(); e.stopPropagation();
    setResearchQueueState(row.dataset.queueTicker||'',btn.dataset.queueStatus||'new');
    if(txt($m('marketSheet')?.dataset.tool)==='portfolio'){
      openTool('portfolio');
      setTimeout(()=>document.querySelector('.market-research-queue')?.scrollIntoView?.({behavior:'smooth',block:'start'}),0);
    } else renderPrimary();
  });

  // v6.3 — Thesis checkpoint + note for Research Queue.
  document.addEventListener('click', e=>{
    const btn=e.target.closest?.('[data-checkpoint-save]'); if(!btn)return;
    const box=btn.closest('.market-research-checkpoint'); if(!box)return;
    e.preventDefault(); e.stopPropagation();
    saveResearchCheckpoint(box.dataset.checkpointTicker||'',box.querySelector('[data-checkpoint-select]')?.value||'',box.querySelector('[data-checkpoint-note]')?.value||'');
    btn.textContent='Guardado'; setTimeout(()=>{btn.textContent='Guardar';},900);
  });

  // v6.0.1 — Action Map summary acts as an immediate filter.
  document.addEventListener('click', e=>{
    const btn=e.target.closest?.('[data-action-filter]');
    if(!btn) return;
    const map=btn.closest('.market-action-map');
    if(!map) return;
    e.preventDefault();
    const requested=btn.dataset.actionFilter||'';
    const active=map.dataset.actionFilter||'';
    const next=active===requested?'':requested;
    map.dataset.actionFilter=next;
    map.querySelectorAll('[data-action-filter]').forEach(x=>x.classList.toggle('is-active',next && x.dataset.actionFilter===next));
    let shown=0;
    map.querySelectorAll('.market-action-row[data-action-key]').forEach(row=>{
      const visible=!next || row.dataset.actionKey===next;
      row.hidden=!visible;
      if(visible) shown++;
    });
    map.querySelectorAll('.market-detail-disclosure').forEach(d=>{
      const any=[...d.querySelectorAll('.market-action-row[data-action-key]')].some(r=>!r.hidden);
      d.hidden=!!next && !any;
      d.open=!!next && any;
    });
    const status=map.querySelector('[data-action-filter-status]');
    if(status){
      const labels={reinforce:'a reforçar',hold:'a manter',review:'a rever',replace:'a substituir'};
      status.textContent=next?`${shown} ${shown===1?'posição':'posições'} ${labels[next]||''}`:'Mostrar todas as posições';
    }
    map.querySelector('.market-action-list')?.scrollIntoView?.({behavior:'smooth',block:'nearest'});
  });

})();
