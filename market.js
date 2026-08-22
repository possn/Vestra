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
      rows.sort((a,b)=>(n(b.score)||0)+dir(b)-(n(a.score)||0)-dir(a));
    } else rows.sort((a,b)=>(n(b.score)||0)-(n(a.score)||0));
    rows=rows.slice(0,20);
    return `<section class="market-section market-discover-section"><div class="market-section__head"><div><h3>${qs?'Resultados':'Ideias com melhor sinal'}</h3><p>${qs?'Pesquisa no universo global':'Qualidade, crescimento, balanço, cash flow e valuation'}</p></div><span class="market-data-age">${ageText()}</span></div>
      <div class="market-sector-grid" role="group" aria-label="Setores">
        <button class="market-chip ${M.sector==='all'?'is-active':''}" data-market-sector="all">Todos</button>
        ${visibleSectors.map(x=>`<button class="market-chip ${M.sector===x?'is-active':''}" data-market-sector="${esc(x)}" title="${esc(x)}">${esc(x)}</button>`).join('')}
        <label class="market-sector-more ${hiddenActive?'is-active':''}"><span>${hiddenActive?esc(M.sector):'Mais'}</span><select data-market-sector-select aria-label="Mais setores"><option value="">Mais setores</option>${moreSectors.map(x=>`<option value="${esc(x)}" ${M.sector===x?'selected':''}>${esc(x)}</option>`).join('')}</select></label>
      </div>
      <div class="market-list">${rows.length?rows.map(s=>renderRow(s)).join(''):'<div class="market-empty market-empty--filters"><strong>Sem resultados neste filtro.</strong><span>Experimenta outro setor ou remove a pesquisa.</span></div>'}</div></section>`;
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

  function renderPrimary(){
    const root=$m('marketPrimary'); if(!root || !M.loaded) return;
    root.innerHTML = M.mode==='funds'?renderFunds():M.mode==='smart'?renderSmart():M.mode==='watch'?renderWatch():renderDiscover();
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

  function dimRows(s){
    const dims=[['Qualidade',s.quality_pct],['Crescimento',s.growth_pct],['Balanço',s.balance_pct],['Cash flow',s.cashflow_pct],['Valuation',s.value_pct],['Estabilidade',s.stability_pct]];
    return dims.map(([k,v])=>`<div class="market-dim"><div><div class="market-dim__label"><span>${k}</span><strong>${n(v)==null?'—':Math.round(v)}</strong></div><div class="market-bar"><span style="width:${Math.max(0,Math.min(100,n(v)||0))}%"></span></div></div><span></span></div>`).join('');
  }

  function vestraRead(s){
    const score=n(s.score);
    const dims=[['Qualidade',s.quality_pct],['Crescimento',s.growth_pct],['Balanço',s.balance_pct],['Cash flow',s.cashflow_pct],['Valuation',s.value_pct],['Estabilidade',s.stability_pct]];
    const strengths=dims.filter(([,v])=>n(v)!=null&&n(v)>=68).sort((a,b)=>n(b[1])-n(a[1])).slice(0,2).map(([k])=>k);
    const cautions=dims.filter(([,v])=>n(v)!=null&&n(v)<48).sort((a,b)=>n(a[1])-n(b[1])).slice(0,2).map(([k])=>k);
    const direction=txt(s.thesis_direction);
    let label='Acompanhar', cls='is-watch', copy='Perfil intermédio: vale a pena abrir os pilares antes de tirar conclusões.';
    if(score!=null&&score>=72){label='Sinal forte';cls='';copy='Conjunto de métricas acima da média no universo Vestra, sujeito à qualidade e atualidade dos dados.';}
    else if(score!=null&&score<52){label='Mais exigente';cls='is-risk';copy='Há fragilidades relevantes nas métricas; o score pede análise adicional antes de qualquer decisão.';}
    if(isFund(s)) copy='Leitura agregada do fundo com foco em custo, qualidade e encaixe — não substitui análise da composição.';
    const signals=[];
    strengths.forEach(x=>signals.push(`<span class="market-signal">↑ ${esc(x)}</span>`));
    cautions.forEach(x=>signals.push(`<span class="market-signal market-signal--warn">! ${esc(x)}</span>`));
    if(direction==='up') signals.push('<span class="market-signal">↗ Tese a melhorar</span>');
    if(direction==='down') signals.push('<span class="market-signal market-signal--warn">↘ Tese a piorar</span>');
    if(n(s.insider_buy_count_30d)>0) signals.push('<span class="market-signal market-signal--gold">Insiders a comprar</span>');
    return `<div class="market-verdict"><div class="market-verdict__score ${cls}">${score==null?'—':Math.round(score)}</div><div class="market-verdict__copy"><small>Leitura Vestra</small><strong>${label}</strong><p>${copy}</p>${signals.length?`<div class="market-signal-row">${signals.slice(0,4).join('')}</div>`:''}</div></div>`;
  }

  function shortDate(v){
    if(!v) return '—'; const d=new Date(v); if(Number.isNaN(d.valueOf())) return esc(v);
    return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short',year:'numeric'}).format(d);
  }



  function investmentCase(s){
    const evidence=Array.isArray(s.thesis_evidence)?s.thesis_evidence.filter(Boolean):[];
    const drivers=Array.isArray(s.thesis_evolution_drivers)?s.thesis_evolution_drivers.filter(Boolean):[];
    const risks=Array.isArray(s.thesis_risks)?s.thesis_risks.filter(Boolean):[];
    const dims=[['Qualidade',s.quality_pct],['Crescimento',s.growth_pct],['Balanço',s.balance_pct],['Cash flow',s.cashflow_pct],['Valuation',s.value_pct],['Estabilidade',s.stability_pct]];
    const weak=dims.filter(([,v])=>n(v)!=null&&n(v)<48).sort((a,b)=>n(a[1])-n(b[1])).map(([k,v])=>`${k} ${Math.round(n(v))}/100`);
    const fwdVs=n(s.forward_pe_vs_sector_pct), trailVs=n(s.trailing_pe_vs_sector_pct), evVs=n(s.ev_ebitda_vs_sector_pct);
    const valuationDelta=fwdVs??trailVs??evVs;
    let valuation='Sem leitura relativa suficiente', valuationClass='';
    if(valuationDelta!=null){
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
    if(txt(s.thesis_direction)==='up') watch.push('Tese quantitativa a melhorar');
    if(txt(s.thesis_direction)==='down') watch.push('Tese quantitativa a piorar');
    const why=evidence.length?evidence.slice(0,3):[s.thesis_summary||s.business_summary||'Ainda não existe evidência suficiente para resumir a tese.'];
    const catalysts=drivers.length?drivers.slice(0,3):[txt(s.thesis_evolution_summary)||'Sem catalisador quantitativo claro identificado nos dados atuais.'];
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
    if(tab==='overview') body.innerHTML=`${changePanel(s)}${investmentCase(s)}<details class="market-detail-disclosure"><summary>Ver pilares e detalhe quantitativo</summary><div class="market-detail-card"><h4>Pilares</h4>${dimRows(s)}</div>${Array.isArray(s.thesis_risks)&&s.thesis_risks.length?`<div class="market-detail-card"><h4>Riscos adicionais</h4><ul>${s.thesis_risks.slice(0,6).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}</details>`;
    if(tab==='perspective') {
      const buys=(n(s.analyst_strong_buy)||0)+(n(s.analyst_buy)||0), holds=n(s.analyst_hold)||0, sells=(n(s.analyst_sell)||0)+(n(s.analyst_strong_sell)||0);
      const revUp=n(s.analyst_eps_revisions_up_30d)||0, revDown=n(s.analyst_eps_revisions_down_30d)||0;
      body.innerHTML=`<div class="market-detail-card market-perspective-card"><div class="market-perspective-head"><div><small>CONSENSO</small><h4>O que o mercado espera</h4></div><span class="market-consensus ${buys>sells?'is-positive':sells>buys?'is-negative':''}">${buys>sells?'Viés positivo':sells>buys?'Viés cauteloso':'Neutro'}</span></div><div class="market-metrics"><div class="market-metric"><small>Target médio</small><strong>${money(s.analyst_price_target_mean,s.currency)}</strong></div><div class="market-metric"><small>Upside target</small><strong>${pct(s.analyst_price_target_upside_pct)}</strong></div><div class="market-metric"><small>Próx. earnings</small><strong>${shortDate(s.analyst_next_earnings_date)}</strong></div><div class="market-metric"><small>EPS próximo ano</small><strong>${pct(s.analyst_eps_next_y_growth)}</strong></div><div class="market-metric"><small>Rev. EPS 30d</small><strong>${revUp} ↑ · ${revDown} ↓</strong></div><div class="market-metric"><small>Última surpresa</small><strong>${pct(s.analyst_latest_eps_surprise_pct)}</strong></div></div></div><div class="market-detail-card"><h4>Analistas</h4><div class="market-consensus-bar"><span class="is-buy" style="flex:${Math.max(0,buys)}"></span><span class="is-hold" style="flex:${Math.max(0,holds)}"></span><span class="is-sell" style="flex:${Math.max(0,sells)}"></span></div><div class="market-consensus-legend"><span>${buys} Comprar</span><span>${holds} Manter</span><span>${sells} Vender</span></div><p style="margin-top:10px">Estimativas são contexto, não recomendação. Dá mais peso à direção das revisões e à execução real do negócio do que ao target isolado.</p></div>`;
    }
    if(tab==='growth') body.innerHTML=`<div class="market-detail-card"><h4>Crescimento e resultados</h4><div class="market-metrics"><div class="market-metric"><small>Receita YoY</small><strong>${pct(s.revenue_yoy_latest??s.revenue_growth)}</strong></div><div class="market-metric"><small>Lucro YoY</small><strong>${pct(s.net_income_yoy_latest??s.earnings_growth)}</strong></div><div class="market-metric"><small>EPS YoY</small><strong>${pct(s.eps_yoy_latest??s.eps_growth)}</strong></div><div class="market-metric"><small>Margem líquida</small><strong>${pct(s.net_margin_latest??s.profit_margin)}</strong></div><div class="market-metric"><small>ROCE proxy</small><strong>${pct(s.roce_proxy)}</strong></div><div class="market-metric"><small>FCF</small><strong>${compact(s.free_cash_flow)}</strong></div></div></div>`;
    if(tab==='valuation') body.innerHTML=`<div class="market-detail-card"><h4>Valuation</h4><div class="market-metrics"><div class="market-metric"><small>P/E</small><strong>${num(s.trailing_pe)}</strong></div><div class="market-metric"><small>Forward P/E</small><strong>${num(s.forward_pe)}</strong></div><div class="market-metric"><small>P/B</small><strong>${num(s.price_to_book)}</strong></div><div class="market-metric"><small>EV/EBITDA</small><strong>${num(s.enterprise_to_ebitda)}</strong></div><div class="market-metric"><small>vs sector P/E</small><strong>${pct(s.trailing_pe_vs_sector_pct)}</strong></div><div class="market-metric"><small>Dividend yield</small><strong>${pct(s.dividend_yield)}</strong></div></div></div>`;
    if(tab==='earnings') {
      const hist=Array.isArray(s.analyst_earnings_history_4q)?s.analyst_earnings_history_4q.slice(0,4):[];
      body.innerHTML=`<div class="market-detail-card"><h4>Resultados e catalisadores</h4><div class="market-metrics"><div class="market-metric"><small>Próx. resultados</small><strong>${shortDate(s.analyst_next_earnings_date)}</strong></div><div class="market-metric"><small>Dias até earnings</small><strong>${n(s.analyst_days_to_earnings)==null?'—':Math.round(n(s.analyst_days_to_earnings))}</strong></div><div class="market-metric"><small>Última surpresa EPS</small><strong>${pct(s.analyst_latest_eps_surprise_pct)}</strong></div><div class="market-metric"><small>Beats 4T</small><strong>${n(s.analyst_earnings_beats_4q)==null?'—':Math.round(n(s.analyst_earnings_beats_4q))}</strong></div><div class="market-metric"><small>Misses 4T</small><strong>${n(s.analyst_earnings_misses_4q)==null?'—':Math.round(n(s.analyst_earnings_misses_4q))}</strong></div><div class="market-metric"><small>Surpresa média 4T</small><strong>${pct(s.analyst_earnings_avg_surprise_4q)}</strong></div></div>${hist.length?`<div class="market-earnings-list">${hist.map(x=>`<div><span>${shortDate(x.date||x.earnings_date)}</span><strong>${pct(x.surprise_pct??x.eps_surprise_pct)}</strong></div>`).join('')}</div>`:''}</div>`;
    }
    if(tab==='financials') body.innerHTML=`<div class="market-detail-card"><h4>Saúde financeira</h4><div class="market-metrics"><div class="market-metric"><small>Margem bruta</small><strong>${pct(s.gross_margin)}</strong></div><div class="market-metric"><small>Margem operacional</small><strong>${pct(s.operating_margin)}</strong></div><div class="market-metric"><small>Margem líquida</small><strong>${pct(s.profit_margin)}</strong></div><div class="market-metric"><small>Debt / Equity</small><strong>${num(s.debt_to_equity)}</strong></div><div class="market-metric"><small>Current ratio</small><strong>${num(s.current_ratio)}</strong></div><div class="market-metric"><small>Quick ratio</small><strong>${num(s.quick_ratio)}</strong></div><div class="market-metric"><small>Cash flow operacional</small><strong>${compact(s.operating_cash_flow)}</strong></div><div class="market-metric"><small>Free cash flow</small><strong>${compact(s.free_cash_flow)}</strong></div><div class="market-metric"><small>Net cash / dívida</small><strong>${compact(s.net_cash)}</strong></div></div></div>`;
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
      const items=M.news?.tickers?.[s.ticker]||[];
      body.innerHTML=`<div class="market-detail-card"><h4>Notícias recentes</h4>${items.length?items.slice(0,10).map(x=>`<div class="market-news-item"><a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.title)}</a><small>${esc(x.source||'')} · ${esc(x.published||'')}</small></div>`).join(''):'<p>Sem notícias recentes para este ticker.</p>'}</div>`;
    }catch{ body.innerHTML='<div class="market-empty">Não foi possível carregar notícias.</div>'; }
  }

  function sheetPanel(){ return $m('marketSheet')?.querySelector('.market-sheet__panel')||null; }
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
    sh.hidden=true; sh.setAttribute('aria-hidden','true'); sh.dataset.liveReady='0';
    document.documentElement.classList.remove('modal-open'); document.body.classList.remove('modal-open');
    const panel=sheetPanel(); if(panel){panel.scrollTop=0;panel.scrollLeft=0;}
  }

  function openTool(tool){
    ensureLoaded().then(()=>{
      const sh=$m('marketSheet'), c=$m('marketSheetContent'); if(!sh||!c)return;
      sh.hidden=false; sh.setAttribute('aria-hidden','false'); document.body.classList.add('modal-open'); sh.dataset.ticker='';
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
    const close=e.target.closest('[data-market-close]'); if(close) closeSheet();
    const sh=$m('marketSheet'); if(sh&&e.target===sh) closeSheet();
    const tab=e.target.closest('[data-detail-tab]'); if(tab&&sh?.dataset.ticker){
      sh.querySelectorAll('.market-tab').forEach(x=>x.classList.toggle('is-active',x===tab));
      const s=M.byTicker.get(sh.dataset.ticker.toUpperCase());
      if(s){ sh.dataset.liveReady='0'; renderDetailTab(s,tab.dataset.detailTab); }
    }
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
})();
