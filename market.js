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
    fundTheme: '',
    fundLimit: 100,
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
  function notifyMarketSheetChanged(reason='update'){
    try { window.dispatchEvent(new CustomEvent('vestra:market-sheet-changed',{detail:{reason}})); } catch (_) {}
  }
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

  const portfolioContext = window.VestraMarketPortfolioContext?.create({
  getAssets: () => {
    try { return (typeof state !== 'undefined' && state && Array.isArray(state.assets)) ? state.assets : []; }
    catch { return []; }
  },
  text: txt,
  number: n,
}) || null;
function portfolioAssets(){ return portfolioContext?.portfolioAssets() || []; }
function researchEligibleAsset(a){ return portfolioContext?.researchEligibleAsset(a) || false; }
function assetTicker(a){ return portfolioContext?.assetTicker(a) || ''; }
function portfolioTickers(){ return portfolioContext?.portfolioTickers() || new Set(); }
function portfolioValue(a){ return portfolioContext?.portfolioValue(a) ?? 0; }
function researchUniverseValue(assets=portfolioAssets()){ return (assets||[]).filter(researchEligibleAsset).reduce((sum,a)=>sum+portfolioValue(a),0); }
function euro(v){ return portfolioContext?.euro(v) || '—'; }
function inPortfolio(ticker){ return portfolioContext?.inPortfolio(ticker) || false; }

  function workerBase(){
    try { return txt((typeof state!=='undefined' && state?.settings?.workerUrl) || window.VestraRuntimeConfig?.workerUrl).replace(/\/$/,''); } catch { return txt(window.VestraRuntimeConfig?.workerUrl).replace(/\/$/,''); }
  }
  const marketLiveOverlay=window.VestraMarketLiveOverlay?.create({
    getWorkerBase:workerBase,
    getSheet:()=> $m('marketSheet'),
    loadingSet:M.liveLoading,
    text:txt,
    escapeHtml:esc,
    formatMoney:money,
    formatNum:num,
    formatPct:pct,
  })||null;
  function compactLiveBadge(s){ return marketLiveOverlay?.compactLiveBadge(s)||''; }
  function refreshOpenDossierLiveFields(s){ return marketLiveOverlay?.refreshOpenDossierLiveFields(s); }
  async function enrichTickerLive(s){ return marketLiveOverlay?.enrichTickerLive(s)??null; }




  const congressLiveState = {};
  Object.defineProperties(congressLiveState, {
    trades: { get: () => M.congressLive, set: value => { M.congressLive = Array.isArray(value) ? value : []; } },
    loaded: { get: () => M.congressLoaded, set: value => { M.congressLoaded = Boolean(value); } },
    loading: { get: () => M.congressLoading, set: value => { M.congressLoading = value || null; } },
    error: { get: () => M.congressError, set: value => { M.congressError = txt(value); } },
  });
  const congressLiveFeed = window.VestraMarketCongressLive?.create({
    state: congressLiveState,
    getStocksByTicker: () => M.byTicker,
    getStocks: () => M.stocks,
    text: txt,
  }) || null;
  async function loadCongressLive(ticker=''){ return congressLiveFeed?.load(ticker) ?? []; }


  const watchSnapshotState = {};
Object.defineProperties(watchSnapshotState, {
  watchlist: { get: () => M.watchlist, set: value => { M.watchlist = value instanceof Set ? value : new Set(); } },
  previousSnapshot: { get: () => M.previousSnapshot, set: value => { M.previousSnapshot = value || null; } },
  currentSnapshot: { get: () => M.currentSnapshot, set: value => { M.currentSnapshot = value || null; } },
});
const watchSnapshots = window.VestraMarketWatchSnapshots?.create({
  state: watchSnapshotState,
  text: txt,
  number: n,
  escapeHtml: esc,
  formatShortDate: shortDate,
  getPortfolioTickers: portfolioTickers,
  getStocksByTicker: () => M.byTicker,
  getStocks: () => M.stocks,
  getGeneratedAt: () => M.data?.generated_at,
}) || null;
function loadWatchlist(){ return watchSnapshots?.loadWatchlist() || M.watchlist; }
function saveWatchlist(){ return watchSnapshots?.saveWatchlist(); }
function isWatched(ticker){ return watchSnapshots?.isWatched(ticker) || false; }
function toggleWatch(ticker){
  const t=txt(ticker).toUpperCase(); if(!t) return;
  if(M.watchlist.has(t)) M.watchlist.delete(t); else M.watchlist.add(t);
  saveWatchlist(); if(M.loaded) syncSnapshots(); renderPrimary();
  const sh=$m('marketSheet');
  if(sh && sh.dataset.ticker && sh.dataset.ticker.toUpperCase()===t){
    const s=M.byTicker.get(t); if(s){ const active=sh.querySelector('.market-tab.is-active')?.dataset.detailTab||'overview'; $m('marketSheetContent').innerHTML=detailBase(s); renderDetailTab(s,active); const tab=sh.querySelector(`[data-detail-tab="${active}"]`); if(tab){sh.querySelectorAll('.market-tab').forEach(x=>x.classList.toggle('is-active',x===tab));} notifyMarketSheetChanged('ticker-rerender'); }
  }
}
function snapshotStock(s){ return watchSnapshots?.snapshotStock(s) || {}; }
function buildSnapshot(){ return watchSnapshots?.buildSnapshot() || {generatedAt:'',savedAt:new Date().toISOString(),stocks:{}}; }
function syncSnapshots(){ return watchSnapshots?.syncSnapshots() || null; }
function previousFor(s){ return watchSnapshots?.previousFor(s) || null; }
function daysUntil(v){ return watchSnapshots?.daysUntil(v) ?? null; }
function changeSignals(s){ return watchSnapshots?.changeSignals(s) || []; }
function changeBadge(s){ return watchSnapshots?.changeBadge(s) || ''; }
function changePanel(s){ return watchSnapshots?.changePanel(s) || ''; }

  const marketRowUI = window.VestraMarketRowUI?.create({
  text: txt,
  number: n,
  escapeHtml: esc,
  getGeneratedAt: () => M.data?.generated_at,
  inPortfolio,
  isWatched,
  changeBadge,
}) || null;
function isFund(s){ return marketRowUI?.isFund(s) || false; }
function scoreClass(value){ return marketRowUI?.scoreClass(value) || 'market-score--soft'; }
function ageText(){ return marketRowUI?.ageText() || ''; }

  const staticUniverseState = {};
  Object.defineProperties(staticUniverseState, {
    loaded: { get: () => M.loaded, set: value => { M.loaded = Boolean(value); } },
    loading: { get: () => M.loading, set: value => { M.loading = value || null; } },
    data: { get: () => M.data, set: value => { M.data = value || null; } },
    stocks: { get: () => M.stocks, set: value => { M.stocks = Array.isArray(value) ? value : []; } },
    byTicker: { get: () => M.byTicker, set: value => { M.byTicker = value instanceof Map ? value : new Map(); } },
  });
  const staticUniverse = window.VestraMarketStaticUniverse?.create({
    state: staticUniverseState,
    text: txt,
    beforeReady: syncSnapshots,
    onReady: renderPrimary,
    onError: err => {
      const el=$m('marketPrimary'); if(el) el.innerHTML=`<div class="market-empty market-empty--error"><strong>Mercado indisponível</strong><br><span>Não foi possível carregar os dados agora.</span><br><button class="btn btn--outline btn--sm" data-market-retry style="margin-top:12px">Tentar novamente</button><small class="market-error-detail">${esc(err.message)}</small></div>`;
    },
  }) || null;
  async function ensureLoaded(){ return staticUniverse?.ensureLoaded(); }

  function upsertRemoteStock(row={}){
    const ticker=txt(row.ticker||row.symbol).toUpperCase();
    if(!ticker) return null;
    const existing=M.byTicker.get(ticker);
    const stock=existing||{ticker};
    const incoming={...row,ticker};
    if(n(incoming.current_price)==null && n(incoming.price)!=null) incoming.current_price=n(incoming.price);
    if(incoming.quote_type) incoming.quote_type=txt(incoming.quote_type).toUpperCase();
    if(!incoming.name) incoming.name=existing?.name||ticker;
    Object.assign(stock,incoming,{
      ticker,
      _remoteTransient:true,
      _dossierHydrated:true,
      _dossierHydrationError:'',
      _remoteLoading:!!incoming._remoteLoading,
    });
    if(!existing) M.stocks.push(stock);
    M.byTicker.set(ticker,stock);
    return stock;
  }

    function renderRow(s, meta='', displayScore=null){ return marketRowUI?.renderRow(s,meta,displayScore) || ''; }

  const WEEKLY_ROTATION_THEMES=[
    ['Semicondutores',/semiconductor|semiconductors|chip|foundry|wafer|integrated circuit/i],
    ['Biotecnologia',/biotech|biotechnology|genomic|genomics|gene therap|life sciences/i],
    ['Minerais & metais',/metal|mining|miner|copper|lithium|uranium|gold|silver|steel|aluminum|aluminium|rare earth/i],
    ['Agricultura',/agricultur|agribusiness|farm|crop|seed|fertili[sz]er|grain|potash/i],
    ['Energia',/energy|oil|gas|petroleum|exploration|drilling|refin/i],
    ['Defesa & aeroespacial',/defen[cs]e|aerospace|military|weapon|missile/i],
    ['IA & software',/artificial intelligence|machine learning|software|cloud|saas|cyber|data infrastructure/i],
    ['Bancos',/bank|banks|banking|financial services/i],
    ['Imobiliário',/real estate|reit|property/i],
    ['Consumo discricionário',/consumer cyclical|consumer discretionary|auto manufacturer|travel|leisure|retail/i],
  ];
  const WEEKLY_ROTATION_ETFS={
    'Semicondutores':['SMH','SOXX','XSD'],
    'Biotecnologia':['XBI','IBB','ARKG'],
    'Minerais & metais':['COPX','PICK'],
    'Agricultura':[],
    'Energia':['XLE','XOP'],
    'Defesa & aeroespacial':['ITA','PPA','XAR'],
    'IA & software':['IGV','AIQ','BOTZ','CHAT','WCLD'],
    'Bancos':['KBE','KRE','XLF'],
    'Imobiliário':['VNQ','IYR','XLRE'],
    'Consumo discricionário':['XLY','VCR'],
  };
  function weeklyEtfConsensus(expectedSign, etfReturn, flowUsd){
    if(expectedSign!==1&&expectedSign!==-1) return {confirmed:null,evidenceCount:0};
    const directional=[etfReturn,flowUsd]
      .filter(v=>v!=null&&v!==0)
      .map(v=>v>0?1:-1);
    if(!directional.length) return {confirmed:null,evidenceCount:0};
    if(!directional.every(sign=>sign===expectedSign)) return {confirmed:false,evidenceCount:directional.length};
    const flowSign=flowUsd!=null&&flowUsd!==0?(flowUsd>0?1:-1):0;
    return {confirmed:flowSign===expectedSign?true:null,evidenceCount:directional.length};
  }
  function weeklyEtfConfirmation(label,expectedSign=0){
    const tickers=WEEKLY_ROTATION_ETFS[label]||[];
    const funds=tickers.map(t=>M.byTicker.get(t)).filter(Boolean);
    const withFlow=funds.filter(f=>n(f.fund_flow_1w_usd)!=null);
    const withReturn=funds.filter(f=>n(f.fund_return_1w_pct)!=null);
    const flowUsd=withFlow.length?withFlow.reduce((a,f)=>a+n(f.fund_flow_1w_usd),0):null;
    const etfReturn=withReturn.length?rotationMedian(withReturn.map(f=>n(f.fund_return_1w_pct)).filter(x=>x!=null)):null;
    const flowWindows=withFlow.map(f=>n(f.fund_flow_observation_days)).filter(x=>x!=null&&x>0).sort((a,b)=>a-b);
    const flowWindowMin=flowWindows.length?flowWindows[0]:null;
    const flowWindowMax=flowWindows.length?flowWindows[flowWindows.length-1]:null;
    const consensus=weeklyEtfConsensus(expectedSign,etfReturn,flowUsd);
    return {withFlow:withFlow.length,withReturn:withReturn.length,flowUsd,etfReturn,flowWindowMin,flowWindowMax,...consensus};
  }
  function compactFlowUsd(v){
    if(v==null)return 'baseline';
    const sign=v>=0?'+':'-'; const x=Math.abs(v);
    if(x>=1e9)return sign+'$'+(x/1e9).toFixed(1)+'B';
    if(x>=1e6)return sign+'$'+(x/1e6).toFixed(0)+'M';
    if(x>=1e3)return sign+'$'+(x/1e3).toFixed(0)+'K';
    return sign+'$'+x.toFixed(0);
  }
  function rotationEtfText(r){
    const e=r?.etf;
    const state=e?.confirmed===true?'ETF confirma':e?.confirmed===false?'ETF diverge':'ETF sem confirmação';
    const flowWindow=e?.flowWindowMin==null?'':e.flowWindowMin===e.flowWindowMax?' · janela '+Math.round(e.flowWindowMin)+'d':' · janela '+Math.round(e.flowWindowMin)+'–'+Math.round(e.flowWindowMax)+'d';
    if(e?.withFlow)return state+' · flow '+compactFlowUsd(e.flowUsd)+' · '+e.withFlow+' fundos'+flowWindow;
    if(e?.withReturn)return state+' · retorno '+(e.etfReturn>=0?'+':'')+e.etfReturn.toFixed(1)+'% · flow a formar baseline';
    return 'ETF sem cobertura';
  }

  function weeklyRotationReturn(stock){
    return n(stock?.market_return_5d_pct);
  }
  function rotationMedian(values){
    const xs=values.filter(v=>Number.isFinite(v)).sort((a,b)=>a-b);
    if(!xs.length) return null;
    const m=Math.floor(xs.length/2);
    return xs.length%2?xs[m]:(xs[m-1]+xs[m])/2;
  }
  function weeklyRotationCoverage(){
    const stocks=M.stocks.filter(s=>!isFund(s)&&txt(s.zombie)!=='yes');
    const rows=WEEKLY_ROTATION_THEMES.map(([label,re])=>{
      const members=stocks.filter(s=>re.test(`${txt(s.sector)} ${txt(s.industry)} ${txt(s.name)}`));
      const weekly=members.filter(s=>weeklyRotationReturn(s)!=null);
      return {label,members:members.length,weekly:weekly.length,ready:weekly.length>=4};
    });
    return {total:rows.length,ready:rows.filter(x=>x.ready).length,pending:rows.filter(x=>!x.ready),rows};
  }
  function weeklyRotationThemeRows(){
    const stocks=M.stocks.filter(s=>!isFund(s)&&txt(s.zombie)!=='yes');
    const rows=[];
    for(const [label,re] of WEEKLY_ROTATION_THEMES){
      const members=stocks.filter(s=>re.test(`${txt(s.sector)} ${txt(s.industry)} ${txt(s.name)}`));
      const weekly=members.map(s=>({stock:s,r5:weeklyRotationReturn(s),r20:n(s.market_return_20d_pct)})).filter(x=>x.r5!=null);
      if(weekly.length<4) continue;
      const med5=rotationMedian(weekly.map(x=>x.r5));
      const breadth=weekly.filter(x=>x.r5>0).length/weekly.length*100;
      const med20=rotationMedian(weekly.map(x=>x.r20).filter(x=>x!=null));
      const rank=(med5||0)*1.4+(breadth-50)*.08+(med20||0)*.25;
      let signal='Rotação mista',tone='neutral',expectedEtfSign=0;
      if(med5>=2&&breadth>=60){signal='Entrada forte',tone='positive',expectedEtfSign=1;}
      else if(med5>=.5&&breadth>=55){signal='A receber capital',tone='positive',expectedEtfSign=1;}
      else if(med5<=-2&&breadth<=40){signal='Saída forte',tone='risk',expectedEtfSign=-1;}
      else if(med5<=-.5&&breadth<=45){signal='A perder capital',tone='risk',expectedEtfSign=-1;}
      else if(med5>0){signal='A melhorar',tone='warn';}
      else if(med5<0){signal='A enfraquecer',tone='warn';}
      const etf=weeklyEtfConfirmation(label,expectedEtfSign);
      rows.push({label,count:weekly.length,med5,breadth,med20,rank,signal,tone,etf});
    }
    return rows.sort((a,b)=>b.rank-a.rank);
  }
  function renderRotationRow(r, rank){
    return `<div class="market-rotation-row is-${r.tone}"><div class="market-rotation-rank">${rank}</div><div class="market-rotation-name"><strong>${esc(r.label)}</strong><small>${esc(r.signal)} · ${r.count} ações</small><em>${esc(rotationEtfText(r))}</em></div><div class="market-rotation-bar"><i style="width:${Math.max(4,Math.min(100,r.breadth))}%"></i><small>breadth ${r.breadth.toFixed(0)}%</small></div><div class="market-rotation-metrics"><strong>${r.med5>=0?'+':''}${r.med5.toFixed(1)}%</strong><small>5d mediano${r.med20!=null?` · 20d ${r.med20>=0?'+':''}${r.med20.toFixed(1)}%`:''}</small></div></div>`;
  }
  function renderRotationGroup(title, subtitle, rows, tone, emptyText){
    if(!rows.length) return `<div class="market-rotation-group market-rotation-group--empty market-rotation-group--${tone}"><div class="market-rotation-group__head market-rotation-group__head--compact"><strong>${esc(title)}</strong><small>${esc(emptyText)}</small></div></div>`;
    return `<div class="market-rotation-group market-rotation-group--${tone}"><div class="market-rotation-group__head"><strong>${esc(title)}</strong><small>${esc(subtitle)}</small></div><div class="market-rotation-grid">${rows.map((r,i)=>renderRotationRow(r,i+1)).join('')}</div></div>`;
  }
  function renderWeeklyRotation(){
    const rows=weeklyRotationThemeRows(), coverage=weeklyRotationCoverage();
    if(!rows.length) return `<div class="market-rotation market-rotation--waiting" aria-live="polite"><div class="market-perspective-head"><div><small>WEEKLY ROTATION · 5D</small><h4>Para onde está a rodar o mercado?</h4></div><span class="market-rotation-status">A preparar</span></div><div class="market-rotation-wait"><span class="market-rotation-wait-copy">A formar a primeira leitura semanal.</span></div></div>`;
    const inflows=rows.filter(r=>r.med5>0 && r.breadth>=50).slice(0,3);
    const medianRank=rotationMedian(rows.map(r=>r.rank));
    const relativeDestinations=!inflows.length
      ?rows.filter(r=>r.rank>medianRank).slice(0,3).map(r=>({
        ...r,
        signal:r.med5<0?'Mais resiliente · ainda negativo':'A ganhar força relativa',
        tone:'neutral'
      }))
      :[];
    const relativeLabels=new Set(relativeDestinations.map(r=>r.label));
    const outflows=rows
      .filter(r=>r.med5<0 && r.breadth<=50 && !relativeLabels.has(r.label))
      .sort((a,b)=>a.rank-b.rank)
      .slice(0,3);
    const pending=coverage.pending.map(x=>x.label).slice(0,4);
    const pendingText=pending.length?`Ainda a formar série: ${esc(pending.join(', '))}${coverage.pending.length>pending.length?` +${coverage.pending.length-pending.length}`:''}. Um tema só entra no ranking com ≥4 ações com retorno semanal.`:'Todos os temas têm cobertura semanal suficiente.';
    const relativeBlock=relativeDestinations.length
      ?renderRotationGroup('A ganhar força relativa','Melhor rank relativo · não implica entrada líquida',relativeDestinations,'relative','')
      :'';
    return `<div class="market-rotation"><div class="market-perspective-head"><div><small>WEEKLY ROTATION · 5D</small><h4>Para onde está a rodar o mercado?</h4></div><span class="market-data-age">${coverage.ready}/${coverage.total} temas · 5d</span></div>${renderRotationGroup('Entradas por preço','Retorno 5d positivo · breadth ≥50%',inflows,'in','Sem entradas por preço esta semana')}${relativeBlock}${renderRotationGroup('Saídas por preço','Retorno 5d negativo · breadth ≤50%',outflows,'out','Sem saídas por preço esta semana')}<details class="market-rotation-method"><summary>Como é calculado?</summary><div class="market-rotation-method__body"><p>O ranking combina retorno 5d, breadth e retorno 20d. A direção principal continua a ser definida por preço + breadth.</p><p>Quando não existem entradas absolutas, mostramos os temas acima da mediana do rank como destinos relativos. Isto identifica onde o mercado está a resistir/melhorar mais, sem chamar “entrada” a um retorno ainda negativo.</p><p>A confirmação ETF compara a direção do retorno semanal e do flow com o sinal de preço: só diz “ETF confirma” quando toda a evidência direcional disponível concorda; qualquer contradição aparece como “ETF diverge”. O flow resulta da variação de AUM ajustada ao retorno e não representa subscrições/resgates diretamente observados.</p><p>${pendingText}</p></div></details></div>`;
  }

  function renderDiscover(){
    const sectors = [...new Set(M.stocks.filter(s=>!isFund(s)&&s.sector).map(s=>s.sector))].sort();
    const preferred = ['Technology','Financial Services','Healthcare','Industrials','Consumer Cyclical','Basic Materials'];
    const visibleSectors = preferred.filter(x=>sectors.includes(x));
    for(const x of sectors){ if(visibleSectors.length>=6) break; if(!visibleSectors.includes(x)) visibleSectors.push(x); }
    const moreSectors = sectors.filter(x=>!visibleSectors.includes(x));
    const hiddenActive = M.sector!=='all' && !visibleSectors.includes(M.sector);
    const qs = M.query.toLowerCase();
    const canonicalOpportunityRenderer=!qs&&!!window.VestraMarketOpportunities?.refresh;
    let rows = [];
    if(!canonicalOpportunityRenderer){
      rows=M.stocks.filter(s=>!isFund(s));
      if(qs) rows=rows.filter(s=>`${s.ticker} ${s.name} ${s.sector} ${s.industry}`.toLowerCase().includes(qs));
      else rows=rows.filter(s=>n(s.opportunity_score)!=null && s.opportunity_eligible===true && n(s.opportunity_timing_score)>=55 && s.opportunity_overextended!==true && n(s.data_coverage_pct)>=55 && n(s.confidence_score)>=50 && txt(s.zombie)!=='yes');
      if(M.sector!=='all') rows=rows.filter(s=>s.sector===M.sector);
      if(!qs){
        rows.sort((a,b)=>{
          const ob=n(b.opportunity_score)||0, oa=n(a.opportunity_score)||0;
          if(ob!==oa) return ob-oa;
          return (n(b.opportunity_timing_score)||0)-(n(a.opportunity_timing_score)||0);
        });
      } else rows.sort((a,b)=>(n(b.score)||0)-(n(a.score)||0));
      rows=rows.slice(0,20);
    }
    return `<section class="market-section market-discover-section"><div class="market-section__head"><div><h3>${qs?'Resultados':'Melhores oportunidades'}</h3><p>${qs?'Pesquisa no universo global':'Oportunidades emergentes · empresas robustas com momentum a começar, sem preço excessivamente esticado'}</p></div><span class="market-data-age">${ageText()}</span></div>
      ${!qs&&M.sector==='all'?renderWeeklyRotation():''}
      <div class="market-sector-grid" role="group" aria-label="Setores">
        <button class="market-chip ${M.sector==='all'?'is-active':''}" data-market-sector="all">Todos</button>
        ${visibleSectors.map(x=>`<button class="market-chip ${M.sector===x?'is-active':''}" data-market-sector="${esc(x)}" title="${esc(x)}">${esc(x)}</button>`).join('')}
        <label class="market-sector-more ${hiddenActive?'is-active':''}"><span>${hiddenActive?esc(M.sector):'Mais'}</span><select data-market-sector-select aria-label="Mais setores"><option value="">Mais setores</option>${moreSectors.map(x=>`<option value="${esc(x)}" ${M.sector===x?'selected':''}>${esc(x)}</option>`).join('')}</select></label>
      </div>
      <div class="market-list">${canonicalOpportunityRenderer?'':rows.length?rows.map(s=>renderRow(s,qs?'':[`Opportunity ${Math.round(n(s.opportunity_score))}/100`,txt(s.opportunity_label),txt(s.opportunity_timing_label),n(s.opportunity_timing_score)!=null?`Momento ${Math.round(n(s.opportunity_timing_score))}/100`:'',n(s.opportunity_return_20d_pct)!=null?`20d ${n(s.opportunity_return_20d_pct)>=0?'+':''}${num(s.opportunity_return_20d_pct)}%`:''].filter(Boolean).join(' · '),qs?null:s.opportunity_score)).join(''):'<div class="market-empty market-empty--filters"><strong>Sem resultados neste filtro.</strong><span>Experimenta outro setor ou remove a pesquisa.</span></div>'}</div></section>`;
  }


  function low52Stats(s){
    // The startup market index deliberately omits the full 1Y history. Use the
    // compact 52-week bounds there; once a dossier is hydrated the complete
    // history remains available and takes precedence.
    const hist=Array.isArray(s?.price_history_1y)?s.price_history_1y:[];
    const closes=hist.map(x=>n(x?.close)).filter(x=>x!=null&&x>0);
    const current=n(s?.current_price) ?? (closes.length?closes[closes.length-1]:null);
    const low=closes.length?Math.min(...closes):(n(s?.low52_price_low)??n(s?.fifty_two_week_low));
    const high=closes.length?Math.max(...closes):(n(s?.low52_price_high)??n(s?.fifty_two_week_high));
    if(current==null || current<=0 || low==null || low<=0) return null;
    const above=(current/low-1)*100;
    return {low,high:high??low,current,above};
  }

  function low52OpportunityRank(s){
    // The 52-week-low surface is a lens over canonical Discovery, not a
    // second alpha engine. Eligibility, evidence quality, Risk Gate and score
    // caps are owned by scripts/opportunity_rank.py and published in the row.
    if(s?.opportunity_eligible!==true) return null;
    const score=n(s?.opportunity_score);
    return score==null?null:Math.round(Math.max(0,Math.min(100,score)));
  }

  function renderLows(){
    let rows=M.stocks.filter(s=>!isFund(s)).map(s=>({s,stats:low52Stats(s)}))
      .filter(x=>x.stats && x.stats.above>=-0.5 && x.stats.above<=5)
      .map(x=>({...x,opportunityRank:low52OpportunityRank(x.s)}))
      .filter(x=>x.opportunityRank!=null)
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
    }).join(''):'<div class="market-empty"><strong>Sem oportunidades Discovery elegíveis até 5% do mínimo de 52 semanas.</strong><br><span>O universo será recalculado quando os dados de mercado forem atualizados.</span></div>';
    return `<section class="market-section"><div class="market-section__head"><div><h3>Mínimos de 52 semanas</h3><p>Até 5% do mínimo, filtrados e ordenados pelo Discovery canónico. Esta vista não calcula um segundo score.</p></div><span class="market-data-age">${total} ${total===1?'empresa':'empresas'}</span></div><div class="market-list">${body}</div></section>`;
  }

  const ETF_THEMES=[
    ['all','Todos os ETFs',/.+/i],
    ['technology','Tecnologia',/technology|tech(?:nology)?|digital|software|cloud|internet|information technology|computing|saas|platform/i],
    ['semiconductors','Semicondutores',/semiconductor|chip|microchip|semicon|phlx semiconductor|integrated circuit|foundry|wafer|memory chip/i],
    ['ai_robotics','IA & Robótica',/artificial intelligence|machine learning|(^|[^a-z])ai([^a-z]|$)|robot|automation|robotics|autonomous systems/i],
    ['cybersecurity','Cibersegurança',/cyber|security.*tech|digital security|network security|information security/i],
    ['healthcare','Saúde',/health|healthcare|medical|pharma|pharmaceutical/i],
    ['biotech','Biotecnologia',/biotech|biotechnology|genomic|genomics/i],
    ['energy','Energia',/energy|oil|gas|petroleum|exploration|natural gas/i],
    ['clean_energy','Energia limpa',/clean energy|renewable|solar|wind|hydrogen|decarbon/i],
    ['nuclear_uranium','Nuclear & Urânio',/uranium|nuclear/i],
    ['gold','Ouro',/gold|gold miner|gold mining/i],
    ['silver_metals','Prata & Metais',/silver|precious metal|metals|mining|copper|lithium/i],
    ['water','Água',/water|clean water|wastewater|desalination|water infrastructure|water utilities/i],
    ['agriculture','Agricultura',/agricultur|agribusiness|farm|crop|seed|grain|fertili[sz]er|food production/i],
    ['defence','Defesa',/defen[cs]e|aerospace|military|weapons|defense technology/i],
    ['infrastructure','Infraestruturas',/infrastructure/i],
    ['real_estate','Imobiliário',/real estate|reit|property/i],
    ['dividend','Dividendos',/dividend|income|high yield equity/i],
    ['bonds','Obrigações',/bond|treasury|fixed income|corporate debt|government debt/i],
    ['emerging','Emergentes',/emerging market|emerging markets/i],
    ['china','China',/china|chinese|csi 300|hang seng/i],
    ['europe','Europa',/europe|eurozone|stoxx|european/i],
    ['world','Mundial',/world|global|all-world|all world|msci acwi/i],
    ['sp500','S&P 500',/s&p\s*500|sp 500|s&p500/i],
    ['nasdaq','Nasdaq',/nasdaq|qqq/i],
    ['small_caps','Small Caps',/small cap|small-cap|smallcap/i],
  ];

  function fundThemeText(s){
    return `${txt(s.ticker)} ${txt(s.name)} ${txt(s.sector)} ${txt(s.industry)} ${txt(s.category)} ${txt(s.region)} ${txt(s.theme)} ${txt(s.fund_theme)} ${txt(s.style)} ${txt(s.fund_style)} ${txt(s.ucits)} ${txt(s.fund_ucits)} ${txt(s.description)} ${txt(s.long_business_summary)} ${txt(s.business_summary)}`;
  }

  function fundMatchesTheme(s,key){
    const def=ETF_THEMES.find(x=>x[0]===key);
    return Boolean(def && def[2].test(fundThemeText(s)));
  }

  function renderFunds(){
    const qs=M.query.toLowerCase();
    let funds=M.stocks.filter(isFund);
    const available=ETF_THEMES.map(([key,label,matcher])=>({
      key,label,count:funds.filter(s=>matcher.test(fundThemeText(s))).length
    })).filter(x=>x.count>0);

    if(qs){
      funds=funds.filter(s=>fundThemeText(s).toLowerCase().includes(qs));
      funds.sort((a,b)=>(n(b.etf_score)||-1)-(n(a.etf_score)||-1));
      return `<section class="market-section"><div class="market-section__head"><div><h3>ETFs · pesquisa</h3><p>Resultados para ${esc(M.query)}.</p></div><span class="market-data-age">${funds.length}</span></div><div class="market-list">${funds.length?funds.map(s=>renderRow(s,[n(s.expense_ratio)!=null?`TER ${pct(s.expense_ratio)}`:'',txt(s.region)].filter(Boolean).join(' · '))).join(''):'<div class="market-empty">Sem ETFs encontrados.</div>'}</div></section>`;
    }

    if(!M.fundTheme){
      return `<section class="market-section market-etf-discovery"><div class="market-section__head"><div><h3>Escolher ETFs por tema</h3><p>Escolhe primeiro a exposição que procuras. Só depois mostramos os fundos desse tema.</p></div><span class="market-data-age">${funds.length} fundos</span></div><div class="market-etf-theme-grid" role="group" aria-label="Temas de ETF">${available.map(x=>`<button type="button" class="market-etf-theme" data-market-fund-theme="${esc(x.key)}"><strong>${esc(x.label)}</strong><span>${x.count} ${x.count===1?'ETF':'ETFs'}</span></button>`).join('')}</div></section>`;
    }

    const theme=available.find(x=>x.key===M.fundTheme);
    funds=funds.filter(s=>fundMatchesTheme(s,M.fundTheme)).sort((a,b)=>(n(b.etf_score)||-1)-(n(a.etf_score)||-1));
    const total=funds.length;
    const visible=M.fundTheme==='all'?funds.slice(0,M.fundLimit):funds;
    const more=M.fundTheme==='all'&&visible.length<total?`<button type="button" class="market-etf-change-theme" data-market-fund-more>Mostrar mais · ${visible.length} de ${total}</button>`:'';
    const copy=M.fundTheme==='all'?'Catálogo completo, ordenado pelo ETF Score quando existe. Pesquisa continua disponível para qualquer fundo.':'ETFs classificados pela exposição temática disponível.';
    return `<section class="market-section market-etf-discovery"><div class="market-section__head"><div><h3>${esc(theme?.label||'ETFs')}</h3><p>${copy}</p></div><button type="button" class="market-etf-change-theme" data-market-fund-theme="">Mudar tema</button></div><div class="market-list">${visible.length?visible.map(s=>renderRow(s,[n(s.expense_ratio)!=null?`TER ${pct(s.expense_ratio)}`:'',txt(s.region)].filter(Boolean).join(' · '))).join(''):'<div class="market-empty">Sem ETFs encontrados neste tema.</div>'}</div>${more}</section>`;
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
    const status=liveCount?`Congresso · ${liveCount}`:(M.congressError?'Congresso indisponível':ageText());
    const empty=M.congressError
      ? `<div class="market-empty"><strong>Não foi possível carregar Congresso.</strong><br><span>${esc(M.congressError)}</span><br><small>Insiders continuam disponíveis. Os trades do Congresso serão tentados novamente.</small></div>`
      : '<div class="market-empty">A carregar atividade recente…</div>';
    return `<section class="market-section"><div class="market-section__head"><div><h3>Smart money</h3><p>Compras de insiders e atividade declarada no Congresso dos EUA</p><p class="market-source-credit">Congresso: snapshot Vestra · divulgações STOCK Act oficiais</p></div><span class="market-data-age">${status}</span></div><div class="market-list">${rows.map(s=>renderRow(s,`${n(s.insider_buy_count_30d)||0} compras insider · ${Array.isArray(s.congress_trades)?s.congress_trades.length:0} trades Congresso`)).join('')||empty}</div></section>`;
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
    if(M.mode==='metals' && window.VestraMetals?.renderInto){
      window.VestraMetals.renderInto(root);
      return;
    }
    root.dataset.metalsActive='0';
    root.innerHTML = M.mode==='funds'?renderFunds():M.mode==='smart'?renderSmart():M.mode==='watch'?renderWatch():M.mode==='lows'?renderLows():renderDiscover();
    if(M.mode==='discover'&&!M.query&&window.VestraMarketOpportunities?.refresh){
      // Direct handoff avoids rendering a disposable native shortlist and then
      // replacing it one animation frame later via the companion observer.
      window.VestraMarketOpportunities.refresh();
    }
  }

  const marketSearchSuggestions = window.VestraMarketSearchSuggestions?.create({
    getStocks: () => M.stocks,
    getQuery: () => M.query,
    isLoaded: () => M.loaded,
    getBox: () => $m('marketSuggestions'),
    text: txt,
    number: n,
    escapeHtml: esc,
    isFund,
  }) || null;
  function hideSearchSuggestions(){ return marketSearchSuggestions?.hide(); }
  function renderSearchSuggestions(){ return marketSearchSuggestions?.render(); }

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

    function scoreDimensionLabel(label){
    const labels={
      'Quality':'Qualidade','Growth':'Crescimento','Balance':'Balanço','Cash Flow':'Cash flow','Valuation':'Valuation',
      'Execution':'Execução','Earnings Quality':'Qualidade dos lucros','Capital Allocation':'Alocação de capital','Stability':'Estabilidade',
      'Bank Quality':'Qualidade bancária','Efficiency':'Eficiência','Asset Quality':'Qualidade do crédito','Capital Proxy':'Capitalização',
      'Income':'Rendimento','REIT Quality':'Qualidade REIT','Leverage':'Alavancagem','P/FFO Value':'P/FFO','Distribution':'Distribuição',
      'Insurance Quality':'Qualidade seguradora','Underwriting Proxy':'Subscrição','Utility Quality':'Qualidade utility',
      'Energy Quality':'Qualidade energia','Cash Runway':'Runway de caixa','Net Cash':'Caixa líquida',
      'Dilution Discipline':'Disciplina de diluição','Operating Quality':'Qualidade operacional'
    };
    return labels[label]||label;
  }

  function scoreDims(s){
    const native=s?.score_dimensions;
    if(native && typeof native==='object' && !Array.isArray(native)){
      const rows=Object.entries(native).map(([label,value])=>[scoreDimensionLabel(label),n(value)]).filter(([,value])=>value!=null);
      if(rows.length) return rows;
    }
    const mapped=[
      ['Qualidade',s.quality_pct],['Crescimento',s.growth_pct],['Balanço',s.balance_pct],['Cash flow',s.cashflow_pct],
      ['Valuation',s.value_pct],['Execução',s.execution_pct],['Qualidade dos lucros',s.earnings_quality_pct],
      ['Alocação de capital',s.capital_allocation_pct],['Estabilidade',s.stability_pct]
    ];
    return mapped.filter(([,v])=>v!=null);
  }

  function scoreMetricValue(s,key,kind='pct'){
    const value=n(s?.[key]);
    if(value==null) return null;
    if(kind==='num') return num(value);
    if(kind==='compact') return compact(value);
    if(kind==='multiple') return `${num(value)}×`;
    return pct(value);
  }

  function pillarMetricSummary(s,label){
    const defs={
      'Qualidade':[['ROE','roe'],['ROA','roa'],['Margem líquida','profit_margin'],['Margem operacional','operating_margin'],['Margem bruta','gross_margin']],
      'Crescimento':[['Receitas','revenue_growth'],['Lucros','earnings_growth'],['Lucros trimestrais','earnings_quarterly_growth']],
      'Balanço':[['Current ratio','current_ratio','multiple'],['Quick ratio','quick_ratio','multiple'],['Debt / Equity','debt_to_equity','num'],['Net cash','net_cash','compact'],['Cobertura juros','interest_coverage','multiple']],
      'Cash flow':[['FCF yield','fcf_yield'],['Cash flow operacional','operating_cash_flow','compact'],['Free cash flow','free_cash_flow','compact']],
      'Valuation':[['P/E','trailing_pe','multiple'],['Forward P/E','forward_pe','multiple'],['P/B','price_to_book','multiple'],['EV/EBITDA','enterprise_to_ebitda','multiple'],['PEG','peg_ratio','multiple']],
      'Execução':[['Receitas','revenue_growth'],['Lucros','earnings_growth'],['Margem operacional','operating_margin']],
      'Qualidade dos lucros':[['Conversão caixa/lucro','cash_conversion_ratio','multiple'],['Accrual ratio','accrual_ratio'],['Margem FCF','fcf_margin']],
      'Alocação de capital':[['Diluição YoY','diluted_shares_yoy'],['Buybacks último T','repurchases_last_quarter','compact'],['ROCE proxy','roce_proxy'],['Cobertura dividendo/FCF','dividend_fcf_coverage','multiple']],
      'Estabilidade':[['Beta','beta','num']],
      'Qualidade bancária':[['ROE','roe'],['ROA','roa'],['Margem líquida','profit_margin']],
      'Eficiência':[['Efficiency ratio','efficiency_ratio_proxy']],
      'Qualidade do crédito':[['Provisões / receitas','provision_to_revenue']],
      'Capitalização':[['Equity / assets','equity_to_assets']],
      'Rendimento':[['Dividend yield','dividend_yield']],
      'Qualidade REIT':[['FFO / ação proxy','reit_ffo_per_share_proxy','num'],['ROE','roe'],['Margem líquida','profit_margin']],
      'Alavancagem':[['Net debt / EBITDA','reit_net_debt_to_ebitda','multiple'],['Cobertura juros','interest_coverage','multiple']],
      'P/FFO':[['P/FFO proxy','reit_p_ffo_proxy','multiple']],
      'Distribuição':[['Dividend yield','dividend_yield'],['Payout FFO proxy','reit_ffo_payout_proxy']],
      'Qualidade seguradora':[['ROE','roe'],['ROA','roa'],['Margem líquida','profit_margin']],
      'Subscrição':[['Claims / receitas','insurance_claims_to_revenue'],['Operating ratio proxy','insurance_operating_ratio_proxy']],
      'Qualidade utility':[['ROE','roe'],['Margem operacional','operating_margin'],['Margem líquida','profit_margin']],
      'Qualidade energia':[['ROE','roe'],['ROCE proxy','roce_proxy'],['Margem operacional','operating_margin']],
      'Runway de caixa':[['Cash total','total_cash','compact'],['Free cash flow','free_cash_flow','compact']],
      'Caixa líquida':[['Net cash','net_cash','compact']],
      'Disciplina de diluição':[['Diluição YoY','diluted_shares_yoy']],
      'Qualidade operacional':[['ROA','roa'],['Margem operacional','operating_margin']]
    };
    const metrics=defs[label]||[];
    if(!metrics.length) return '';
    const present=[]; let missing=0;
    for(const [name,key,kind] of metrics){
      const rendered=scoreMetricValue(s,key,kind||'pct');
      if(rendered==null){ missing+=1; continue; }
      present.push(`${esc(name)} <strong>${esc(rendered)}</strong>`);
    }
    const missingText=missing?` · ${missing} ${missing===1?'métrica em falta':'métricas em falta'}`:'';
    return `<div class="market-dim__evidence">${present.length?present.join(' · '):'Sem métricas-base disponíveis'}${missingText}</div>`;
  }

  function dimRows(s){
    const dims=scoreDims(s);
    return dims.map(([k])=>{
      const evidence=pillarMetricSummary(s,k);
      if(!evidence) return '';
      return `<div class="market-dim market-dim--evidence-only"><div><div class="market-dim__label"><span>${k}</span></div>${evidence}</div></div>`;
    }).filter(Boolean).join('');
  }

  function scoreModelLabel(model){
    return ({general:'Geral',bank:'Bancos',biotech:'Biotecnologia',energy:'Energia',growth_tech:'Tecnologia / crescimento',insurance:'Seguros',reit:'REIT',utility:'Utilities'})[txt(model)]||txt(model)||'Não classificado';
  }

  function scoreModelWeights(model){
    const packs={
      general:[['Qualidade',18],['Crescimento',15],['Balanço',14],['Cash flow',8],['Valuation',12],['Execução',10],['Qualidade dos lucros',10],['Alocação de capital',8],['Estabilidade',5]],
      growth_tech:[['Qualidade',20],['Crescimento',22],['Balanço',12],['Cash flow',10],['Valuation',7],['Execução',12],['Qualidade dos lucros',9],['Alocação de capital',5],['Estabilidade',3]],
      bank:[['Qualidade bancária',22],['Eficiência',13],['Qualidade do crédito',10],['Capitalização',15],['Crescimento',15],['Valuation',15],['Rendimento',5],['Estabilidade',5]],
      reit:[['Qualidade REIT',22],['Crescimento',16],['Alavancagem',20],['P/FFO',20],['Distribuição',17],['Estabilidade',5]],
      insurance:[['Qualidade seguradora',22],['Subscrição',18],['Capitalização',18],['Crescimento',12],['Valuation',17],['Rendimento',8],['Estabilidade',5]],
      utility:[['Qualidade utility',18],['Balanço',22],['Rendimento',18],['Valuation',17],['Crescimento',10],['Estabilidade',10],['Cash flow',5]],
      energy:[['Qualidade energia',20],['Cash flow',22],['Balanço',18],['Valuation',20],['Crescimento',10],['Estabilidade',10]],
      biotech:[['Runway de caixa',25],['Caixa líquida',15],['Disciplina de diluição',20],['Crescimento',20],['Qualidade operacional',10],['Estabilidade',10]]
    };
    return packs[txt(model)]||[];
  }

  function scoreRiskExplanation(s){
    const gate=txt(s.risk_gate), cap=n(s.score_cap), flags=Array.isArray(s.risk_flags)?s.risk_flags:[];
    const capText=cap!=null?` O score fica limitado a ${Math.round(cap)}/100.`:'';
    if(!gate) return flags.length
      ? `<strong>Risk Gate não classificado:</strong> existem sinais estruturais registados, mas o nível do gate não está disponível.${capText}`
      : '<strong>Risk Gate:</strong> não classificado com a evidência atual.';
    if(gate==='clear'&&!flags.length) return '<strong>Risk Gate:</strong> sem bloqueios estruturais materiais detetados.';
    const label=({watch:'vigilância',high:'elevado',severe:'severo'})[gate]||gate;
    return `<strong>Risk Gate ${esc(label)}:</strong> existem sinais estruturais que não podem ser compensados por outros pilares.${capText}`;
  }

  function scoreReliabilityLabel(value){
    return ({
      robust:'Robusta',
      moderate_evidence:'Moderada',
      limited_evidence:'Limitada',
      insufficient_data:'Insuficiente',
    })[txt(value)]||'—';
  }

  function scoreEvidenceExplanation(s){
    const conf=n(s.confidence_score), critical=n(s.critical_metric_coverage_pct);
    const native=n(s.model_native_coverage_pct);
    const reliability=txt(s.score_reliability);
    const raw=n(s.score_raw), published=n(s.score);
    let tone='Evidência não classificada';
    if(reliability==='robust') tone='Evidência robusta';
    else if(reliability==='insufficient_data') tone='Evidência insuficiente';
    else if(reliability==='limited_evidence') tone='Evidência limitada';
    else if(reliability==='moderate_evidence') tone='Evidência moderada';
    else if(conf!=null&&conf<60) tone='Confiança baixa';
    const moderation=raw!=null&&published!=null&&published<raw-0.1?` O score quantitativo bruto era ${Math.round(raw)}, mas a publicação foi moderada para ${Math.round(published)} pela qualidade/cobertura da evidência.`:'';
    return `<strong>${esc(tone)}.</strong>${critical==null?'':` Métricas críticas ${Math.round(critical)}%.`}${native==null?'':` Cobertura nativa do modelo ${Math.round(native)}%.`} Fiabilidade do Score ${esc(scoreReliabilityLabel(reliability))}.${moderation}`;
  }

  function scoreWeightExplanation(s){
    const weights=scoreModelWeights(s.score_model);
    if(!weights.length) return 'Pesos indisponíveis sem modelo classificado.';
    return weights.map(([label,w])=>`${esc(label)} ${w}%`).join(' · ');
  }

  function scoreBand(value){
    const v=n(value);
    if(v==null) return 'Sem score publicável';
    if(v>=75) return 'Muito forte no ranking';
    if(v>=60) return 'Acima da média';
    if(v>=40) return 'Intermédio';
    return 'Abaixo da média';
  }

  function scoreModelRationale(s){
    const model=txt(s?.score_model);
    if(!model) return '';
    const notes={
      general:'Modelo geral: qualidade, crescimento, balanço, valuation, execução, qualidade dos lucros, alocação de capital e estabilidade.',
      growth_tech:'Growth Tech: dá mais peso a crescimento, execução, margens, qualidade do cash flow e valuation compatível com empresas de crescimento.',
      bank:'Bancos: rentabilidade, eficiência, qualidade do crédito, capitalização, crescimento do net interest income, P/B-P/E e rendimento.',
      reit:'REIT: FFO/P-FFO proxy, alavancagem, payout/distribuição, crescimento e estabilidade. AFFO, NAV e ocupação não são inventados quando faltam.',
      insurance:'Seguros: rentabilidade, underwriting proxy, capitalização, crescimento, valuation e rendimento; não fabrica combined ratio regulatório.',
      utility:'Utilities: resiliência do balanço, rendimento, qualidade operacional, valuation e estabilidade pesam mais do que crescimento headline.',
      energy:'Energia: geração de caixa, eficiência de capital, balanço e valuation têm maior peso; crescimento cíclico pesa menos.',
      biotech:'Biotech: runway de caixa, caixa líquida, disciplina de diluição e progresso operacional; P/E genérico é excluído quando não é economicamente útil.'
    };
    return notes[model]||txt(s?.score_model_note)||'';
  }

  function peerScoreContext(s){
    const peerCount=n(s?.peer_count);
    const lines=[];
    const rel=(label,value)=>{
      const v=n(value);
      if(v==null) return;
      const direction=v<0?'desconto':'prémio';
      lines.push(`${label}: ${Math.abs(v).toFixed(0)}% de ${direction} vs mediana`);
    };
    rel('Forward P/E',s?.forward_pe_vs_sector_pct);
    rel('Trailing P/E',s?.trailing_pe_vs_sector_pct);
    rel('P/B',s?.pb_vs_sector_pct);
    rel('EV/EBITDA',s?.ev_ebitda_vs_sector_pct);

    const compare=(label,value,median,kind='pct')=>{
      const v=n(value), m=n(median);
      if(v==null||m==null) return;
      const fv=kind==='num'?num(v):pct(v);
      const fm=kind==='num'?num(m):pct(m);
      const delta=v-m;
      const word=Math.abs(delta)<1e-12?'em linha com':delta>0?'acima de':'abaixo de';
      lines.push(`${label}: ${fv} vs ${fm} · ${word} mediana`);
    };
    compare('ROE',s?.roe,s?.sector_roe_median);
    compare('Margem operacional',s?.operating_margin,s?.sector_operating_margin_median);
    compare('Margem bruta',s?.gross_margin,s?.sector_gross_margin_median);
    compare('ROCE proxy',s?.roce_proxy,s?.sector_roce_proxy_median);
    compare('Dividend yield',s?.dividend_yield,s?.sector_dividend_yield_median);
    compare('FCF yield',s?.fcf_yield,s?.sector_fcf_yield_median);

    if(!lines.length) return '';
    const peerLabel=peerCount!=null&&peerCount>0?` · ${Math.round(peerCount)} peers`:'';
    return `<p class="market-case-note"><strong>Face aos peers${peerLabel}.</strong> ${lines.slice(0,6).map(esc).join(' · ')}. <span class="market-data-age">Contexto relativo; não é recomendação.</span></p>`;
  }

  function scoreExplanation(s){
    const score=n(s.score), coverage=n(s.data_coverage_pct);
    const confidence=txt(s.data_confidence)||scoreReliabilityLabel(s.score_reliability);
    if(score==null){
      return `<div class="market-detail-card market-score-explain"><div class="market-perspective-head"><div><small>COMO LER A AVALIAÇÃO</small><h4>Score não publicado</h4></div><span class="market-data-age">evidência insuficiente</span></div><p>Não há dados suficientes para produzir uma avaliação comparável com segurança. A ausência de score não significa uma empresa fraca.</p><div class="market-action-context"><span>Modelo ${esc(scoreModelLabel(s.score_model))}</span><span>Cobertura ${coverage==null?'—':Math.round(coverage)+'%'}</span><span>Confiança ${esc(confidence)}</span></div></div>`;
    }
    return `<div class="market-detail-card market-score-explain"><div class="market-perspective-head"><div><small>PORQUE TEM ESTE SCORE</small><h4>Como se forma a avaliação</h4></div><span class="market-data-age">${esc(scoreModelLabel(s.score_model))}</span></div><p><strong>O Score Vestra é um ranking relativo do perfil fundamental — não é uma previsão de retorno nem uma probabilidade de valorização.</strong> Um pilar em 80 significa aproximadamente percentil 80 no conjunto comparável usado por esse pilar; não significa 80% de probabilidade de subir.</p><div class="market-score-detail"><div class="market-dossier-section-label">DETALHE QUANTITATIVO DOS PILARES</div>${dimRows(s)}</div>${scoreModelRationale(s)?`<p class="market-case-note"><strong>Modelo usado.</strong> ${esc(scoreModelRationale(s))}</p>`:''}${peerScoreContext(s)}<div class="market-score-layers"><p class="market-case-note"><strong>1 · Ranking fundamental.</strong> Os pesos-base do modelo ${esc(scoreModelLabel(s.score_model))} são: ${scoreWeightExplanation(s)}. Nos modelos especializados, cada métrica usa peers do mesmo modelo quando existem pelo menos 20 observações válidas; métricas mais raras recuam para o universo global. Quando falta um pilar, ele não vale zero nem aumenta o peso dos restantes: mantém o peso-base e entra como neutro 50. A falta de evidência é tratada separadamente pela Reliability/Confidence.</p><p class="market-case-note"><strong>2 · Qualidade da evidência.</strong> ${scoreEvidenceExplanation(s)}</p><p class="market-case-note"><strong>3 · Travão de risco.</strong> ${scoreRiskExplanation(s)}</p><p class="market-case-note"><strong>4 · Valuation, tese e expectativas.</strong> A faixa de fair value e os sinais de tese/analistas são camadas separadas. Podem mudar a leitura e a ação sem reescrever artificialmente o score fundamental.</p><p class="market-case-note"><strong>5 · Decisão de carteira.</strong> “Reforçar”, “Manter”, “Rever” ou “Substituir” considera ainda peso da posição, concentração setorial, overlap e alternativas. Uma empresa excelente pode por isso ficar em “Manter”.</p></div><p class="market-case-note">Scores com coberturas muito diferentes devem ser comparados com cautela. A validação prospetiva ainda está a recolher cohorts; o score deve ser usado como screener explicável, não como promessa de performance futura.</p></div>`;
  }

  function shortDate(v){
    if(!v) return '—'; const d=new Date(v); if(Number.isNaN(d.valueOf())) return esc(v);
    return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short',year:'numeric'}).format(d);
  }

  const dossierSignals = window.VestraMarketDossierSignals?.create({
    text: txt,
    number: n,
    escapeHtml: esc,
    formatShortDate: shortDate,
  }) || null;
  function evidencePanel(s){ return dossierSignals?.evidencePanel(s) || ''; }
  function recoveryPanel(s){ return dossierSignals?.recoveryPanel(s) || ''; }
  function drawdownPanel(s){ return dossierSignals?.drawdownPanel(s) || ''; }

  function investmentCase(s){
    const evidence=Array.isArray(s.thesis_evidence)?s.thesis_evidence.filter(Boolean):[];
    const drivers=Array.isArray(s.thesis_evolution_drivers)?s.thesis_evolution_drivers.filter(Boolean):[];
    const estimateDrivers=Array.isArray(s.earnings_intelligence_drivers)?s.earnings_intelligence_drivers.filter(Boolean):[];
    const risks=Array.isArray(s.thesis_risks)?s.thesis_risks.filter(Boolean):[];
    const riskFlags=Array.isArray(s.risk_flags)?s.risk_flags.filter(Boolean):[];
    const dims=scoreDims(s);
    const weak=dims.filter(([,v])=>n(v)!=null&&n(v)<48).sort((a,b)=>n(a[1])-n(b[1])).map(([k,v])=>`${k} ${Math.round(n(v))}/100`);
    const fwdVs=n(s.forward_pe_vs_sector_pct), trailVs=n(s.trailing_pe_vs_sector_pct), evVs=n(s.ev_ebitda_vs_sector_pct);
    const valuationDelta=fwdVs??trailVs??evVs;
    const valuationSignal=txt(s.valuation_signal);
    let valuation='Sem leitura robusta', valuationClass='';
    if(valuationSignal==='undervalued'){ valuation='Abaixo do fair value'; valuationClass='is-positive'; }
    else if(valuationSignal==='overvalued'){ valuation='Acima do fair value'; valuationClass='is-caution'; }
    else if(valuationSignal==='fair'){ valuation='Próximo do fair value'; }
    else if(valuationSignal==='uncertain'){ valuation='Leitura não acionável'; }
    else if(valuationSignal==='insufficient'){ valuation='Dados insuficientes'; }
    else if(!valuationSignal&&valuationDelta!=null){
      if(valuationDelta<=-15){ valuation='A desconto vs setor'; valuationClass='is-positive'; }
      else if(valuationDelta>=20){ valuation='Com prémio vs setor'; valuationClass='is-caution'; }
      else valuation='Em linha com o setor';
    }
    const watch=[];
    if(txt(s.thesis_direction)==='up') watch.push('Tese quantitativa a melhorar');
    if(txt(s.thesis_direction)==='down') watch.push('Tese quantitativa a piorar');
    if(riskFlags.length) watch.push('Risk Gate com sinais estruturais a acompanhar');
    const why=evidence.length?evidence.slice(0,3):['Sem evidência específica adicional para além da síntese da tese.'];
    const catalystPool=[...estimateDrivers,...drivers];
    const catalysts=catalystPool.length?catalystPool.slice(0,3):[txt(s.thesis_evolution_summary)||'Sem catalisador quantitativo claro identificado nos dados atuais.'];
    const riskItems=[...risks.slice(0,3),...weak.slice(0,Math.max(0,3-risks.length))].slice(0,3);
    if(!riskItems.length){
      if(riskFlags.length) riskItems.push('O Risk Gate regista sinais estruturais; consulta o Travão de risco na explicação do Score.');
      else riskItems.push('Sem risco específico suficientemente forte identificado pelo modelo; rever métricas e negócio antes de decidir.');
    }
    const list=arr=>`<ul class="market-case-list">${arr.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
    return `<div class="market-case">
      <div class="market-case__top"><div><small>INVESTMENT CASE</small><h4>${esc(s.thesis_type||'Leitura do ativo')}</h4><p>${esc(s.thesis_summary||'Síntese ainda limitada pelos dados disponíveis.')}</p></div><span class="market-case__confidence">Confiança ${esc(txt(s.thesis_confidence)||'—')}</span></div>
      <div class="market-case-grid">
        <section><div class="market-case-label"><span>01</span> Porque interessa</div>${list(why)}</section>
        <section><div class="market-case-label"><span>02</span> O que pode correr bem</div>${list(catalysts)}</section>
        <section><div class="market-case-label"><span>03</span> O que pode quebrar a tese</div>${list(riskItems)}</section>
        <section><div class="market-case-label"><span>04</span> Está caro ou barato?</div><div class="market-value-call ${valuationClass}">${esc(valuation)}</div><p class="market-case-note">Conclusão editorial; fair value, múltiplos e margens de segurança estão na tab Valuation.</p></section>
      </div>
      <div class="market-watchpoints"><div class="market-case-label"><span>05</span> O que vigiar</div>${watch.length?watch.slice(0,4).map(x=>`<span>${esc(x)}</span>`).join(''):'<p class="market-case-note">Sem evento ou alteração quantitativa relevante identificada.</p>'}</div>
    </div>`;
  }

  function dossierScoreHistory(s){
    const raw=s?.score_history_quarterly ?? s?.score_history_4q ?? s?.score_history ?? s?.historical_scores;
    const rows=Array.isArray(raw)?raw:[];
    return rows.map((x,i)=>{
      if(typeof x==='number') return {label:`T${i+1}`,value:n(x)};
      const value=n(x?.score ?? x?.value ?? x?.vestra_score);
      const label=txt(x?.quarter ?? x?.period ?? x?.label ?? x?.date) || `T${i+1}`;
      return {label,value};
    }).filter(x=>x.value!=null).slice(-6);
  }

  function dossierScoreBoard(s){
    const score=n(s.score);
    const history=dossierScoreHistory(s);
    const historyHtml=history.length>=2
      ? `<div class="market-dossier-score-history"><div class="market-dossier-section-label">Histórico do Score</div><div class="market-dossier-history-bars">${history.map(x=>`<div class="market-dossier-history-bar"><i style="height:${Math.max(8,Math.min(100,x.value))}%"></i><strong>${Math.round(x.value)}</strong><span>${esc(x.label)}</span></div>`).join('')}</div></div>`
      : '';
    const historyClass=historyHtml?' market-dossier-scoreboard--with-history':'';
    return `<section class="market-dossier-scoreboard${historyClass}"><div class="market-dossier-scorehero"><div><small>VESTRA SCORE</small><strong>${score==null?'—':Math.round(score)}</strong><span>/100</span></div><p>${score==null?'Score não publicável com a evidência atual.':esc(scoreBand(score))}</p></div>${historyHtml}</section>`;
  }

  function dossierFullPicture(s){
    const summary=txt(s.long_business_summary)||txt(s.business_summary);
    const industry=txt(s.industry);
    const geography=txt(s.country)||txt(s.region);
    const quoteType=txt(s.quote_type);
    const facts=[
      ['Indústria',industry],
      ['País / região',geography],
      ['Tipo',quoteType],
      ['Moeda',txt(s.currency)]
    ].filter(([,value])=>value);
    const factsHtml=facts.length
      ? `<div class="market-dossier-company-facts">${facts.map(([label,value])=>`<div><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join('')}</div>`
      : '<p class="market-dossier-muted">A ficha de identificação ainda está incompleta para este ativo.</p>';
    return `<section class="market-dossier-editorial-card market-dossier-full-picture"><div class="market-dossier-section-label">THE FULL PICTURE</div><h3>O negócio em poucas linhas</h3><p>${esc(summary||'Ainda não existe uma descrição de negócio suficientemente robusta para este ativo.')}</p><div class="market-dossier-company-identity"><h4>Ficha da empresa</h4>${factsHtml}</div></section>`;
  }

  function dossierFinancialSnapshot(s){
    const metrics=[
      ['Receitas',n(s.total_revenue??s.revenue)],
      ['Lucro líquido',n(s.net_income)]
    ];
    const rows=metrics.filter(([,value])=>value!=null);
    if(!rows.length) return '';
    return `<section class="market-dossier-editorial-card market-dossier-financial-snapshot"><div class="market-dossier-section-label">FINANCIAL SNAPSHOT</div><div class="market-dossier-card-head"><h3>Escala do negócio</h3><span>Receita · lucro</span></div><div class="market-dossier-financial-grid">${rows.map(([label,value])=>`<div><small>${esc(label)}</small><strong>${compact(value)}</strong></div>`).join('')}</div><p class="market-dossier-interpretation">Escala e lucro em leitura rápida; geração de caixa, rácios, margens e balanço estão na tab Financeiro.</p></section>`;
  }

  function dossierGrowthProfile(s){
    const growth=n(s.growth_pct);
    const note=growth==null?'Cobertura insuficiente para classificar o crescimento face aos comparáveis.':growth>=70?'Crescimento acima da maioria dos comparáveis.':growth<45?'Crescimento é atualmente um dos pontos mais frágeis do perfil.':'Crescimento sem extremo claro face aos comparáveis.';
    return `<section class="market-dossier-editorial-card"><div class="market-dossier-section-label">GROWTH PROFILE</div><div class="market-dossier-card-head"><h3>Tração do negócio</h3><span>${growth==null?'—':Math.round(growth)+'/100'}</span></div><p>${esc(note)} O detalhe de receita, lucro, EPS e restantes métricas de execução está na tab Growth.</p></section>`;
  }

  function dossierExpectationsContext(s){
    const signal=txt(s.estimate_signal);
    const signalLabel={
      improving:'Expectativas a melhorar',
      deteriorating:'Expectativas a piorar',
      neutral:'Expectativas estáveis',
      insufficient:'Cobertura insuficiente'
    }[signal]||'Cobertura insuficiente';
    const signalTone=signal==='improving'?'is-positive':signal==='deteriorating'?'is-negative':'';
    const interpretation=signal==='improving'
      ? 'As estimativas recentes estão a mover-se na direção positiva.'
      : signal==='deteriorating'
        ? 'As estimativas recentes estão a ser revistas em baixa.'
        : signal==='neutral'
          ? 'As expectativas não mostram uma direção material neste momento.'
          : 'Ainda não existe cobertura suficiente para ler a direção das expectativas.';
    return `<section class="market-dossier-editorial-card market-dossier-expectations"><div class="market-dossier-section-label">MARKET EXPECTATIONS</div><div class="market-dossier-card-head"><h3>O que o mercado está a descontar</h3><span class="${signalTone}">${esc(signalLabel)}</span></div><p>${esc(interpretation)} O detalhe de revisões, targets e próximos resultados está na tab Perspetiva; o fair value está na tab Valuation.</p></section>`;
  }

  function dossierCatalystsRisks(s){
    const events=Array.isArray(s.catalyst_events)?s.catalyst_events.filter(Boolean):[];
    const positives=events.filter(x=>txt(x?.tone)==='positive').map(x=>txt(x?.label||x?.evidence)).filter(Boolean);
    const eventSignals=events.filter(x=>txt(x?.tone)==='event').map(x=>txt(x?.label||x?.evidence)).filter(Boolean);
    const risks=events.filter(x=>txt(x?.tone)==='risk').map(x=>txt(x?.label||x?.evidence)).filter(Boolean);
    const thesisDrivers=Array.isArray(s.thesis_evolution_drivers)?s.thesis_evolution_drivers.filter(Boolean):[];
    const earningsDrivers=Array.isArray(s.earnings_intelligence_drivers)?s.earnings_intelligence_drivers.filter(Boolean):[];
    const thesisRisks=Array.isArray(s.thesis_risks)?s.thesis_risks.filter(Boolean):[];
    const riskFlags=Array.isArray(s.risk_flags)?s.risk_flags.filter(Boolean):[];
    const unique=rows=>[...new Set(rows.map(x=>txt(x)).filter(Boolean))];
    const catalysts=unique([...positives,...eventSignals,...earningsDrivers,...thesisDrivers]);
    const riskItems=unique([...risks,...thesisRisks]);
    const hasStructuralRisk=riskFlags.length>0;
    if(!catalysts.length&&!riskItems.length&&!hasStructuralRisk) return '';
    const next=s.catalyst_next_date?shortDate(s.catalyst_next_date):(s.analyst_next_earnings_date?shortDate(s.analyst_next_earnings_date):'—');
    const balance=catalysts.length&&riskItems.length
      ? `${catalysts.length} catalisador${catalysts.length===1?'':'es'} e ${riskItems.length} risco${riskItems.length===1?'':'s'} identificados.`
      : catalysts.length&&hasStructuralRisk
        ? `${catalysts.length} catalisador${catalysts.length===1?'':'es'} identificado${catalysts.length===1?'':'s'}; o Risk Gate regista sinais estruturais adicionais.`
        : catalysts.length
          ? `${catalysts.length} catalisador${catalysts.length===1?'':'es'} identificado${catalysts.length===1?'':'s'}, sem risco específico adicional neste bloco.`
          : riskItems.length
            ? `${riskItems.length} risco${riskItems.length===1?'':'s'} identificado${riskItems.length===1?'':'s'}, sem catalisador robusto adicional neste bloco.`
            : 'O Risk Gate regista sinais estruturais; consulta o Travão de risco na explicação do Score.';
    return `<section class="market-dossier-editorial-card market-dossier-catalysts"><div class="market-dossier-section-label">CATALYSTS & RISKS</div><div class="market-dossier-card-head"><h3>O que pode mudar a tese</h3><span>Próximo evento · ${esc(next)}</span></div><p>${esc(balance)} O detalhe qualitativo está na tab Síntese, dentro do Investment Case.</p></section>`;
  }

  function dossierPillarBand(value){
    const v=n(value);
    if(v==null) return {label:'Sem score',tone:'is-muted'};
    if(v>=75) return {label:'Forte',tone:'is-positive'};
    if(v>=60) return {label:'Acima da média',tone:'is-positive'};
    if(v>=40) return {label:'Intermédio',tone:'is-neutral'};
    return {label:'Abaixo da média',tone:'is-caution'};
  }

  function dossierPillarCards(s){
    const dims=scoreDims(s).map(([label,value])=>({label,value:n(value)})).filter(x=>x.value!=null);
    if(!dims.length) return '';
    return `<section class="market-dossier-breakdown"><div class="market-dossier-section-label">SCORE BREAKDOWN</div><div class="market-dossier-breakdown-head"><h3>Porque tem este Score?</h3><p>Percentis relativos do modelo Vestra; o detalhe quantitativo fica nas tabs e na explicação do Score.</p></div><div class="market-dossier-breakdown-grid">${dims.map(({label,value})=>{
      const band=dossierPillarBand(value);
      return `<article class="market-dossier-breakdown-card"><div class="market-dossier-breakdown-card__head"><div><span>${esc(label)}</span><strong>${Math.round(value)}</strong></div><em class="${band.tone}">${esc(band.label)}</em></div><div class="market-dossier-breakdown-track"><i style="width:${Math.max(0,Math.min(100,value))}%"></i></div></article>`;
    }).join('')}</div><p class="market-dossier-interpretation">Os pilares são rankings relativos; não representam probabilidade de valorização. Métricas em falta não são tratadas como zero.</p></section>`;
  }

  function smartMoneyEventType(raw){
    const value=txt(raw).toLowerCase();
    if(/buy|purchase|acquir/.test(value)) return 'buy';
    if(/sell|sale|dispos/.test(value)) return 'sell';
    return 'other';
  }

  function smartMoneyTimeline(s){
    const prices=(Array.isArray(s.price_history_1y)?s.price_history_1y:[])
      .map(x=>({date:txt(x?.date),close:n(x?.close??x?.price)}))
      .filter(x=>x.date&&x.close!=null);
    if(prices.length<2) return '<p class="market-case-note">Histórico de preço insuficiente para mapear operações.</p>';
    const points=prices.slice(-120);
    const dateValue=d=>{ const t=Date.parse(d); return Number.isFinite(t)?t:null; };
    const dated=points.map(x=>({...x,t:dateValue(x.date)})).filter(x=>x.t!=null);
    if(dated.length<2) return '<p class="market-case-note">Histórico de preço insuficiente para mapear operações.</p>';
    const minT=dated[0].t,maxT=dated[dated.length-1].t,minP=Math.min(...dated.map(x=>x.close)),maxP=Math.max(...dated.map(x=>x.close)),range=maxP-minP||1;
    const xy=x=>({x:(x.t-minT)/(maxT-minT||1)*100,y:90-(x.close-minP)/range*72});
    const line=dated.map(x=>{const p=xy(x);return `${p.x.toFixed(2)},${p.y.toFixed(2)}`}).join(' ');
    const nearest=t=>dated.reduce((best,x)=>!best||Math.abs(x.t-t)<Math.abs(best.t-t)?x:best,null);
    const events=[];
    for(const x of (Array.isArray(s.insider_transactions)?s.insider_transactions:[]).slice(0,12)){
      const date=txt(x?.date||x?.transaction_date),t=dateValue(date); if(t==null||t<minT||t>maxT) continue;
      const p=xy(nearest(t)); events.push({kind:'insider',type:smartMoneyEventType(x?.type||x?.transaction_type),date,label:txt(x?.name||x?.insider||'Insider'),x:p.x,y:p.y});
    }
    for(const x of (Array.isArray(s.congress_trades)?s.congress_trades:[]).slice(0,12)){
      const date=txt(x?.transaction_date||x?.date),t=dateValue(date); if(t==null||t<minT||t>maxT) continue;
      const p=xy(nearest(t)); events.push({kind:'congress',type:smartMoneyEventType(x?.type||x?.transaction),date,label:txt(x?.member||x?.representative||x?.name||'Congresso'),x:p.x,y:p.y});
    }
    const markers=events.map(e=>`<circle class="market-smart-marker market-smart-marker--${e.kind} market-smart-marker--${e.type}" cx="${e.x.toFixed(2)}" cy="${e.y.toFixed(2)}" r="2.6"><title>${esc(e.label)} · ${esc(shortDate(e.date))}</title></circle>`).join('');
    const rows=events.slice(0,10).map(e=>`<div class="market-smart-event"><i class="market-smart-dot market-smart-dot--${e.kind} market-smart-dot--${e.type}"></i><span><strong>${esc(e.kind==='insider'?'Insider':'Congresso')}</strong> · ${esc(e.label)}</span><em>${esc(shortDate(e.date))}</em></div>`).join('');
    return `<div class="market-smart-timeline"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Preço e operações declaradas"><polyline points="${line}" fill="none" stroke="currentColor" stroke-width="1.6" vector-effect="non-scaling-stroke" class="market-smart-price-line"/>${markers}</svg><div class="market-smart-legend"><span><i class="market-smart-dot market-smart-dot--insider"></i>Insider</span><span><i class="market-smart-dot market-smart-dot--congress"></i>Congresso</span></div>${rows?`<div class="market-smart-events">${rows}</div>`:'<p class="market-case-note">Sem operações datadas no intervalo visível.</p>'}<p class="market-case-note">Os marcadores mostram a data declarada sobre o preço semanal mais próximo. Não calculamos retorno pós-operação nem taxa de acerto sem evidência suficiente.</p></div>`;
  }

  function dossierSmartMoney(s){
    const buyValue=n(s.insider_buy_value_30d), sellValue=n(s.insider_sell_value_30d);
    const buyCount=n(s.insider_buy_count_30d), sellCount=n(s.insider_sell_count_30d);
    const hasCompleteValue=buyValue!=null&&sellValue!=null;
    const hasCompleteCount=buyCount!=null&&sellCount!=null;
    const hasAnyCoverage=buyValue!=null||sellValue!=null||buyCount!=null||sellCount!=null;
    const net=hasCompleteValue
      ? buyValue-sellValue
      : hasCompleteCount
        ? buyCount-sellCount
        : null;
    const partial=net==null&&hasAnyCoverage;
    const flowTone=net==null?'':net>0?'is-positive':net<0?'is-negative':'';
    const flowLabel=partial?'Cobertura parcial':net==null?'Cobertura insuficiente':net>0?'Fluxo comprador':net<0?'Fluxo vendedor':'Sem fluxo líquido';
    const interpretation=partial
      ? 'Os dados insider dos últimos 30 dias estão incompletos entre compras e vendas, por isso não é seguro classificar o fluxo líquido.'
      : net==null
        ? 'Ainda não há dados insider suficientes para classificar o fluxo dos últimos 30 dias.'
        : net>0
          ? 'O fluxo insider declarado nos últimos 30 dias é líquido comprador.'
          : net<0
            ? 'O fluxo insider declarado nos últimos 30 dias é líquido vendedor.'
            : 'Não existe fluxo insider líquido material nos últimos 30 dias.';
    return `<section class="market-dossier-editorial-card market-dossier-smart"><div class="market-dossier-section-label">SMART MONEY MAP</div><div class="market-dossier-card-head"><h3>Insiders e divulgações políticas</h3><span class="${flowTone}">${flowLabel}</span></div><p>${esc(interpretation)} O detalhe de compras, vendas, operações do Congresso e respetivo mapa temporal está na tab Smart money.</p></section>`;
  }

  function detailBase(s){
    const watched=isWatched(s.ticker), held=inPortfolio(s.ticker);
    return `<div class="market-dossier-shell"><div class="market-detail-head market-detail-head--editorial"><div><div class="market-kicker">${esc(isFund(s)?'ETF / Fundo':s.sector||'Empresa')}</div><div class="market-title-line"><h1>${esc(s.name||s.ticker)}</h1>${held?'<span class="market-held-badge market-held-badge--detail">Na carteira</span>':''}</div><h2 class="market-dossier-symbol">${esc(s.ticker)}</h2>${txt(s.exchange)?`<p class="market-dossier-exchange">${esc(s.exchange)}</p>`:''}${compactLiveBadge(s)}</div><div class="market-detail-actions"><button class="market-watch market-watch--detail ${watched?'is-active':''}" data-market-watch="${esc(s.ticker)}" aria-label="${watched?'Remover da lista':'Guardar para acompanhar'}">${watched?'★':'☆'}</button><button class="market-close" data-market-close>×</button></div></div>
      <div class="market-dossier-price-row"><div><small>PREÇO</small><strong data-live-field="current_price">${money(s.current_price,s.currency)}</strong></div>${n(s.market_cap)!=null?`<div><small>MARKET CAP</small><strong>${compact(s.market_cap)}</strong></div>`:''}</div>
      ${dossierScoreBoard(s)}
      ${dossierPillarCards(s)}
      ${dossierFullPicture(s)}
      ${dossierFinancialSnapshot(s)}
      ${dossierGrowthProfile(s)}
      ${dossierExpectationsContext(s)}
      ${dossierCatalystsRisks(s)}
      ${dossierSmartMoney(s)}
      <div class="market-tabs market-tabs--dossier" role="tablist" aria-label="Dossier"><button class="market-tab is-active" data-detail-tab="overview">Síntese</button><button class="market-tab" data-detail-tab="perspective">Perspetiva</button><button class="market-tab" data-detail-tab="growth">Growth</button><button class="market-tab" data-detail-tab="valuation">Valuation</button><button class="market-tab" data-detail-tab="earnings">Resultados</button><button class="market-tab" data-detail-tab="financials">Financeiro</button><button class="market-tab" data-detail-tab="smart">Smart money</button><button class="market-tab" data-detail-tab="news">Notícias</button></div><div id="marketDetailBody"></div></div>`;
  }

  function renderDetailTab(s,tab){
    const body=$m('marketDetailBody'); if(!body) return;
    if(tab==='overview') body.innerHTML=`${changePanel(s)}${recoveryPanel(s)}${drawdownPanel(s)}${evidencePanel(s)}${investmentCase(s)}${scoreExplanation(s)}`;
    if(tab==='perspective') {
      const strongBuy=n(s.analyst_strong_buy), buy=n(s.analyst_buy), hold=n(s.analyst_hold), sell=n(s.analyst_sell), strongSell=n(s.analyst_strong_sell);
      const buys=strongBuy==null&&buy==null?null:(strongBuy||0)+(buy||0);
      const holds=hold;
      const sells=sell==null&&strongSell==null?null:(sell||0)+(strongSell||0);
      const hasConsensus=buys!=null||holds!=null||sells!=null;
      const hasDirectionalConsensus=buys!=null&&sells!=null;
      const consensusLabel=!hasConsensus?'Cobertura insuficiente':!hasDirectionalConsensus?'Cobertura parcial':buys>sells?'Viés positivo':sells>buys?'Viés cauteloso':'Neutro';
      const consensusTone=hasDirectionalConsensus?(buys>sells?'is-positive':sells>buys?'is-negative':''):'';
      const revUp=n(s.analyst_eps_revisions_up_30d), revDown=n(s.analyst_eps_revisions_down_30d);
      const revisionSummary=revUp==null&&revDown==null?'—':`${revUp==null?'—':Math.round(revUp)} ↑ · ${revDown==null?'—':Math.round(revDown)} ↓`;
      body.innerHTML=`<div class="market-detail-card market-perspective-card"><div class="market-perspective-head"><div><small>CONSENSO</small><h4>O que o mercado espera</h4></div><span class="market-consensus ${consensusTone}">${consensusLabel}</span></div><div class="market-metrics"><div class="market-metric"><small>Target médio</small><strong>${money(s.analyst_price_target_mean,s.currency)}</strong></div><div class="market-metric"><small>Upside target</small><strong>${pct(s.analyst_price_target_upside_pct)}</strong></div><div class="market-metric"><small>Próx. earnings</small><strong>${shortDate(s.analyst_next_earnings_date)}</strong></div><div class="market-metric"><small>EPS próximo ano</small><strong>${pct(s.analyst_eps_next_y_growth)}</strong></div><div class="market-metric"><small>Rev. EPS 30d</small><strong>${revisionSummary}</strong></div><div class="market-metric"><small>Última surpresa</small><strong>${pct(s.analyst_latest_eps_surprise_pct)}</strong></div></div></div><div class="market-detail-card"><h4>Analistas</h4><div class="market-consensus-bar"><span class="is-buy" style="flex:${Math.max(0,buys??0)}"></span><span class="is-hold" style="flex:${Math.max(0,holds??0)}"></span><span class="is-sell" style="flex:${Math.max(0,sells??0)}"></span></div><div class="market-consensus-legend"><span>${buys==null?'—':Math.round(buys)} Comprar</span><span>${holds==null?'—':Math.round(holds)} Manter</span><span>${sells==null?'—':Math.round(sells)} Vender</span></div><p style="margin-top:10px">Estimativas são contexto, não recomendação. Dá mais peso à direção das revisões e à execução real do negócio do que ao target isolado.</p></div>`;
    }
    if(tab==='growth') body.innerHTML=`<div class="market-detail-card"><h4>Crescimento e resultados</h4><div class="market-metrics"><div class="market-metric"><small>Receita YoY</small><strong>${pct(s.revenue_yoy_latest??s.revenue_growth)}</strong></div><div class="market-metric"><small>Lucro YoY</small><strong>${pct(s.net_income_yoy_latest??s.earnings_growth)}</strong></div><div class="market-metric"><small>EPS YoY</small><strong>${pct(s.eps_yoy_latest??s.eps_growth)}</strong></div><div class="market-metric"><small>Margem líquida</small><strong>${pct(s.net_margin_latest??s.profit_margin)}</strong></div><div class="market-metric"><small>ROCE proxy</small><strong>${pct(s.roce_proxy)}</strong></div><div class="market-metric"><small>FCF</small><strong>${compact(s.free_cash_flow)}</strong></div></div></div>`;
    if(tab==='valuation') {
      const methods=Array.isArray(s.valuation_methods)?s.valuation_methods:[];
      const signalMap={undervalued:'Margem potencial',fair:'Próximo do fair value',overvalued:'Acima do fair value',uncertain:'Não acionável',insufficient:'Dados insuficientes'};
      body.innerHTML=`<div class="market-detail-card"><div class="market-perspective-head"><div><small>FAIR VALUE VESTRA</small><h4>${n(s.fair_value_low)==null?'Sem faixa robusta':`${money(s.fair_value_low,s.currency)} – ${money(s.fair_value_high,s.currency)}`}</h4></div><span class="market-consensus ${txt(s.valuation_signal)==='undervalued'?'is-positive':txt(s.valuation_signal)==='overvalued'?'is-negative':''}">${esc(signalMap[txt(s.valuation_signal)]||'—')}</span></div><div class="market-metrics"><div class="market-metric"><small>Fair value central</small><strong>${money(s.fair_value_mid,s.currency)}</strong></div><div class="market-metric"><small>Upside/downside</small><strong>${n(s.fair_value_upside_pct)==null?'—':`${n(s.fair_value_upside_pct)>=0?'+':''}${num(s.fair_value_upside_pct)}%`}</strong></div><div class="market-metric"><small>Margem segurança</small><strong>${n(s.margin_of_safety_pct)==null?'—':`${n(s.margin_of_safety_pct)>=0?'+':''}${num(s.margin_of_safety_pct)}%`}</strong></div><div class="market-metric"><small>Confiança valuation</small><strong>${esc(txt(s.valuation_confidence)||'—')}</strong></div><div class="market-metric"><small>Modelo</small><strong>${esc(txt(s.valuation_model)||txt(s.score_model)||'—')}</strong></div><div class="market-metric"><small>Métodos</small><strong>${methods.length}</strong></div></div><p>${esc(s.valuation_note||'Faixa peer-relative; não é target de analistas.')}</p>${methods.length?`<div class="market-watchpoints">${methods.slice(0,5).map(x=>`<span>${esc(x.method)} · ${money(x.fair_value,s.currency)}${n(x.weight)!=null?` · peso ${num(x.weight)}×`:''}</span>`).join('')}</div>`:''}<div class="market-score-layers"><p class="market-case-note"><strong>1 · De onde vem cada valor.</strong> Cada método pergunta a que preço esta empresa negociaria se o seu múltiplo ou yield convergisse para a mediana do próprio setor. Ex.: no P/E, fair value implícito = preço atual × P/E mediano do setor ÷ P/E da empresa.</p><p class="market-case-note"><strong>2 · Como se chega ao centro.</strong> Os métodos têm pesos diferentes conforme o modelo económico. O Vestra combina a média ponderada com a mediana das estimativas para reduzir o efeito de um método extremo. Nos modelos Geral e Tecnologia/Crescimento, Qualidade e Growth podem ajustar o centro, mas o ajuste total é limitado a ±12%.</p><p class="market-case-note"><strong>3 · Porque existe uma faixa.</strong> Com dois ou mais métodos a banda mínima é ±12%; com apenas um é ±18%. Se os métodos discordarem, a faixa alarga, até ao máximo de ±28%. Uma faixa larga significa maior incerteza, não maior upside.</p><p class="market-case-note"><strong>4 · Como nasce o sinal.</strong> “Undervalued” exige pelo menos +25% até ao fair value central; “Overvalued” começa em −20%. Entre estes limites a leitura é “Fair”. Risk Gate high/severe ou confidence score &lt;50 transforma o sinal em “Uncertain”, mesmo quando a estimativa numérica parece barata.</p><p class="market-case-note"><strong>5 · O que isto não é.</strong> Não é DCF, NAV inferido, target de analistas nem preço futuro previsto. É uma faixa peer-relative, dependente dos dados e dos comparáveis disponíveis.</p></div></div><div class="market-detail-card"><h4>Múltiplos</h4><div class="market-metrics"><div class="market-metric"><small>P/E</small><strong>${num(s.trailing_pe)}</strong></div><div class="market-metric"><small>Forward P/E</small><strong>${num(s.forward_pe)}</strong></div><div class="market-metric"><small>P/B</small><strong>${num(s.price_to_book)}</strong></div><div class="market-metric"><small>EV/EBITDA</small><strong>${num(s.enterprise_to_ebitda)}</strong></div><div class="market-metric"><small>vs sector P/E</small><strong>${pct(s.trailing_pe_vs_sector_pct)}</strong></div><div class="market-metric"><small>FCF yield</small><strong>${pct(s.fcf_yield)}</strong></div></div></div>`;
    }
    if(tab==='earnings') {
      const hist=Array.isArray(s.analyst_earnings_history_4q)?s.analyst_earnings_history_4q.slice(0,4):[];
      const estimateLabel={improving:'Expectativas a melhorar',deteriorating:'Expectativas a piorar',neutral:'Expectativas neutras',insufficient:'Cobertura insuficiente'}[txt(s.estimate_signal)]||'Cobertura insuficiente';
      const estimateCls=txt(s.estimate_signal)==='improving'?'is-positive':txt(s.estimate_signal)==='deteriorating'?'is-negative':'';
      const eDrivers=Array.isArray(s.earnings_intelligence_drivers)?s.earnings_intelligence_drivers:[];
      body.innerHTML=`<div class="market-detail-card market-perspective-card"><div class="market-perspective-head"><div><small>EXPECTATION MOMENTUM</small><h4>${estimateLabel}</h4></div><span class="market-consensus ${estimateCls}">${n(s.estimate_momentum_score)==null?'—':Math.round(n(s.estimate_momentum_score))+'/100'}</span></div><div class="market-metrics"><div class="market-metric"><small>Momentum</small><strong>${n(s.estimate_momentum_score)==null?'—':Math.round(n(s.estimate_momentum_score))+'/100'}</strong></div><div class="market-metric"><small>Breadth revisões</small><strong>${n(s.estimate_revision_breadth_pct)==null?'—':`${n(s.estimate_revision_breadth_pct)>=0?'+':''}${num(s.estimate_revision_breadth_pct)}%`}</strong></div><div class="market-metric"><small>Score revisões</small><strong>${n(s.estimate_revision_score)==null?'—':Math.round(n(s.estimate_revision_score))+'/100'}</strong></div><div class="market-metric"><small>Score surpresas</small><strong>${n(s.earnings_surprise_score)==null?'—':Math.round(n(s.earnings_surprise_score))+'/100'}</strong></div><div class="market-metric"><small>Confiança</small><strong>${esc(txt(s.estimate_confidence)||'—')}</strong></div><div class="market-metric"><small>Risco evento</small><strong>${esc(txt(s.earnings_event_risk)||'—')}</strong></div></div>${eDrivers.length?`<div class="market-watchpoints">${eDrivers.slice(0,5).map(x=>`<span>${esc(x)}</span>`).join('')}</div>`:''}<p>Overlay de expectativas; não altera diretamente o Score Vestra.</p></div><div class="market-detail-card"><h4>Resultados e catalisadores</h4><div class="market-metrics"><div class="market-metric"><small>Próx. resultados</small><strong>${shortDate(s.analyst_next_earnings_date)}</strong></div><div class="market-metric"><small>Dias até earnings</small><strong>${n(s.analyst_days_to_earnings)==null?'—':Math.round(n(s.analyst_days_to_earnings))}</strong></div><div class="market-metric"><small>Última surpresa EPS</small><strong>${pct(s.analyst_latest_eps_surprise_pct)}</strong></div><div class="market-metric"><small>Beats 4T</small><strong>${n(s.analyst_earnings_beats_4q)==null?'—':Math.round(n(s.analyst_earnings_beats_4q))}</strong></div><div class="market-metric"><small>Misses 4T</small><strong>${n(s.analyst_earnings_misses_4q)==null?'—':Math.round(n(s.analyst_earnings_misses_4q))}</strong></div><div class="market-metric"><small>Surpresa média 4T</small><strong>${pct(s.analyst_earnings_avg_surprise_4q)}</strong></div></div>${hist.length?`<div class="market-earnings-list">${hist.map(x=>`<div><span>${shortDate(x.date||x.earnings_date)}</span><strong>${pct(x.surprise_pct??x.eps_surprise_pct)}</strong></div>`).join('')}</div>`:''}</div>`;
    }
    if(tab==='financials') body.innerHTML=`<div class="market-detail-card"><h4>Saúde financeira</h4><div class="market-metrics"><div class="market-metric"><small>Margem bruta</small><strong>${pct(s.gross_margin)}</strong></div><div class="market-metric"><small>Margem operacional</small><strong>${pct(s.operating_margin)}</strong></div><div class="market-metric"><small>Margem líquida</small><strong>${pct(s.profit_margin)}</strong></div><div class="market-metric"><small>Debt / Equity</small><strong>${num(s.debt_to_equity)}</strong></div><div class="market-metric"><small>Current ratio</small><strong>${num(s.current_ratio)}</strong></div><div class="market-metric"><small>Quick ratio</small><strong>${num(s.quick_ratio)}</strong></div><div class="market-metric"><small>Cash flow operacional</small><strong>${compact(s.operating_cash_flow)}</strong></div><div class="market-metric"><small>Free cash flow</small><strong>${compact(s.free_cash_flow)}</strong></div><div class="market-metric"><small>Net cash / dívida</small><strong>${compact(s.net_cash)}</strong></div></div></div><div class="market-detail-card"><h4>Qualidade dos lucros</h4><div class="market-metrics"><div class="market-metric"><small>Score qualidade</small><strong>${n(s.earnings_quality_pct)==null?'—':Math.round(n(s.earnings_quality_pct))+'/100'}</strong></div><div class="market-metric"><small>Conversão caixa/lucro</small><strong>${n(s.cash_conversion_ratio)==null?'—':num(s.cash_conversion_ratio)+'×'}</strong></div><div class="market-metric"><small>Accrual ratio</small><strong>${pct(s.accrual_ratio)}</strong></div><div class="market-metric"><small>Margem FCF</small><strong>${pct(s.fcf_margin)}</strong></div></div><p style="margin-top:10px">Quanto maior a conversão de lucro em caixa e menor o accrual ratio, menor a dependência de resultados puramente contabilísticos.</p></div><div class="market-detail-card"><h4>Alocação de capital</h4><div class="market-metrics"><div class="market-metric"><small>Score alocação</small><strong>${n(s.capital_allocation_pct)==null?'—':Math.round(n(s.capital_allocation_pct))+'/100'}</strong></div><div class="market-metric"><small>Diluição YoY</small><strong>${pct(s.diluted_shares_yoy)}</strong></div><div class="market-metric"><small>Buybacks último T</small><strong>${compact(s.repurchases_last_quarter)}</strong></div><div class="market-metric"><small>ROCE proxy</small><strong>${pct(s.roce_proxy)}</strong></div><div class="market-metric"><small>Cobertura dividendo/FCF</small><strong>${n(s.dividend_fcf_coverage)==null?'—':num(s.dividend_fcf_coverage)+'×'}</strong></div></div></div><div class="market-detail-card"><h4>Qualidade dos dados</h4><div class="market-metrics"><div class="market-metric"><small>Cobertura</small><strong>${n(s.data_coverage_pct)==null?'—':Math.round(n(s.data_coverage_pct))+'%'}</strong></div><div class="market-metric"><small>Confiança da evidência</small><strong>${n(s.confidence_score)==null?esc(txt(s.data_confidence)||'—'):Math.round(n(s.confidence_score))+'/100'}</strong></div><div class="market-metric"><small>Fiabilidade do Score</small><strong>${esc(scoreReliabilityLabel(s.score_reliability))}</strong></div><div class="market-metric"><small>Modelo</small><strong>${esc(scoreModelLabel(s.score_model))}</strong></div>${n(s.model_native_coverage_pct)==null?'':`<div class="market-metric"><small>Cobertura nativa do modelo</small><strong>${Math.round(n(s.model_native_coverage_pct))}%</strong></div>`}</div><p style="margin-top:10px">Cobertura diz quanto dos dados esperados está disponível. Confiança da evidência combina cobertura, qualidade e atualidade das fontes, concordância entre fontes e identidade. Fiabilidade do Score indica se essa evidência é suficiente para publicar o ranking sem moderação excessiva.</p>${Array.isArray(s.data_sources)&&s.data_sources.length?`<p class="market-case-note" style="margin-top:8px">Fontes: ${s.data_sources.map(esc).join(' · ')}</p>`:''}${s.identity_source?`<p class="market-case-note" style="margin-top:6px">Identidade: ${esc(s.identity_source)}${s.isin?' · ISIN '+esc(s.isin):''}${s.lei?' · LEI '+esc(s.lei):''}</p>`:''}</div>`;
    if(tab==='smart') {
      const ins=Array.isArray(s.insider_transactions)?s.insider_transactions.slice(0,8):[];
      const con=Array.isArray(s.congress_trades)?s.congress_trades.slice(0,8):[];
      const buyCount=n(s.insider_buy_count_30d), sellCount=n(s.insider_sell_count_30d);
      const buyValue=n(s.insider_buy_value_30d), sellValue=n(s.insider_sell_value_30d);
      const hasInsiderSummary=buyCount!=null||sellCount!=null||buyValue!=null||sellValue!=null;
      const insiderSummary=hasInsiderSummary
        ? `${buyCount==null?'—':Math.round(buyCount)} compras (${buyValue==null?'—':money(buyValue,'USD')}) · ${sellCount==null?'—':Math.round(sellCount)} vendas (${sellValue==null?'—':money(sellValue,'USD')})`
        : 'Cobertura insider insuficiente nos últimos 30 dias.';
      body.innerHTML=`<div class="market-detail-card market-smart-map-card"><div class="market-perspective-head"><div><small>SMART MONEY MAP</small><h4>Preço e operações declaradas</h4></div><span class="market-data-age">12 meses</span></div>${smartMoneyTimeline(s)}</div><div class="market-detail-card"><h4>Insiders · 30 dias</h4><p>${esc(insiderSummary)}</p>${ins.length?`<ul>${ins.map(x=>`<li>${esc(x.name||x.insider||'Insider')} · ${esc(x.transaction_type||x.type||'')} · ${money(x.value||x.transaction_value,'USD')}</li>`).join('')}</ul>`:''}</div><div class="market-detail-card"><h4>Congresso</h4>${con.length?`<ul>${con.map(x=>`<li>${esc(x.representative||x.member||x.name||'')} · ${esc(x.type||x.transaction||'')} · ${esc(x.amount||x.amount_range||'—')}</li>`).join('')}</ul>`:'<p id="marketCongressEmpty">A verificar divulgações recentes…</p>'}</div>`;
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
  function resetDossierViewport(){
    const panel=sheetPanel(); if(!panel) return;
    panel.scrollTop=0; panel.scrollLeft=0;
    // One delayed reset after layout is enough; repeated RAF writes can fight iOS momentum.
    setTimeout(()=>{ if(!$m('marketSheet')?.hidden){ panel.scrollTop=0; panel.scrollLeft=0; } }, 35);
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
    notifyMarketSheetChanged('ticker-open');
    resetDossierViewport();
    enrichTickerLive(s);
  }
  function closeSheet(){
    const sh=$m('marketSheet'); if(!sh)return;
    const returnView=txt(sh.dataset.returnView);
    sh.hidden=true; sh.setAttribute('aria-hidden','true'); sh.dataset.liveReady='0'; sh.dataset.tool=''; sh.dataset.returnView='';
    notifyMarketSheetChanged('close');
    document.documentElement.classList.remove('modal-open'); document.body.classList.remove('modal-open');
    const panel=sheetPanel(); if(panel){panel.scrollTop=0;panel.scrollLeft=0;}
    if((returnView==='assets' || returnView==='market') && typeof setView==='function') setView(returnView);
  }

  function portfolioConviction(s){
    // Conviction answers "how strong is the investment thesis?", not "how much
    // evidence do we have?" or "is risk acceptable?". Confidence and Risk Gate
    // remain independent decision gates so the same weakness is not counted twice.
    const score=n(s?.score), est=n(s?.estimate_momentum_score);
    const valMap={undervalued:85,fair:65,overvalued:25,uncertain:40,insufficient:45};
    const valuationSignal=txt(s?.valuation_signal);
    const val=Object.prototype.hasOwnProperty.call(valMap,valuationSignal)?valMap[valuationSignal]:null;
    // Score is the required owner of fundamental alpha. Missing secondary signals
    // stay neutral rather than silently renormalising the remaining weights upward.
    if(score==null) return null;
    let x=score*.70+(est??50)*.12+(val??50)*.18;
    if(txt(s?.thesis_direction)==='up') x+=4;
    if(txt(s?.thesis_direction)==='down') x-=7;
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

  function portfolioFit(r, sectorRows, analysed, etfs, targets=loadPortfolioTargets()){
    const positionPct=analysed>0?r.value/analysed*100:0;
    const sector=txt(r.stock?.sector);
    const sectorPct=sector?sectorRows.find(x=>x.sector===sector)?.pct||0:0;
    const indirectPct=isFund(r.stock)?0:indirectExposurePct(r.stock,etfs);
    const maxPos=Math.max(3,Math.min(30,n(targets?.maxPosition)||10));
    const maxSector=Math.max(10,Math.min(60,n(targets?.maxSector)||25));
    const posSevere=maxPos*1.5, sectorSevere=maxSector*1.4;
    const overlapWatch=targets?.overlap==='reduce'?2:Infinity, overlapSevere=targets?.overlap==='reduce'?4:Infinity;
    const flags=[];
    if(positionPct>=posSevere) flags.push(`posição ${positionPct.toFixed(0)}% > objetivo ${maxPos}%`);
    else if(positionPct>=maxPos) flags.push(`posição acima do objetivo ${positionPct.toFixed(0)}% > ${maxPos}%`);
    if(sectorPct>=sectorSevere) flags.push(`setor concentrado ${sectorPct.toFixed(0)}% > objetivo ${maxSector}%`);
    else if(sectorPct>=maxSector) flags.push(`setor acima do objetivo ${sectorPct.toFixed(0)}% > ${maxSector}%`);
    if(indirectPct>=overlapWatch) flags.push(`+${indirectPct.toFixed(1)}% indireto via ETFs`);
    let fit='balanced';
    if(positionPct>=posSevere||sectorPct>=sectorSevere||indirectPct>=overlapSevere) fit='concentrated';
    else if(positionPct>=maxPos||sectorPct>=maxSector||indirectPct>=overlapWatch) fit='watch';
    return {positionPct,sectorPct,indirectPct,fit,flags,maxPos,maxSector};
  }
  function portfolioFitSummary(ctx){
    const fit=ctx||{};
    const label=fit.fit==='concentrated'?'Concentrado':fit.fit==='watch'?'Atenção':'Equilibrado';
    const parts=[
      `posição ${(n(fit.positionPct)||0).toFixed(1)}%`,
      `setor ${(n(fit.sectorPct)||0).toFixed(1)}%`,
    ];
    if((n(fit.indirectPct)||0)>0)parts.push(`ETF indireto ${(n(fit.indirectPct)||0).toFixed(1)}%`);
    return `Portfolio Fit: ${label} · ${parts.join(' · ')}`;
  }

  function fundExpensePct(stock){
    const raw=n(stock?.expense_ratio);
    if(raw==null||raw<0)return null;
    return Math.abs(raw)<=1?raw*100:raw;
  }
  function fundEtfScore(stock){
    const published=n(stock?.etf_score);
    if(published!=null)return published;
    const assessed=window.VestraEtfIntelligence?.assess?.(stock);
    return n(assessed?.etf_score);
  }
  function fundEtfCoverage(stock){
    const published=n(stock?.etf_score_coverage_pct);
    if(published!=null)return published;
    const assessed=window.VestraEtfIntelligence?.assess?.(stock);
    return n(assessed?.etf_score_coverage_pct);
  }
  function fundThemeKeys(stock){
    return ETF_THEMES.filter(([key,,matcher])=>key!=='all'&&matcher.test(fundThemeText(stock))).map(([key])=>key);
  }
  function fundHoldingsOverlapPct(a,b){
    const left=new Map((a?.top_holdings||[]).map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null&&w>0));
    const right=new Map((b?.top_holdings||[]).map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null&&w>0));
    if(!left.size||!right.size)return null;
    let overlap=0;
    for(const [ticker,w] of left)if(right.has(ticker))overlap+=Math.min(w,right.get(ticker));
    return Math.max(0,Math.min(100,overlap));
  }
  function fundPortfolioDuplicationPct(stock, heldEtfs, sourceTicker=''){
    const source=txt(sourceTicker).toUpperCase();
    let maxOverlap=0, observed=false;
    for(const row of heldEtfs||[]){
      const ticker=txt(row?.stock?.ticker).toUpperCase();
      if(!ticker||ticker===source||ticker===txt(stock?.ticker).toUpperCase())continue;
      const overlap=fundHoldingsOverlapPct(stock,row.stock);
      if(overlap==null)continue;
      observed=true; maxOverlap=Math.max(maxOverlap,overlap);
    }
    return observed?maxOverlap:null;
  }
  function sameFundExposure(source,candidate){
    const a=new Set(fundThemeKeys(source)), b=new Set(fundThemeKeys(candidate));
    const common=[...a].filter(x=>b.has(x));
    if(!common.length)return {match:false,common:[],overlap:null};
    const overlap=fundHoldingsOverlapPct(source,candidate);
    const sameCategory=txt(source?.fund_category||source?.category).toLowerCase()&&txt(source?.fund_category||source?.category).toLowerCase()===txt(candidate?.fund_category||candidate?.category).toLowerCase();
    const specific=common.some(x=>!['world','europe','emerging','dividend','bonds'].includes(x));
    const match=overlap==null?sameCategory||specific:overlap>=30||(sameCategory&&specific);
    return {match,common,overlap};
  }
  function findEtfOptimizeAlternatives(ranked,heldTickers){
    const heldEtfs=ranked.filter(r=>isFund(r.stock));
    const universe=M.stocks.filter(isFund);
    const suggestions=[];
    for(const row of heldEtfs){
      const source=row.stock, sourceScore=fundEtfScore(source), sourceCoverage=fundEtfCoverage(source);
      if(sourceScore==null||sourceCoverage==null||sourceCoverage<50)continue;
      const sourceTer=fundExpensePct(source);
      const sourceDup=fundPortfolioDuplicationPct(source,heldEtfs,txt(source.ticker));
      const sourceDiv=n(source?.etf_score_dimensions?.diversification);
      const candidates=universe.map(candidate=>{
        const key=txt(candidate?.ticker).toUpperCase().replace(/\.[A-Z]+$/,'');
        if(!key||heldTickers.has(key))return null;
        const exposure=sameFundExposure(source,candidate);
        if(!exposure.match)return null;
        const score=fundEtfScore(candidate), coverage=fundEtfCoverage(candidate);
        if(score==null||coverage==null||coverage<50)return null;
        const ter=fundExpensePct(candidate);
        const scoreDelta=score-sourceScore;
        const terSaving=sourceTer!=null&&ter!=null?sourceTer-ter:null;
        const candidateDup=fundPortfolioDuplicationPct(candidate,heldEtfs,txt(source.ticker));
        const dupDelta=sourceDup!=null&&candidateDup!=null?candidateDup-sourceDup:null;
        const candDiv=n(candidate?.etf_score_dimensions?.diversification);
        const divDelta=sourceDiv!=null&&candDiv!=null?candDiv-sourceDiv:null;
        const improvements=[
          scoreDelta>=3,
          terSaving!=null&&terSaving>=0.05,
          dupDelta!=null&&dupDelta<=-5,
          divDelta!=null&&divDelta>=5,
        ].filter(Boolean).length;
        if(!improvements)return null;
        if(scoreDelta<-2)return null;
        if(terSaving!=null&&terSaving<-0.03)return null;
        if(dupDelta!=null&&dupDelta>10)return null;
        const evidence=[exposure.overlap!=null?1:0,terSaving!=null?1:0,dupDelta!=null?1:0,divDelta!=null?1:0].reduce((a,b)=>a+b,0);
        return {source,candidate,sourceScore,score,scoreDelta,sourceTer,ter,terSaving,sourceDup,candidateDup,dupDelta,divDelta,exposure,improvements,evidence};
      }).filter(Boolean).sort((a,b)=>b.improvements-a.improvements||b.scoreDelta-a.scoreDelta||(b.terSaving??-99)-(a.terSaving??-99)||(b.evidence-a.evidence));
      if(candidates[0])suggestions.push(candidates[0]);
    }
    return suggestions.sort((a,b)=>b.improvements-a.improvements||b.scoreDelta-a.scoreDelta||(b.terSaving??-99)-(a.terSaving??-99)).slice(0,3);
  }
  function renderEtfOptimizeCard(rows){
    if(!rows?.length)return '';
    const meta=x=>{
      const parts=[`ETF Score ${Math.round(x.sourceScore)}→${Math.round(x.score)}`];
      if(x.sourceTer!=null&&x.ter!=null)parts.push(`TER ${x.sourceTer.toFixed(2)}→${x.ter.toFixed(2)}%`);
      if(x.exposure.overlap!=null)parts.push(`overlap exposição ~${x.exposure.overlap.toFixed(0)}%`);
      if(x.sourceDup!=null&&x.candidateDup!=null)parts.push(`duplicação carteira ${x.sourceDup.toFixed(0)}→${x.candidateDup.toFixed(0)}%`);
      return parts.join(' · ');
    };
    return `<div class="market-detail-card market-etf-optimize"><div class="market-perspective-head"><div><small>ETF OPTIMIZE · MESMA EXPOSIÇÃO</small><h4>ETFs que podes comparar</h4></div><span class="market-data-age">${rows.length} candidatos</span></div><p class="market-case-note">Compara ETFs com exposição temática semelhante. A Vestra exige melhoria material em ETF Score, custo, diversificação ou duplicação e bloqueia candidatos que agravem materialmente as restantes dimensões.</p><div class="market-list">${rows.map(x=>renderRow(x.candidate,`Alternativa a ${x.source.ticker} · ${meta(x)}`)).join('')}</div><p class="market-case-note">Isto é uma shortlist de research, não uma recomendação automática de troca. Não altera Vestra Score, Discovery Score nem Portfolio Action.</p></div>`;
  }

  function portfolioAction(stock, alternativesByTicker, context){
    const conviction=portfolioConviction(stock);
    const evidence=portfolioMoveEvidence(stock,conviction);
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
    // Portfolio construction context must come from portfolioFit(), which already
    // applies the user's current targets and overlap policy. Do not reintroduce
    // fixed thresholds here or the explanation can disagree with the decision.
    if(Array.isArray(ctx.flags)) reasons.push(...ctx.flags.slice(0,2));
    // Thesis direction and estimate momentum already belong to Conviction.
    // Portfolio Action must not apply those signals a second time; Risk Gate
    // remains an independent safety layer and portfolio context remains separate.
    const structuralDeterioration=gate==='high'||gate==='severe'||(conviction!=null&&conviction<50);
    if(alt && alt.portfolioFit!=='worse' && structuralDeterioration) {
      const fitNote=alt.portfolioFit==='better'?' · melhora diversificação':'';
      return {key:'replace',label:'Substituir',tone:'risk',reason:`${reasons[0]||'convicção fraca'} · alternativa ${alt.to.ticker} superior${fitNote}`};
    }
    if(structuralDeterioration||gate==='watch') return {key:'review',label:'Rever',tone:structuralDeterioration?'risk':'warn',reason:reasons.slice(0,2).join(' · ')||(gate==='watch'?'Risk Gate watch':'convicção baixa')};
    if(evidence.reinforceEligible) {
      if(ctx.fit==='concentrated'||ctx.fit==='watch') return {key:'hold',label:'Manter',tone:'neutral',reason:`boa tese · não reforçar por ${ctx.flags?.[0]||(ctx.fit==='watch'?'Portfolio Fit em atenção':'concentração')}`};
      return {key:'reinforce',label:'Reforçar',tone:'positive',reason:reasons.slice(0,2).join(' · ')||'convicção elevada'};
    }
    if(conviction==null) return {key:'hold',label:'Manter',tone:'neutral',reason:reasons.slice(0,2).join(' · ')||'convicção indisponível com a evidência atual'};
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
  function portfolioMoveEvidence(stock, conviction=null){
    const conf=n(stock?.confidence_score), valuation=txt(stock?.valuation_signal), estimates=txt(stock?.estimate_signal), thesis=txt(stock?.thesis_direction), gate=txt(stock?.risk_gate);
    const reliability=txt(stock?.score_reliability).toLowerCase(), coverage=n(stock?.data_coverage_pct), critical=n(stock?.critical_metric_coverage_pct);
    const conv=n(conviction);
    const actionableValuation=['undervalued','fair'].includes(valuation);
    const reliabilityReady=['robust','moderate_evidence'].includes(reliability);
    const evidenceReady=reliabilityReady&&coverage!=null&&coverage>=65&&critical!=null&&critical>=50;
    const strict=conf!=null&&conf>=60&&evidenceReady&&gate==='clear'&&actionableValuation&&estimates!=='deteriorating'&&thesis!=='down';
    const reinforceEligible=strict&&conv!=null&&conv>=70;
    const acceptable=(conf==null||conf>=45)&&reliability!=='insufficient_data'&&!(valuation==='overvalued'&&estimates==='deteriorating')&&thesis!=='down'&&!['high','severe'].includes(gate);
    const warnings=[]; let penalty=0;
    if(conf==null){penalty+=7;warnings.push('confiança sem score');}
    else if(conf<60){penalty+=(60-conf)*.35+3;warnings.push(`confiança ${Math.round(conf)}`);}
    if(!reliability){penalty+=7;warnings.push('fiabilidade do Score não classificada');}
    else if(!reliabilityReady){penalty+=8;warnings.push(`fiabilidade ${reliability}`);}
    if(coverage==null||coverage<65){penalty+=6;warnings.push('cobertura fundamental insuficiente');}
    if(critical==null||critical<50){penalty+=6;warnings.push('cobertura crítica insuficiente');}
    if(!valuation){penalty+=5;warnings.push('valuation sem sinal');}
    else if(valuation==='overvalued'){penalty+=9;warnings.push('valuation exigente');}
    else if(valuation==='uncertain'){penalty+=3;warnings.push('valuation incerto');}
    else if(valuation==='insufficient'){penalty+=5;warnings.push('valuation insuficiente');}
    if(estimates==='deteriorating'){penalty+=8;warnings.push('expectativas a piorar');}
    if(thesis==='down'){penalty+=7;warnings.push('tese a deteriorar');}
    if(!gate){penalty+=6;warnings.push('Risk Gate não classificado');}
    else if(gate==='watch'){penalty+=6;warnings.push('Risk Gate watch');}
    const tier=strict?'preferred':acceptable?'acceptable':'research';
    if(tier==='research') penalty+=12;
    return {conf,reliability,coverage,critical,valuation,estimates,thesis,gate,conviction:conv,evidenceReady,strict,reinforceEligible,acceptable,tier,penalty,warnings};
  }
  function evaluatePortfolioMove({mode='replace',sourceStock=null,destination,rows=[],amount=0,totalAfter=1,sourceConv=null,destinationConv=null,positionPct=0,sectorPct=0,indirect=0,sourceIndirect=0}={}){
    const targets=loadPortfolioTargets(), maxPos=Math.max(3,Math.min(30,n(targets.maxPosition)||10)), maxSector=Math.max(10,Math.min(60,n(targets.maxSector)||25));
    const evidence=portfolioMoveEvidence(destination,destinationConv);
    const riskPenalty=riskBudgetPenalty(destination,rows,amount,totalAfter,sourceStock);
    const overlapDelta=indirect-sourceIndirect;
    const convictionGain=sourceConv!=null&&destinationConv!=null?destinationConv-sourceConv:null;
    const convDelta=convictionGain==null?null:convictionGain*(amount/(totalAfter||1));
    const sourceAutomatable=!sourceStock||(!isFund(sourceStock)&&n(sourceStock.score)!=null&&n(sourceStock.confidence_score)!=null);
    let autoEligible=false;
    if(mode==='fresh'){
      autoEligible=evidence.reinforceEligible&&riskPenalty<5&&(targets.overlap!=='reduce'||indirect<2)&&positionPct<=maxPos&&sectorPct<=maxSector;
    }else if(mode==='alternative'){
      autoEligible=sourceAutomatable&&evidence.strict&&convictionGain>=5&&convDelta>0&&overlapDelta<1.5&&riskPenalty<5;
    }else if(mode==='scenario'){
      autoEligible=evidence.strict&&convDelta>0&&overlapDelta<2&&riskPenalty<5;
    }else{
      autoEligible=sourceAutomatable&&evidence.strict&&convictionGain>=2&&convDelta>0&&overlapDelta<2&&positionPct<=maxPos+1&&sectorPct<=maxSector+1&&riskPenalty<5;
    }
    const warnings=[...evidence.warnings];
    if(sourceStock&&!sourceAutomatable) warnings.push('origem apenas para análise manual');
    if(mode==='alternative'&&convictionGain!=null&&convictionGain<5) warnings.push('melhoria de convicção insuficiente');
    else if(mode!=='fresh'&&convictionGain!=null&&convictionGain<2) warnings.push('melhoria de convicção insuficiente');
    if(mode==='alternative'&&overlapDelta>=1.5) warnings.push('aumenta overlap');
    else if(mode!=='fresh'&&overlapDelta>=2) warnings.push('aumenta overlap');
    if(mode==='fresh'&&targets.overlap==='reduce'&&indirect>=2) warnings.push('overlap elevado');
    if(riskPenalty>=5) warnings.push('pressiona orçamento de risco');
    if(positionPct>(mode==='replace'?maxPos+1:maxPos)) warnings.push('excede objetivo por posição');
    if(sectorPct>(mode==='replace'?maxSector+1:maxSector)) warnings.push('excede objetivo setorial');
    return {targets,maxPos,maxSector,evidence,riskPenalty,overlapDelta,convictionGain,convDelta,sourceAutomatable,autoEligible,warnings};
  }

  function renderRiskBudget(rows,total=0){
    const profile=portfolioRiskProfile(rows,total>0?total:undefined), t=loadPortfolioTargets();
    const analysedValue=rows.reduce((a,r)=>a+(n(r.value)||0),0);
    const riskBase=total>0?total:(analysedValue||1);
    const coverage=total>0?analysedValue/total*100:100;
    const partialCoverage=total>0&&coverage<35;
    const factorCoveredValue=rows.reduce((a,r)=>a+(stockRiskTags(r.stock).length?(n(r.value)||0):0),0);
    const factorCoverage=factorCoveredValue/riskBase*100;
    const partialFactorCoverage=factorCoverage<35;
    const maxFactor=n(t.maxFactor)||45, maxCurrency=n(t.maxCurrency)||70, maxRegion=n(t.maxRegion)||70;
    const breaches=[...profile.factors.filter(x=>x.pct>maxFactor).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxFactor}%`),...profile.currencies.filter(x=>x.pct>maxCurrency).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxCurrency}%`),...profile.regions.filter(x=>x.pct>maxRegion).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxRegion}%`)];
    const excess=profile.factors.reduce((a,x)=>a+Math.max(0,x.pct-maxFactor),0)+profile.currencies.reduce((a,x)=>a+Math.max(0,x.pct-maxCurrency),0)+profile.regions.reduce((a,x)=>a+Math.max(0,x.pct-maxRegion),0);
    const incomplete=partialCoverage||partialFactorCoverage||!profile.factors.length||!profile.currencies.length||!profile.regions.length;
    const rawFit=Math.max(0,Math.min(100,Math.round(100-excess*1.4))), fit=incomplete?null:rawFit, hasBreaches=breaches.length>0;
    const tone=incomplete?'is-warn':!hasBreaches&&fit>=85?'is-positive':fit>=65?'is-warn':'is-risk';
    const statusLabel=incomplete?'Dados parciais':!hasBreaches&&fit>=85?'Boa diversificação':fit>=65?'Atenção':'Concentração elevada';
    const riskRows=(items,limit,max)=>items.slice(0,limit).map(x=>{
      const over=x.pct>max, width=Math.max(2,Math.min(100,x.pct));
      return `<div class="market-risk-item ${over?'is-over':''}"><div class="market-risk-item__head"><strong>${esc(x.name)}</strong><span>${x.pct.toFixed(0)}%${over?` · limite ${max}%`:''}</span></div><div class="market-risk-bar"><i style="width:${width}%"></i></div></div>`;
    }).join('');
    const html=`<div class="market-detail-card market-risk-budget"><div class="market-perspective-head"><div><small>PORTFOLIO RISK BUDGET · PROXY</small><h4>Diversificação da carteira</h4></div><div class="market-risk-score ${tone}"><strong>${fit==null?'—':fit+'/100'}</strong><small>${statusLabel}</small></div></div><p class="market-risk-intro">Mostra onde a carteira está mais dependente do mesmo fator, moeda ou região. Quanto maior a concentração, maior o impacto se esse risco correr mal.</p><div class="market-risk-grid"><section class="market-risk-group"><div class="market-risk-group__title"><strong>Fatores</strong><small>máx. ${maxFactor}%</small></div><div>${riskRows(profile.factors,5,maxFactor)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section><section class="market-risk-group"><div class="market-risk-group__title"><strong>Moedas</strong><small>máx. ${maxCurrency}%</small></div><div>${riskRows(profile.currencies,4,maxCurrency)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section><section class="market-risk-group"><div class="market-risk-group__title"><strong>Regiões</strong><small>máx. ${maxRegion}%</small></div><div>${riskRows(profile.regions,4,maxRegion)||'<p class="market-risk-empty">Sem classificação suficiente.</p>'}</div></section></div>${incomplete?`<div class="market-risk-alert"><strong>${partialCoverage?'Cobertura insuficiente':partialFactorCoverage?'Cobertura de fatores insuficiente':'Classificação incompleta'}</strong><span>${partialCoverage?`Só ${coverage.toFixed(0)}% da carteira tem research; o Risk Fit global fica indisponível.`:partialFactorCoverage?`Só ${factorCoverage.toFixed(0)}% da carteira tem classificação de fatores; o Risk Fit global fica indisponível.`:'O Risk Fit fica indisponível até existirem dados para fatores, moedas e regiões.'}</span></div>`:breaches.length?`<div class="market-risk-alert"><strong>${breaches.length} ${breaches.length===1?'excesso a acompanhar':'excessos a acompanhar'}</strong><ul>${breaches.slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:'<div class="market-risk-ok"><strong>Dentro dos limites definidos</strong><span>Não há concentrações acima dos teus Portfolio Targets.</span></div>'}<p class="market-risk-footnote">Leitura de exposição, não previsão de volatilidade. Usa os dados disponíveis e pode conter proxies quando moeda/região não vêm explicitamente da fonte.</p></div>`;
    return {fit,html,profile,breaches,hasBreaches,incomplete,coverage,factorCoverage};
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
  function renderStressScenario(rows,key,total=0){
    const sc=PORTFOLIO_STRESS_SCENARIOS[key], r=portfolioStress(rows,key);
    const analysedValue=rows.reduce((a,x)=>a+(n(x.value)||0),0);
    const coverage=total>0?analysedValue/total*100:100;
    const partial=total>0&&coverage<35;
    const tone=r.resilience>=75?'is-positive':r.resilience>=55?'is-warn':'is-risk';
    return `<div class="market-stress-result" data-stress-panel="${key}" ${key==='rates'?'':'hidden'}><div class="market-stress-kpis"><div><small>Impacto proxy</small><strong>${r.portfolioImpact>=0?'+':''}${r.portfolioImpact.toFixed(1)}%</strong></div><div><small>Resiliência</small><strong class="${tone}">${r.resilience}/100</strong></div><div><small>Exposição forte</small><strong>${r.exposedWeight.toFixed(0)}%</strong></div></div><p class="market-case-note">${esc(sc.note)}</p>${r.top.length?`<div class="market-stress-list">${r.top.map(x=>`<button type="button" data-market-ticker="${esc(x.stock.ticker)}"><span><strong>${esc(x.stock.ticker)}</strong><small>peso ${x.weight.toFixed(1)}% · choque ${x.impact.toFixed(0)}%</small></span><em>${x.contribution.toFixed(2)} pp</em></button>`).join('')}</div>`:'<p class="market-case-note">Sem exposição negativa material identificada neste cenário.</p>'}<p class="market-case-note">${partial?`Resultado parcial: ${coverage.toFixed(0)}% da carteira tem cobertura de research; impacto e resiliência referem-se apenas à parte analisável. `:''}Stress proxy, não previsão: não modela correlações dinâmicas, opções, hedges, impostos nem liquidez.</p></div>`;
  }
  function renderPortfolioStressTest(rows,total=0){
    const analysedValue=rows.reduce((a,r)=>a+(n(r.value)||0),0);
    const coverage=total>0?analysedValue/total*100:100;
    return `<div class="market-detail-card market-stress-test"><div class="market-perspective-head"><div><small>PORTFOLIO STRESS TEST · PROXY</small><h4>Como reage a parte analisável?</h4></div><span class="market-data-age">${coverage.toFixed(0)}% coberto</span></div><div class="market-stress-tabs">${Object.entries(PORTFOLIO_STRESS_SCENARIOS).map(([k,v],i)=>`<button type="button" data-stress-scenario="${k}" class="${i===0?'is-active':''}">${esc(v.label)}</button>`).join('')}</div>${Object.keys(PORTFOLIO_STRESS_SCENARIOS).map(k=>renderStressScenario(rows,k,total)).join('')}</div>`;
  }

  const INFLATION_BUCKETS={
    benefit:{label:'Beneficia',tone:'benefit'},
    resilient:{label:'Resiliente',tone:'resilient'},
    neutral:{label:'Neutro',tone:'neutral'},
    vulnerable:{label:'Vulnerável',tone:'vulnerable'},
  };
  function averageKnown(values){
    const xs=values.map(n).filter(v=>v!=null);
    return xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
  }
  function inflationFundProfile(stock){
    const hay=`${txt(stock?.name)} ${txt(stock?.fund_theme)} ${txt(stock?.fund_style)} ${txt(stock?.sector)} ${txt(stock?.industry)}`.toLowerCase();
    if(/gold|silver|precious metal|commodity|commodities|oil|gas|energy|uranium|copper|mining|materials|agricultur/.test(hay)) return {bucket:'benefit',drivers:['exposição temática a ativos reais'],evidence:1};
    if(/consumer staples|consumer defensive|healthcare|infrastructure/.test(hay)) return {bucket:'resilient',drivers:['exposição temática defensiva'],evidence:1};
    if(/real estate|reit|long duration|technology|growth/.test(hay)) return {bucket:'vulnerable',drivers:['tema sensível a taxas/discount rate'],evidence:1};
    return null;
  }
  function inflationShieldProfile(stock){
    if(isFund(stock)) return inflationFundProfile(stock);
    const sec=txt(stock?.sector).toLowerCase(), ind=txt(stock?.industry).toLowerCase();
    if(!sec&&!ind) return null;
    let structural=0, sectorDriver='setor sem viés forte';
    if(/energy/.test(sec)){structural=2.2;sectorDriver='energia tende a captar inflação de commodities';}
    else if(/basic materials|materials/.test(sec)){structural=1.8;sectorDriver='materiais têm ligação direta a preços de inputs';}
    else if(/consumer defensive/.test(sec)){structural=1.15;sectorDriver='procura defensiva em bens essenciais';}
    else if(/healthcare/.test(sec)){structural=.75;sectorDriver='procura relativamente defensiva';}
    else if(/industrials/.test(sec)){structural=.45;sectorDriver='exposição cíclica com algum pricing power';}
    else if(/utilities/.test(sec)){structural=.35;sectorDriver='receitas defensivas, mas sensibilidade a taxas';}
    else if(/financial/.test(sec)){structural=.25;sectorDriver='impacto misto entre inflação e taxas';}
    else if(/real estate/.test(sec)){structural=-.45;sectorDriver='rendas podem reajustar, mas duration e financiamento pesam';}
    else if(/technology/.test(sec)){structural=-.65;sectorDriver='duration longa pode sofrer com taxas reais altas';}
    else if(/communication/.test(sec)){structural=-.55;sectorDriver='duration e custos podem pressionar múltiplos';}
    else if(/consumer cyclical/.test(sec)){structural=-1.05;sectorDriver='procura discricionária e margens mais expostas';}

    const pricing=averageKnown([stock?.moat_score,stock?.profitability_pct,stock?.stability_pct]);
    const balance=averageKnown([stock?.balance_pct,stock?.leverage_pct,stock?.cashflow_pct]);
    const drivers=[sectorDriver];
    let adjustment=0, evidence=1;
    if(pricing!=null){
      evidence++;
      if(pricing>=70){adjustment+=.95;drivers.push('pricing power/margens proxy fortes');}
      else if(pricing>=55){adjustment+=.35;drivers.push('pricing power/margens proxy razoáveis');}
      else if(pricing<40){adjustment-=.6;drivers.push('margens/estabilidade mais frágeis');}
    }
    if(balance!=null){
      evidence++;
      if(balance>=65){adjustment+=.7;drivers.push('balanço e cash flow resilientes');}
      else if(balance<40){adjustment-=.75;drivers.push('balanço/cash flow mais vulneráveis');}
    }
    if(stockRiskTags(stock).includes('Sensível a taxas')){adjustment-=.8;drivers.push('sensível a taxas');}
    const composite=structural+adjustment;
    const bucket=composite>=2.5?'benefit':composite>=.75?'resilient':composite>-.75?'neutral':'vulnerable';
    return {bucket,drivers,evidence,structural,composite};
  }
  function renderInflationShield(rows,portfolioTotal=0){
    const analysedTotal=rows.reduce((a,r)=>a+(n(r.value)||0),0)||1;
    const total=portfolioTotal>0?portfolioTotal:analysedTotal;
    const classified=rows.map(r=>({...r,inflation:inflationShieldProfile(r.stock)})).filter(r=>r.inflation&&r.value>0);
    const covered=classified.reduce((a,r)=>a+r.value,0), coverage=covered/total*100;
    const partial=portfolioTotal>0&&coverage<35;
    const groups={benefit:[],resilient:[],neutral:[],vulnerable:[]};
    classified.forEach(r=>groups[r.inflation.bucket].push(r));
    const weight=k=>groups[k].reduce((a,r)=>a+r.value,0)/(covered||1)*100;
    Object.values(groups).forEach(xs=>xs.sort((a,b)=>b.value-a.value));
    const protective=weight('benefit')+weight('resilient'), vulnerable=weight('vulnerable');
    const status=partial?'Dados parciais':vulnerable>=25?'Pressão elevada':protective>=65?'Proteção relevante':protective>=45?'Proteção mista':'Proteção limitada';
    const statusTone=partial?'is-warn':vulnerable>=25?'is-risk':protective>=65?'is-positive':'is-warn';
    const zones=Object.keys(INFLATION_BUCKETS).map(k=>{
      const meta=INFLATION_BUCKETS[k], pct=weight(k), names=groups[k].slice(0,4).map(r=>esc(r.stock.ticker)).join(' · ');
      return `<div class="market-inflation-zone market-inflation-zone--${meta.tone}"><span>${esc(meta.label)}</span><strong>${pct.toFixed(0)}%</strong><small>${names||'—'}</small></div>`;
    }).join('');
    const bar=Object.keys(INFLATION_BUCKETS).map(k=>`<i class="market-inflation-bar__${INFLATION_BUCKETS[k].tone}" style="width:${Math.max(0,weight(k)).toFixed(2)}%" title="${esc(INFLATION_BUCKETS[k].label)} ${weight(k).toFixed(1)}%"></i>`).join('');
    const sortedClassified=classified.slice().sort((a,b)=>b.value-a.value);
    const inflationRow=r=>{
      const meta=INFLATION_BUCKETS[r.inflation.bucket], portfolioWeight=r.value/total*100;
      return `<button type="button" class="market-inflation-row" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${esc(r.inflation.drivers.slice(0,2).join(' · '))}</small></span><em class="market-inflation-badge market-inflation-badge--${meta.tone}">${esc(meta.label)}</em><b>${portfolioWeight.toFixed(1)}%</b></button>`;
    };
    const visible=sortedClassified.slice(0,10), remaining=sortedClassified.slice(10);
    const list=visible.map(inflationRow).join('');
    const more=remaining.length?`<details class="market-detail-disclosure market-inflation-more"><summary>Ver mais ${remaining.length} posições classificadas</summary><div class="market-inflation-list">${remaining.map(inflationRow).join('')}</div></details>`:'';
    const classifiedCount=sortedClassified.length;
    return `<div class="market-detail-card market-inflation-shield"><div class="market-perspective-head"><div><small>INFLATION SHIELD · REGIME LENS</small><h4>Como reage a parte classificável à inflação?</h4></div><span class="market-inflation-status ${statusTone}">${esc(status)}</span></div><p class="market-case-note">Lente fundamental explicável para um regime de inflação persistente com taxas restritivas. Não altera Vestra Score, Discovery nem Portfolio Fit.</p><div class="market-inflation-coverage"><span>Cobertura ${coverage.toFixed(0)}%</span><small>${classifiedCount} posições classificadas · ${partial?'cobertura insuficiente para conclusão global':'distribuição da exposição classificada'}</small></div><div class="market-inflation-bar" aria-label="Distribuição Inflation Shield">${bar}</div><div class="market-inflation-zones">${zones}</div><p class="market-case-note market-inflation-selection-note"><strong>Porque aparecem estas posições?</strong> Não são uma shortlist de “melhores hedges”. São todas as posições da carteira para as quais existe evidência suficiente nesta lente, ordenadas pelo peso na carteira. As primeiras 10 ficam visíveis; as restantes estão em “Ver mais”.</p><div class="market-inflation-list">${list||'<p class="market-case-note">Sem posições classificáveis com os dados atuais.</p>'}</div>${more}<details class="market-detail-disclosure market-inflation-method"><summary>Como é feita a classificação?</summary><p class="market-case-note">Empresas: começa pelo viés do setor e ajusta por moat/profitabilidade/estabilidade, balanço/leverage/cash flow e sensibilidade a taxas. ETFs/fundos só entram quando o tema é explícito. O resultado é Beneficia, Resiliente, Neutro ou Vulnerável.</p></details><p class="market-case-note">${partial?'O estado global fica indisponível enquanto menos de 35% da carteira tiver classificação Inflation Shield. ':''}Proxy, não backtest. Não infere correlação histórica com CPI quando essa série não existe.</p></div>`;
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
    const good=inverse?d<0:d>0;
    const shown=inverse?Math.abs(d).toFixed(1):`${d>0?'+':''}${d.toFixed(1)}`;
    return `${good?'↑':'↓'} ${shown}${suffix}`;
  }
  function renderPortfolioHealthTimeline(history){
    if(!history?.length) return '';
    const latest=history[history.length-1], prev=history.length>1?history[history.length-2]:null;
    const rows=history.slice(-8);
    const comparableResearch=!!prev&&txt(latest.researchContext)&&txt(prev.researchContext)&&latest.researchContext===prev.researchContext;
    const comparableConviction=!!prev&&txt(latest.convictionContext)&&txt(prev.convictionContext)&&latest.convictionContext===prev.convictionContext;
    const comparableActions=!!prev&&txt(latest.actionContext)&&txt(prev.actionContext)&&latest.actionContext===prev.actionContext;
    const comparableTargets=!!prev&&txt(latest.targetContext)&&txt(prev.targetContext)&&latest.targetContext===prev.targetContext;
    const comparableTargetEvidence=!!prev&&txt(latest.targetEvidenceContext)&&txt(prev.targetEvidenceContext)&&latest.targetEvidenceContext===prev.targetEvidenceContext;
    const comparableRisk=!!prev&&txt(latest.riskContext)&&txt(prev.riskContext)&&latest.riskContext===prev.riskContext&&txt(latest.riskEvidenceContext)&&txt(prev.riskEvidenceContext)&&latest.riskEvidenceContext===prev.riskEvidenceContext;
    const fitDelta=prev?(!comparableResearch?'cobertura alterada':!comparableTargets?'targets alterados':comparableTargetEvidence?healthDeltaLabel(latest.targetFit,prev.targetFit,false,''):'classificação alterada'):'baseline';
    const riskDelta=prev?(!comparableResearch?'cobertura alterada':comparableRisk?healthDeltaLabel(latest.riskFit,prev.riskFit,false,''):latest.riskContext!==prev.riskContext?'limites alterados':'classificação alterada'):'baseline';
    const convictionDelta=prev?(comparableConviction?healthDeltaLabel(latest.conviction,prev.conviction,false,''):'convicção cobertura alterada'):'baseline';
    const topPositionDelta=prev?(comparableResearch?healthDeltaLabel(latest.topPosition,prev.topPosition,true,' pp'):'cobertura alterada'):'baseline';
    const riskPositionsDelta=prev?(!comparableResearch?'cobertura alterada':comparableActions?healthDeltaLabel(latest.riskPositions,prev.riskPositions,true):'sinais alterados'):'baseline';
    const trend=prev?`${fitDelta} fit · ${riskDelta} risk · ${convictionDelta} conv.`:'Primeiro snapshot criado';
    return `<div class="market-detail-card market-health-timeline"><div class="market-perspective-head"><div><small>PORTFOLIO HEALTH · HISTÓRICO</small><h4>Evolução da carteira</h4></div><span class="market-data-age">${history.length} ${history.length===1?'dia':'dias'}</span></div><div class="market-health-kpis"><div><small>Target Fit</small><strong>${latest.targetFit==null?'—':Math.round(latest.targetFit)}</strong><em>${fitDelta}</em></div><div><small>Risk Fit</small><strong>${latest.riskFit==null?'—':Math.round(latest.riskFit)}</strong><em>${riskDelta}</em></div><div><small>Convicção</small><strong>${latest.conviction==null?'—':latest.conviction.toFixed(1)}</strong><em>${convictionDelta} · ${latest.convictionCoverage==null?'—':Math.round(latest.convictionCoverage)+'% coberta'}</em></div><div><small>Maior posição</small><strong>${latest.topPosition.toFixed(1)}%</strong><em>${topPositionDelta}</em></div><div><small>Rever/Substituir</small><strong>${latest.riskPositions}</strong><em>${riskPositionsDelta}</em></div><div><small>Cobertura</small><strong>${latest.researchCoverage==null?'—':Math.round(latest.researchCoverage)+'%'}</strong><em>${prev?(comparableResearch?'mesmo universo':'universo alterado'):'baseline'}</em></div></div><div class="market-health-trend">${esc(trend)}</div><div class="market-health-history">${rows.map(x=>`<div class="market-health-row"><span>${esc(x.day.slice(5))}</span><div><i style="width:${x.targetFit==null?3:Math.max(3,Math.min(100,x.targetFit))}%"></i></div><strong>${x.targetFit==null?'—':Math.round(x.targetFit)}</strong><small>conv ${x.conviction==null?'—':x.conviction.toFixed(0)} · pos ${x.topPosition.toFixed(0)}% · setor ${x.topSector.toFixed(0)}% · overlap ${x.overlapCount} · risco ${x.riskPositions} · cobertura ${x.researchCoverage==null?'—':Math.round(x.researchCoverage)+'%'} · conv.cob. ${x.convictionCoverage==null?'—':Math.round(x.convictionCoverage)+'%'}</small></div>`).join('')}</div>${history.length<2?'<p class="market-case-note">A partir do próximo dia a Vestra começa a mostrar a direção das métricas. O snapshot do mesmo dia é atualizado, não duplicado.</p>':prev&&!comparableResearch?'<p class="market-case-note">O conjunto de posições analisáveis mudou desde o snapshot anterior; os deltas não são comparados diretamente entre universos de research diferentes.</p>':prev&&!comparableConviction?'<p class="market-case-note">O conjunto de posições com convicção calculável mudou; o delta de convicção não é comparado diretamente.</p>':prev&&(!comparableTargets||!comparableTargetEvidence||!comparableRisk)?`<p class="market-case-note">${!comparableTargets?'Os Portfolio Targets mudaram; o Target Fit não é comparado diretamente. ':!comparableTargetEvidence?'A classificação usada pelo Target Fit mudou; o Target Fit não é comparado diretamente. ':''}${!comparableRisk?(latest.riskContext!==prev.riskContext?'Os limites do Risk Budget mudaram; o Risk Fit não é comparado diretamente.':'A classificação de risco mudou; o Risk Fit não é comparado diretamente.'):''}</p>`:''}</div>`;
  }

  const RESEARCH_QUEUE_KEY='vestra_research_queue_v1';
  function loadResearchQueue(){
    try{ const x=JSON.parse(localStorage.getItem(RESEARCH_QUEUE_KEY)||'{}'); return x&&typeof x==='object'?x:{}; }
    catch{return {};}
  }
  function saveResearchQueue(x){ try{localStorage.setItem(RESEARCH_QUEUE_KEY,JSON.stringify(x||{}));}catch{} }
  function researchQueueState(ticker,signalKey=''){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(), x=all[key]||{};
    const storedSignal=txt(x.signalKey), currentSignal=txt(signalKey);
    if(['reviewed','snoozed'].includes(x.status)&&storedSignal&&currentSignal&&storedSignal!==currentSignal) return {...x,status:'new',snoozeUntil:0,signalChanged:true};
    if(x.status==='snoozed'&&Number(x.snoozeUntil||0)<=Date.now()) return {...x,status:'new',snoozeUntil:0};
    return {status:x.status||'new',snoozeUntil:Number(x.snoozeUntil||0),updatedAt:Number(x.updatedAt||0),checkpoint:txt(x.checkpoint),note:txt(x.note),checkpointAt:Number(x.checkpointAt||0),signalKey:storedSignal};
  }
  function setResearchQueueState(ticker,status,signalKey=''){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(); if(!key)return;
    const prev=all[key]||{}; all[key]={...prev,status,signalKey:txt(signalKey),updatedAt:Date.now(),snoozeUntil:status==='snoozed'?Date.now()+7*86400000:0};
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

  function portfolioReviewSignals(r){
    const gate=txt(r?.stock?.risk_gate);
    return {
      replace:r?.action?.key==='replace',
      gateRank:gate==='severe'?3:gate==='high'?2:gate==='watch'?1:0,
      conviction:r?.conviction??999,
      value:n(r?.value)||0,
    };
  }
  function researchReviewSignalKey(r){
    const x=portfolioReviewSignals(r);
    return [x.replace?'replace':'review',x.gateRank,x.conviction<50?1:0].join('|');
  }
  function comparePortfolioReview(a,b){
    const x=portfolioReviewSignals(a), y=portfolioReviewSignals(b);
    return Number(y.replace)-Number(x.replace)
      ||y.gateRank-x.gateRank
      ||x.conviction-y.conviction
      ||y.value-x.value;
  }

  function renderResearchQueue(review){
    const rank={new:0,in_review:1,snoozed:2,reviewed:3};
    const items=review.map(r=>{const signalKey=researchReviewSignalKey(r); return {r,signalKey,state:researchQueueState(r.stock.ticker,signalKey)}}).sort((a,b)=>(rank[a.state.status]??9)-(rank[b.state.status]??9)||comparePortfolioReview(a.r,b.r));
    const counts=items.reduce((a,x)=>{a[x.state.status]=(a[x.state.status]||0)+1;return a;},{});
    const activeItems=items.filter(x=>x.state.status!=='reviewed'&&x.state.status!=='snoozed');
    const visible=activeItems.slice(0,12);
    const label={new:'Novo',in_review:'Em revisão',reviewed:'Revisto',snoozed:'Adiado'};
    const tone={new:'is-risk',in_review:'is-warn',reviewed:'is-positive',snoozed:''};
    const rows=visible.length?visible.map(({r,state,signalKey})=>`<div class="market-research-queue-row" data-queue-ticker="${esc(r.stock.ticker)}" data-queue-signal="${esc(signalKey)}"><button type="button" class="market-research-queue-main" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${r.conviction==null?'convicção insuficiente':`convicção ${Math.round(r.conviction)}/100`} · ${esc(txt(r.stock.risk_gate)||'clear')}</small></span><em class="${tone[state.status]||''}">${label[state.status]||'Novo'}</em></button><div class="market-research-queue-actions"><button type="button" data-queue-status="in_review">Em revisão</button><button type="button" data-queue-status="reviewed">Revisto</button><button type="button" data-queue-status="snoozed">Adiar 7d</button></div>${state.status==='in_review'||state.checkpoint?researchCheckpointEditor(r.stock.ticker,state):''}</div>`).join(''):'<p class="market-case-note">Sem revisões ativas pendentes. Itens adiados regressam automaticamente após 7 dias.</p>';
    return `<div class="market-detail-card market-research-queue"><div class="market-perspective-head"><div><small>RESEARCH QUEUE · LOCAL</small><h4>Fila de revisão</h4></div><span class="market-data-age">${(counts.new||0)+(counts.in_review||0)} pendentes</span></div><div class="market-action-context"><span>${counts.new||0} novos</span><span>${counts.in_review||0} em revisão</span><span>${counts.snoozed||0} adiados</span><span>${counts.reviewed||0} revistos</span></div><p class="market-case-note">Memória operacional: organiza o research sem alterar Score Vestra, Action Map ou carteira.</p><div class="market-research-queue-list">${rows}</div>${activeItems.length>12?`<p class="market-case-note">A mostrar as 12 prioridades ativas mais urgentes de ${activeItems.length} pendentes.</p>`:''}</div>`;
  }

  function renderPortfolioDecisionCenter(rows,total,etfOptimizeRows=[]){
    const analysedValue=rows.reduce((a,r)=>a+(n(r.value)||0),0);
    const analysed=analysedValue||1;
    const portfolioBase=total>0?total:analysed;
    const coverage=total>0?analysedValue/total*100:0;
    const partialCoverage=total>0&&coverage<35;
    const ranked=rows.map(r=>({...r,conviction:portfolioConviction(r.stock)}));
    const convRows=ranked.filter(r=>r.conviction!=null&&r.value>0);
    const convWeight=convRows.reduce((a,r)=>a+r.value,0);
    const convictionCoverage=portfolioBase>0?convWeight/portfolioBase*100:0;
    const partialConviction=convictionCoverage<35;
    const conviction=convWeight>0?convRows.reduce((a,r)=>a+r.value*r.conviction,0)/convWeight:null;
    const targets=loadPortfolioTargets();
    const riskBudget=renderRiskBudget(ranked,total);
    const stresses=Object.keys(PORTFOLIO_STRESS_SCENARIOS).map(k=>portfolioStress(ranked,k)).sort((a,b)=>a.resilience-b.resilience);
    const worst=stresses[0];
    const sectors=new Map(); ranked.forEach(r=>{const k=txt(r.stock.sector); if(k) sectors.set(k,(sectors.get(k)||0)+r.value)});
    const topSector=[...sectors.entries()].map(([name,value])=>({name,pct:value/portfolioBase*100})).sort((a,b)=>b.pct-a.pct)[0];
    const topPosition=ranked.slice().sort((a,b)=>b.value-a.value)[0];
    const topPositionPct=topPosition?topPosition.value/portfolioBase*100:0;
    const review=ranked.filter(r=>['review','replace'].includes(r.action?.key)).sort(comparePortfolioReview);
    const activeReview=review.filter(r=>!['reviewed','snoozed'].includes(researchQueueState(r.stock.ticker,researchReviewSignalKey(r)).status));
    const reinforce=ranked.filter(r=>r.action?.key==='reinforce').sort((a,b)=>b.conviction-a.conviction);
    const positionAlert=topPositionPct>targets.maxPosition;
    const sectorAlert=(topSector?.pct||0)>targets.maxSector;
    const riskBudgetAlert=riskBudget.hasBreaches;
    const stressAlert=!partialCoverage&&(worst?.resilience??100)<75;
    const structuralAlert=positionAlert||sectorAlert||riskBudgetAlert||stressAlert;
    const incompleteEvidence=partialCoverage||partialConviction||riskBudget.incomplete;
    const decisionState=activeReview.length?'Rever':structuralAlert?'Atenção':review.length?'Acompanhar':incompleteEvidence?'Dados parciais':'Estável';
    const tone=activeReview.length?'is-risk':structuralAlert||review.length||incompleteEvidence?'is-warn':'is-positive';
    const materialEtfOptimize=(etfOptimizeRows||[]).find(x=>x.improvements>=2||x.scoreDelta>=5||(x.terSaving!=null&&x.terSaving>=.10)||(x.dupDelta!=null&&x.dupDelta<=-10))||null;
    const priorities=[];
    if(activeReview[0]) priorities.push({label:`${activeReview[0].action?.key==='replace'?'Substituir':'Rever'} ${activeReview[0].stock.ticker}: ${activeReview[0].conviction==null?'convicção insuficiente':`convicção ${Math.round(activeReview[0].conviction)}/100`}`,kind:'ticker',value:activeReview[0].stock.ticker});
    if(positionAlert&&topPosition) priorities.push({label:`${topPosition.stock.ticker} está acima do objetivo por posição (${topPositionPct.toFixed(1)}%)`,kind:'ticker',value:topPosition.stock.ticker});
    if(sectorAlert&&topSector) priorities.push({label:`${topSector.name} está acima do objetivo setorial (${topSector.pct.toFixed(1)}%)`,kind:'targets',value:'targets'});
    if(riskBudgetAlert) priorities.push({label:`Risk Budget: ${riskBudget.breaches.length} ${riskBudget.breaches.length===1?'limite excedido':'limites excedidos'}`,kind:'riskbudget',value:'riskbudget'});
    if(stressAlert&&worst) priorities.push({label:`Stress mais exigente: ${PORTFOLIO_STRESS_SCENARIOS[worst.key].label} · resiliência ${worst.resilience}/100`,kind:'stress',value:worst.key});
    if(materialEtfOptimize) priorities.push({label:`Comparar ${materialEtfOptimize.source.ticker} → ${materialEtfOptimize.candidate.ticker}: ETF Optimize encontrou ${materialEtfOptimize.improvements} melhoria${materialEtfOptimize.improvements===1?'':'s'} material${materialEtfOptimize.improvements===1?'':'is'}`,kind:'etfoptimize',value:materialEtfOptimize.source.ticker});
    if(riskBudget.incomplete) priorities.push({label:'Risk Budget incompleto: faltam classificações de exposição',kind:'riskbudget',value:'riskbudget'});
    if(partialCoverage) priorities.push({label:`Cobertura de research insuficiente: ${coverage.toFixed(0)}% da carteira analisada`,kind:'health',value:'health'});
    if(partialConviction&&!partialCoverage) priorities.push({label:`Cobertura de convicção insuficiente: ${convictionCoverage.toFixed(0)}% da carteira`,kind:'health',value:'health'});
    if(!priorities.length&&reinforce[0]) priorities.push({label:`Carteira sem alerta dominante; ${reinforce[0].stock.ticker} é o reforço com maior convicção atual`,kind:'ticker',value:reinforce[0].stock.ticker});
    const next=activeReview[0]?{label:activeReview[0].action?.key==='replace'?`Abrir ${activeReview[0].stock.ticker} e avaliar substituição`:`Abrir ${activeReview[0].stock.ticker} e rever a tese`,kind:'ticker',value:activeReview[0].stock.ticker}
      :positionAlert?{label:'Usar o Rebalancer para reduzir concentração por posição',kind:'rebalancer',value:'rebalancer'}
      :sectorAlert&&topSector?{label:`Rever concentração no setor ${topSector.name}`,kind:'targets',value:'targets'}
      :riskBudgetAlert?{label:'Rever os limites excedidos no Risk Budget antes de reforçar posições',kind:'riskbudget',value:'riskbudget'}
      :stressAlert&&worst?{label:`Rever o stress ${PORTFOLIO_STRESS_SCENARIOS[worst.key].label}`,kind:'stress',value:worst.key}
      :review.length?{label:'Acompanhar posições já revistas antes de novo reforço',kind:'actionmap',value:'attention'}
      :riskBudget.incomplete?{label:'Completar classificações do Risk Budget antes de tirar conclusões de diversificação',kind:'riskbudget',value:'riskbudget'}
      :materialEtfOptimize?{label:`Comparar ${materialEtfOptimize.source.ticker} com ${materialEtfOptimize.candidate.ticker} no ETF Optimize`,kind:'etfoptimize',value:materialEtfOptimize.source.ticker}
      :partialCoverage?{label:'Completar research antes de tirar conclusões sobre a carteira',kind:'health',value:'health'}
      :partialConviction?{label:'Completar evidência de convicção antes de tirar conclusões globais',kind:'health',value:'health'}
      :reinforce[0]?{label:`Avaliar reforço em ${reinforce[0].stock.ticker}`,kind:'ticker',value:reinforce[0].stock.ticker}
      :{label:'Manter e acompanhar',kind:'health',value:'health'};
    const jumpAttrs=x=>`data-decision-jump="${esc(x.kind)}" data-decision-value="${esc(x.value||'')}"`;
    return `<div class="market-detail-card market-decision-center" data-vpu-conviction="${conviction==null?'':conviction.toFixed(1)}" data-vpu-conviction-coverage="${convictionCoverage.toFixed(0)}" data-vpu-risk="${riskBudget.fit==null?'':riskBudget.fit}" data-vpu-review="${review.length}" data-vpu-state="${esc(decisionState)}" data-vpu-coverage="${coverage.toFixed(0)}"><div class="market-perspective-head"><div><small>PORTFOLIO DECISION CENTER</small><h4>O que merece atenção agora?</h4></div><span class="market-target-fit-score ${tone}">${esc(decisionState)}</span></div><div class="market-decision-kpis"><button type="button" ${jumpAttrs({kind:'actionmap',value:'all'})}><small>Convicção · ${convictionCoverage.toFixed(0)}% coberta</small><strong>${conviction==null?'—':partialConviction?conviction.toFixed(1)+' · parcial':conviction.toFixed(1)}</strong></button><button type="button" ${jumpAttrs({kind:'riskbudget',value:'riskbudget'})}><small>Risk Fit</small><strong>${riskBudget.fit==null?'—':partialCoverage?riskBudget.fit+' · parcial':riskBudget.fit}</strong></button><button type="button" ${jumpAttrs({kind:'stress',value:worst?.key||'rates'})}><small>Pior stress</small><strong>${worst?(partialCoverage?worst.resilience+' · parcial':worst.resilience):'—'}</strong></button><button type="button" ${jumpAttrs({kind:'actionmap',value:'attention'})}><small>Rever/Substituir</small><strong>${review.length}</strong></button></div><button type="button" class="market-decision-next" ${jumpAttrs(next)}><small>PRÓXIMA AÇÃO DE RESEARCH</small><strong>${esc(next.label)}</strong><span>→</span></button><div class="market-decision-priorities">${priorities.slice(0,4).map(x=>`<button type="button" ${jumpAttrs(x)}><span>${esc(x.label)}</span><b>→</b></button>`).join('')}</div><p class="market-case-note">Síntese executiva: prioriza sinais independentes sem os fundir num novo score de investimento.</p></div>${renderResearchQueue(review)}`;
  }

  function portfolioIntelligence(rows,total){
    if(!rows.length) return '';
    const analysed=rows.reduce((a,r)=>a+r.value,0)||1;
    const portfolioBase=total>0?total:analysed;
    const ranked=rows.map(r=>({...r,conviction:portfolioConviction(r.stock)}));
    const heldTickers=new Set(ranked.map(r=>txt(r.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')));

    const sectors=new Map();
    for(const r of ranked){ const k=txt(r.stock.sector); if(k) sectors.set(k,(sectors.get(k)||0)+r.value); }
    const sectorRows=[...sectors.entries()].map(([sector,value])=>({sector,value,pct:value/portfolioBase*100})).sort((a,b)=>b.value-a.value);
    const topPosition=ranked.slice().sort((a,b)=>b.value-a.value)[0];
    const topPosPct=topPosition?topPosition.value/portfolioBase*100:0;

    const etfsForFit=ranked.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/portfolioBase*100}));
    const portfolioTargets=loadPortfolioTargets();
    for(const r of ranked) r.portfolioFit=portfolioFit(r,sectorRows,portfolioBase,etfsForFit,portfolioTargets);

    const etfOptimizeRows=findEtfOptimizeAlternatives(ranked,heldTickers);
    const etfOptimizeHtml=renderEtfOptimizeCard(etfOptimizeRows);

        const weak=ranked.slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999)).slice(0,7);
    const alternatives=[];
    for(const r of weak){
      const curScore=n(r.stock.score), curConv=r.conviction; if(isFund(r.stock)||!txt(r.stock.sector)||curScore==null||curConv==null||r.value<=0) continue;
      const currentIndirect=r.portfolioFit?.indirectPct||0, sourceSectorPct=(sectorRows.find(x=>x.sector===txt(r.stock.sector))?.pct)||0;
      const candidates=M.stocks.filter(x=>!isFund(x)&&!heldTickers.has(txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,''))&&txt(x.sector)===txt(r.stock.sector)&&n(x.score)!=null);
      const cand=candidates.map(x=>{
        const indirect=indirectExposurePct(x,etfsForFit), conv=portfolioConviction(x); if(conv==null) return null;
        const scoreDelta=n(x.score)-curScore;
        const decision=evaluatePortfolioMove({mode:'alternative',sourceStock:r.stock,destination:x,rows:ranked,amount:r.value,totalAfter:portfolioBase,sourceConv:curConv,destinationConv:conv,positionPct:r.value/portfolioBase*100,sectorPct:sourceSectorPct,indirect,sourceIndirect:currentIndirect});
        if(!decision.autoEligible) return null;
        const sameIndustry=!!txt(x.industry)&&txt(x.industry)===txt(r.stock.industry);
        return {stock:x,indirect,conv,scoreDelta,convDelta:decision.convictionGain,sameIndustry,decision};
      }).filter(Boolean).sort((a,b)=>
        b.convDelta-a.convDelta
        ||a.decision.overlapDelta-b.decision.overlapDelta
        ||a.decision.riskPenalty-b.decision.riskPenalty
        ||Number(b.sameIndustry)-Number(a.sameIndustry)
      )[0];
      if(cand){
        const fit=cand.indirect+1<currentIndirect?'better':cand.indirect>currentIndirect+1?'worse':'neutral';
        alternatives.push({from:r.stock,to:cand.stock,delta:cand.scoreDelta,convDelta:cand.convDelta,portfolioFit:fit,currentIndirect,candidateIndirect:cand.indirect,decision:cand.decision});
      }
      if(alternatives.length>=3) break;
    }
    const alternativesByTicker=new Map(alternatives.map(a=>[txt(a.from.ticker).toUpperCase(),a]));
    const actionRows=ranked.map(r=>({...r,action:portfolioAction(r.stock,alternativesByTicker,r.portfolioFit)}));
    const actionOrder={replace:0,review:1,reinforce:2,hold:3};
    actionRows.sort((a,b)=>(actionOrder[a.action.key]??9)-(actionOrder[b.action.key]??9)||(b.value-a.value));
    const actionCounts=actionRows.reduce((acc,r)=>{acc[r.action.key]=(acc[r.action.key]||0)+1;return acc;},{});

    const reinforce=actionRows.filter(r=>r.action?.key==='reinforce').sort((a,b)=>b.conviction-a.conviction).slice(0,3);
    const review=actionRows.filter(r=>['review','replace'].includes(r.action?.key)).sort(comparePortfolioReview).slice(0,3);

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
    const concentrationMaxPos=Math.max(3,Math.min(30,n(portfolioTargets.maxPosition)||10));
    const concentrationMaxSector=Math.max(10,Math.min(60,n(portfolioTargets.maxSector)||25));
    if(topPosition&&topPosPct>concentrationMaxPos) concentration.push(`${topPosition.stock.ticker} representa ~${topPosPct.toFixed(0)}% · objetivo ${concentrationMaxPos}%`);
    if(sectorRows[0]?.pct>concentrationMaxSector) concentration.push(`${sectorRows[0].sector} concentra ~${sectorRows[0].pct.toFixed(0)}% · objetivo ${concentrationMaxSector}%`);
    concentration.push(...overlaps.slice(0,3));

    const compactRows=(arr,metaFn)=>arr.length?`<div class="market-list">${arr.map(r=>renderRow(r.stock,metaFn(r))).join('')}</div>`:'<p class="market-case-note">Nenhuma posição cumpre este filtro com os dados atuais.</p>';
    const altHtml=alternatives.length?`<div class="market-list">${alternatives.map(a=>renderRow(a.to,`Alternativa a ${a.from.ticker} · Convicção +${a.convDelta.toFixed(0)} · Score +${a.delta.toFixed(0)} · ${a.portfolioFit==='better'?'reduz overlap':a.portfolioFit==='worse'?'aumenta overlap':'impacto neutro'}`)).join('')}</div>`:'<p class="market-case-note">Sem alternativa claramente superior identificada no mesmo setor.</p>';
    const concHtml=concentration.length?`<ul class="market-case-list">${[...new Set(concentration)].slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="market-case-note">Sem concentração material detetada com os dados disponíveis.</p>';

    const convRows=ranked.filter(r=>r.conviction!=null&&r.value>0);
    const convictionWeight=convRows.reduce((sum,r)=>sum+r.value,0);
    const convictionCoverage=portfolioBase>0?convictionWeight/portfolioBase*100:100;
    const scenarioPartial=convictionCoverage<35;
    const portfolioConvictionNow=convictionWeight>0?convRows.reduce((sum,r)=>sum+r.value*r.conviction,0)/convictionWeight:null;
    const scenarioRows=alternatives.map(a=>{
      const fromRow=ranked.find(r=>txt(r.stock.ticker).toUpperCase()===txt(a.from.ticker).toUpperCase());
      if(!fromRow) return null;
      const oldConv=portfolioConviction(a.from), newConv=portfolioConviction(a.to);
      if(oldConv==null||newConv==null||portfolioConvictionNow==null||convictionWeight<=0) return null;
      const w=fromRow.value/convictionWeight;
      const after=portfolioConvictionNow+(newConv-oldConv)*w;
      const overlapBefore=n(a.currentIndirect)||0, overlapAfter=n(a.candidateIndirect)||0;
      const positionPct=fromRow.value/portfolioBase*100, sectorPct=(sectorRows.find(x=>x.sector===txt(a.from.sector))?.pct)||0;
      const decision=evaluatePortfolioMove({mode:'scenario',sourceStock:a.from,destination:a.to,rows:ranked,amount:fromRow.value,totalAfter:portfolioBase,sourceConv:oldConv,destinationConv:newConv,positionPct,sectorPct,indirect:overlapAfter,sourceIndirect:overlapBefore});
      const {convDelta,overlapDelta,riskPenalty,autoEligible,warnings}=decision;
      let impact='Neutro';
      if(convDelta<=0||overlapDelta>=2||riskPenalty>=5) impact='Piora';
      else if(convDelta>=.5||overlapDelta<=-1) impact='Melhora';
      const eligibility=autoEligible?'Elegível':decision.evidence.strict?'Manual':'Evidência limitada';
      return {from:a.from,to:a.to,before:portfolioConvictionNow,after,convDelta,overlapBefore,overlapAfter,overlapDelta,riskPenalty,impact,eligibility,warnings,autoEligible};
    }).filter(Boolean).slice(0,3);
    const scenarioHtml=scenarioRows.length?`<div class="market-detail-card market-scenario-preview"><div class="market-perspective-head"><div><small>SCENARIO PREVIEW</small><h4>Se substituíres pelo mesmo valor</h4></div><span class="market-data-age">${convictionCoverage.toFixed(0)}% convicção coberta</span></div><p class="market-case-note">Mantém o valor da posição e o setor; mostra impacto e elegibilidade separadamente. A convicção apresentada refere-se apenas às posições com convicção calculável.${scenarioPartial?' Cobertura insuficiente para interpretar esta média como convicção global da carteira.':''} Evidência limitada não é tratada como deterioração da carteira.</p><div class="market-scenario-list">${scenarioRows.map(x=>`<div class="market-scenario-row"><div><strong>${esc(x.from.ticker)} → ${esc(x.to.ticker)}</strong><small>Convicção analisável ${x.before.toFixed(1)} → ${x.after.toFixed(1)} · overlap ${x.overlapBefore.toFixed(1)}% → ${x.overlapAfter.toFixed(1)}% · risco ${x.riskPenalty.toFixed(1)} · ${esc(x.eligibility)}${x.warnings?.length?' · ⚠ '+esc(x.warnings.join(' · ')):''}</small></div><em class="${x.impact==='Melhora'?'is-positive':x.impact==='Piora'?'is-risk':''}">${x.impact}</em></div>`).join('')}</div><p class="market-case-note">Cenário indicativo: não considera fiscalidade, spreads, comissões ou liquidez. Um cenário não elegível pode continuar visível para comparação manual.</p></div>`:'';

    const rebalSourceRows=actionRows.filter(r=>r.value>0&&r.conviction!=null).slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999));
    const defaultSource=rebalSourceRows[0]||null;
    const rebalancerHtml=defaultSource?`<div class="market-detail-card market-rebalancer" data-rebalancer-card><div class="market-perspective-head"><div><small>ASSISTED REBALANCER</small><h4>Onde melhora mais este capital?</h4></div><span class="market-data-age">simulação</span></div><p class="market-case-note">Escolhe a posição de origem e o montante. A Vestra mantém o valor total da carteira e compara destinos elegíveis por convicção, concentração, overlap e Risk Budget.</p><div class="market-rebalancer-controls"><label><span>Libertar de</span><select data-rebalance-source>${rebalSourceRows.map(r=>`<option value="${esc(r.stock.ticker)}">${esc(r.stock.ticker)} · ${euro(r.value)} · conv. ${Math.round(r.conviction)}</option>`).join('')}</select></label><label><span>Montante</span><input data-rebalance-amount type="number" min="1" max="${Math.max(1,Math.floor(defaultSource.value))}" step="1" value="${Math.max(1,Math.min(1000,Math.round(defaultSource.value)||1))}"></label><button type="button" data-rebalance-run>Simular</button></div><div class="market-rebalancer-results" data-rebalance-results><p class="market-case-note">Toca em Simular para comparar os melhores destinos.</p></div><p class="market-case-note">Research assistido; não considera fiscalidade, custos de transação, liquidez pessoal ou ordens reais.</p></div>`:'';
    const targets=loadPortfolioTargets();
    const targetPositionBreaches=ranked.map(r=>({ticker:r.stock.ticker,pct:r.value/portfolioBase*100})).filter(x=>x.pct>targets.maxPosition).sort((a,b)=>b.pct-a.pct);
    const targetSectorBreaches=sectorRows.filter(x=>x.pct>targets.maxSector);
    const targetOverlapBreaches=targets.overlap==='reduce'?ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2):[];
    const posExcess=targetPositionBreaches.reduce((a,x)=>a+(x.pct-targets.maxPosition),0);
    const sectorExcess=targetSectorBreaches.reduce((a,x)=>a+(x.pct-targets.maxSector),0);
    const overlapExcess=targetOverlapBreaches.reduce((a,r)=>a+Math.max(0,(r.portfolioFit?.indirectPct||0)-2),0);
    const researchCoverage=total>0?analysed/total*100:100;
    const targetIncomplete=total>0&&researchCoverage<35;
    const rawTargetFit=Math.max(0,Math.min(100,Math.round(100-posExcess*1.5-sectorExcess*1.15-overlapExcess*2.5)));
    const targetFit=targetIncomplete?null:rawTargetFit;
    const targetTone=targetIncomplete?'is-warn':targetFit>=85?'is-positive':targetFit>=65?'is-warn':'is-risk';
    const targetIssues=[];
    targetPositionBreaches.slice(0,3).forEach(x=>targetIssues.push(`${x.ticker} ${x.pct.toFixed(1)}% > objetivo ${targets.maxPosition}%`));
    targetSectorBreaches.slice(0,2).forEach(x=>targetIssues.push(`${x.sector} ${x.pct.toFixed(1)}% > objetivo ${targets.maxSector}%`));
    if(targetOverlapBreaches.length) targetIssues.push(`${targetOverlapBreaches.length} posições com overlap indireto ≥2%`);
    const targetFitHtml=`<div class="market-detail-card market-target-fit"><div class="market-perspective-head"><div><small>PORTFOLIO FIT</small><h4>Aderência desta carteira aos objetivos</h4></div><span class="market-target-fit-score ${targetTone}">${targetFit==null?'—':targetFit+'/100'}</span></div><div class="market-action-context"><span>${targetPositionBreaches.length} posições acima</span><span>${targetSectorBreaches.length} setores acima</span><span>${targetOverlapBreaches.length} overlap</span></div>${targetIncomplete?`<p class="market-case-note"><strong>Dados parciais.</strong> Só ${researchCoverage.toFixed(0)}% da carteira tem research; os excessos observados usam o valor total da carteira como denominador e continuam visíveis, mas o Target Fit global fica indisponível.</p>`:targetIssues.length?`<ul class="market-case-list">${targetIssues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="market-case-note">A parte analisável da carteira está dentro dos objetivos definidos.</p>'}</div>`;
    const riskBudget=renderRiskBudget(ranked,total);
    const riskBudgetHtml=riskBudget.html;
    const stressTestHtml=renderPortfolioStressTest(ranked,total);
    const inflationShieldHtml=renderInflationShield(ranked,total);
    const targetContext=[targets.maxPosition,targets.maxSector,targets.overlap].join('|');
    const targetEvidenceContext=ranked.map(r=>[txt(r.stock.ticker).toUpperCase(),txt(r.stock.sector),Number(n(r.portfolioFit?.indirectPct)||0).toFixed(4)].join(':')).filter(Boolean).sort().join('|');
    const riskContext=[targets.maxFactor,targets.maxCurrency,targets.maxRegion].join('|');
    const riskEvidenceContext=ranked.map(r=>[txt(r.stock.ticker).toUpperCase(),stockRiskTags(r.stock).slice().sort().join(','),stockCurrency(r.stock),stockRegion(r.stock)].join(':')).filter(Boolean).sort().join('|');
    const researchContext=ranked.map(r=>txt(r.stock.ticker).toUpperCase()).filter(Boolean).sort().join('|');
    const convictionContext=convRows.map(r=>txt(r.stock.ticker).toUpperCase()).filter(Boolean).sort().join('|');
    const actionContext=actionRows.map(r=>[txt(r.stock.ticker).toUpperCase(),txt(r.action?.key),txt(r.action?.reason)].join(':')).filter(Boolean).sort().join('|');
    const healthSnapshot={targetFit,targetContext,targetEvidenceContext,riskContext,riskEvidenceContext,researchContext,researchCoverage,convictionContext,convictionCoverage,actionContext,conviction:portfolioConvictionNow,topPosition:topPosPct,topSector:sectorRows[0]?.pct||0,overlapCount:ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length,riskPositions:(actionCounts.review||0)+(actionCounts.replace||0),riskFit:riskBudget.fit};
    const healthHistory=savePortfolioHealthSnapshot(healthSnapshot);
    const healthTimelineHtml=renderPortfolioHealthTimeline(healthHistory);
    const targetHtml=`<div class="market-detail-card market-target-engine" data-target-engine><div class="market-perspective-head"><div><small>PORTFOLIO TARGETS</small><h4>Objetivos da carteira</h4></div><span class="market-data-age">guardado localmente</span></div><p class="market-case-note">Estes objetivos passam a orientar o Rebalancer e o plano multi-movimento. Não alteram a carteira por si só.</p><div class="market-target-grid"><label><span>Máx. por posição</span><div><input data-target-position type="number" min="3" max="30" step="1" value="${targets.maxPosition}"><em>%</em></div></label><label><span>Máx. por setor</span><div><input data-target-sector type="number" min="10" max="60" step="1" value="${targets.maxSector}"><em>%</em></div></label><label><span>Máx. fator</span><div><input data-target-factor type="number" min="20" max="80" step="5" value="${targets.maxFactor}"><em>%</em></div></label><label><span>Máx. moeda</span><div><input data-target-currency type="number" min="30" max="100" step="5" value="${targets.maxCurrency}"><em>%</em></div></label><label><span>Máx. região</span><div><input data-target-region type="number" min="30" max="100" step="5" value="${targets.maxRegion}"><em>%</em></div></label><label><span>Overlap ETF</span><select data-target-overlap><option value="reduce" ${targets.overlap==='reduce'?'selected':''}>Reduzir</option><option value="neutral" ${targets.overlap==='neutral'?'selected':''}>Neutro</option></select></label><label><span>Prioridade</span><select data-target-tilt><option value="balanced" ${targets.tilt==='balanced'?'selected':''}>Equilibrado</option><option value="quality" ${targets.tilt==='quality'?'selected':''}>Quality</option><option value="growth" ${targets.tilt==='growth'?'selected':''}>Growth</option><option value="dividend" ${targets.tilt==='dividend'?'selected':''}>Dividendos</option></select></label></div><button type="button" class="market-plan-run" data-target-save>Guardar objetivos</button><span class="market-target-status" data-target-status></span></div>`;
    const freshCapitalHtml=`<div class="market-detail-card market-fresh-capital" data-fresh-capital-card><div class="market-perspective-head"><div><small>FRESH CAPITAL PLANNER</small><h4>Entrou capital novo. Onde reforçar?</h4></div><span class="market-data-age">sem vendas</span></div><p class="market-case-note">Distribui novo capital por até 3 destinos elegíveis, respeitando os Portfolio Targets e sem vender posições existentes.</p><div class="market-fresh-controls"><label><span>Novo capital</span><div><input data-fresh-amount type="number" min="50" step="50" value="1000"><em>€</em></div></label><button type="button" data-fresh-run>Distribuir</button></div><div data-fresh-results><p class="market-case-note">A simulação privilegia convicção, espaço dentro dos limites, overlap e a prioridade da carteira.</p></div></div>`;
    const planHtml=`<div class="market-detail-card market-rebalance-plan" data-rebalance-plan-card><div class="market-perspective-head"><div><small>MULTI-MOVE PLAN · TARGET AWARE</small><h4>Plano de rebalanceamento</h4></div><span class="market-data-age">até 3 movimentos</span></div><p class="market-case-note">Gera um plano a partir das posições mais frágeis e respeita os objetivos guardados acima.</p><button type="button" class="market-plan-run" data-rebalance-plan>Gerar plano</button><div data-rebalance-plan-results><p class="market-case-note">Nenhuma alteração é aplicada à carteira.</p></div></div>`;
    const concentratedCount=ranked.filter(r=>r.portfolioFit?.fit==='concentrated').length;
    const overlapCount=ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length;
    const actionMapHtml=`<div class="market-detail-card market-action-map"><div class="market-perspective-head"><div><small>ACTION MAP · PORTFOLIO FIT</small><h4>Mapa da carteira</h4></div><span class="market-data-age">${actionRows.length} posições</span></div><div class="market-action-context"><span>${concentratedCount} concentração</span><span>${overlapCount} overlap indireto</span><span>${sectorRows[0]?`${esc(sectorRows[0].sector)} ${sectorRows[0].pct.toFixed(0)}%`:'setor —'}</span></div><div class="market-action-summary"><button type="button" class="is-positive" data-action-filter="reinforce">Reforçar ${actionCounts.reinforce||0}</button><button type="button" data-action-filter="hold">Manter ${actionCounts.hold||0}</button><button type="button" class="is-warn" data-action-filter="review">Rever ${actionCounts.review||0}</button><button type="button" class="is-risk" data-action-filter="replace">Substituir ${actionCounts.replace||0}</button></div><div class="market-action-filter-status" data-action-filter-status>Mostrar todas as posições</div><div class="market-action-list">${actionRows.slice(0,12).map(r=>`<button type="button" class="market-action-row" data-action-key="${esc(r.action.key)}" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${esc(r.action.reason)} · ${esc(portfolioFitSummary(r.portfolioFit))}</small></span><em class="market-action-badge market-action-badge--${r.action.tone}">${esc(r.action.label)}</em></button>`).join('')}</div>${actionRows.length>12?`<details class="market-detail-disclosure"><summary>Ver mais ${actionRows.length-12} posições</summary><div class="market-action-list">${actionRows.slice(12).map(r=>`<button type="button" class="market-action-row" data-action-key="${esc(r.action.key)}" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${esc(r.action.reason)} · ${esc(portfolioFitSummary(r.portfolioFit))}</small></span><em class="market-action-badge market-action-badge--${r.action.tone}">${esc(r.action.label)}</em></button>`).join('')}</div></details>`:''}<p class="market-case-note">Classificação de research baseada em dados atuais; não é uma ordem automática de compra ou venda.</p></div>`;

    return `${renderPortfolioDecisionCenter(actionRows,total,etfOptimizeRows)}
      <div class="market-detail-card"><div class="market-perspective-head"><div><small>PORTFOLIO INTELLIGENCE</small><h4>Prioridades da carteira</h4></div><span class="market-data-age">${Math.round(analysed/(total||analysed)*100)}% coberto</span></div><p>Convicção sintetiza Score Vestra, valuation, expectativas e direção da tese. Confiança mede separadamente a qualidade da evidência; Risk Gate é um travão independente. É uma priorização de research — não uma ordem de compra ou venda.</p></div>
      ${actionMapHtml}
      <div class="market-detail-card"><h4>Candidatos a reforço</h4>${compactRows(reinforce,r=>`Convicção ${Math.round(r.conviction)}/100 · ${txt(r.stock.valuation_signal)||'valuation sem sinal'}`)}</div>
      <div class="market-detail-card"><h4>Posições a rever</h4>${compactRows(review,r=>`Convicção ${r.conviction==null?'—':Math.round(r.conviction)}/100 · ${txt(r.stock.risk_gate)||'Risk Gate não classificado'} · ${txt(r.stock.estimate_signal)||'expectativas —'}`)}</div>
      <div class="market-detail-card"><h4>Concentração e overlap</h4>${concHtml}</div>
      <div class="market-detail-card"><h4>Alternativas no mesmo setor</h4><p class="market-case-note">Só aparecem quando há uma empresa não detida do mesmo setor com convicção ≥5 pontos superior, Score ≥3 pontos superior e passa a avaliação canónica de evidência, Risk Budget e overlap.</p>${altHtml}</div>
      ${etfOptimizeHtml}
      ${scenarioHtml}
      ${targetFitHtml}
      ${healthTimelineHtml}
      ${riskBudgetHtml}
      ${stressTestHtml}
      ${inflationShieldHtml}
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
    const totalValue=researchUniverseValue(assets)||rows.reduce((a,r)=>a+r.value,0)||1, targets=loadPortfolioTargets();
    const maxPosition=Math.max(3,Math.min(30,n(targets.maxPosition)||10)), maxSector=Math.max(10,Math.min(60,n(targets.maxSector)||25));
    const sectors=new Map(); for(const r of rows){const k=txt(r.stock.sector);if(k)sectors.set(k,(sectors.get(k)||0)+r.value);}
    const sourceSignals=r=>{
      const gate=txt(r.stock.risk_gate), positionPct=r.value/totalValue*100, sectorKey=txt(r.stock.sector), sectorPct=sectorKey?(sectors.get(sectorKey)||0)/totalValue*100:0;
      const gateRank=gate==='severe'?3:gate==='high'?2:gate==='watch'?1:0;
      const positionExcess=Math.max(0,positionPct-maxPosition);
      const sectorExcess=Math.max(0,sectorPct-maxSector);
      const lowConviction=r.conviction<55;
      // Source pressure is portfolio context + independent Risk Gate + canonical
      // Conviction. Thesis/estimate signals must not be re-applied here.
      const pressured=gateRank>0||positionExcess>0||sectorExcess>0||lowConviction;
      return {gateRank,positionExcess,sectorExcess,lowConviction,pressured};
    };
    const planSources=rows.filter(r=>!isFund(r.stock)&&n(r.stock.score)!=null&&n(r.stock.confidence_score)!=null);
    const sources=planSources.map(r=>({...r,sourceSignals:sourceSignals(r)})).filter(r=>r.sourceSignals.pressured).sort((a,b)=>
      b.sourceSignals.gateRank-a.sourceSignals.gateRank
      ||b.sourceSignals.positionExcess-a.sourceSignals.positionExcess
      ||b.sourceSignals.sectorExcess-a.sourceSignals.sectorExcess
      ||a.conviction-b.conviction
      ||b.value-a.value
    );
    const queue=sources.slice(0,6);
    const baselineRisk=portfolioRiskProfile(rows,totalValue);
    const riskPct=(group,name)=>baselineRisk[group].find(x=>x.name===name)?.pct||0;
    const riskDelta={factors:new Map(),currencies:new Map(),regions:new Map()};
    const addRiskDelta=(group,name,delta)=>riskDelta[group].set(name,(riskDelta[group].get(name)||0)+delta);
    const riskMoveSafe=(sourceStock,destination,amount)=>{
      const delta=amount/totalValue*100, checks=[];
      const srcFactors=new Set(stockRiskTags(sourceStock)), dstFactors=new Set(stockRiskTags(destination));
      for(const name of new Set([...srcFactors,...dstFactors])) checks.push(['factors',name,(dstFactors.has(name)?delta:0)-(srcFactors.has(name)?delta:0),n(targets.maxFactor)||45]);
      const srcCur=stockCurrency(sourceStock), dstCur=stockCurrency(destination);
      for(const name of new Set([srcCur,dstCur])) checks.push(['currencies',name,(dstCur===name?delta:0)-(srcCur===name?delta:0),n(targets.maxCurrency)||70]);
      const srcReg=stockRegion(sourceStock), dstReg=stockRegion(destination);
      for(const name of new Set([srcReg,dstReg])) checks.push(['regions',name,(dstReg===name?delta:0)-(srcReg===name?delta:0),n(targets.maxRegion)||70]);
      return checks.every(([group,name,moveDelta,limit])=>{
        const current=riskPct(group,name)+(riskDelta[group].get(name)||0), next=current+moveDelta;
        return current>limit ? next<=current+.01 : next<=limit+.01;
      });
    };
    const applyRiskMove=(sourceStock,destination,amount)=>{
      const delta=amount/totalValue*100, srcFactors=new Set(stockRiskTags(sourceStock)), dstFactors=new Set(stockRiskTags(destination));
      for(const name of new Set([...srcFactors,...dstFactors])) addRiskDelta('factors',name,(dstFactors.has(name)?delta:0)-(srcFactors.has(name)?delta:0));
      const srcCur=stockCurrency(sourceStock), dstCur=stockCurrency(destination);
      for(const name of new Set([srcCur,dstCur])) addRiskDelta('currencies',name,(dstCur===name?delta:0)-(srcCur===name?delta:0));
      const srcReg=stockRegion(sourceStock), dstReg=stockRegion(destination);
      for(const name of new Set([srcReg,dstReg])) addRiskDelta('regions',name,(dstReg===name?delta:0)-(srcReg===name?delta:0));
    };
    const usedDest=new Set(), sectorDeltas=new Map(), moves=[]; let totalConvDelta=0, totalOverlapDelta=0, totalMoved=0;
    for(const src of queue){
      if(moves.length>=3) break;
      const amount=Math.max(100,Math.min(1000,Math.round((src.value*.25)/50)*50||100));
      const sim=rebalanceSimulation(src.stock.ticker,amount); if(sim.error||!sim.results?.length) continue;
      const dest=sim.results.find(r=>{
        const key=txt(r.stock.ticker).toUpperCase(), sector=txt(r.stock.sector)||'Sem setor';
        const cumulativeSectorPct=r.sectorPct+((sectorDeltas.get(sector)||0)/totalValue*100);
        const projectedOverlap=totalOverlapDelta+r.overlapDelta;
        const overlapSafe=targets.overlap==='reduce'?projectedOverlap<=0:projectedOverlap<2;
        return !usedDest.has(key)&&r.autoEligible&&cumulativeSectorPct<=maxSector+1&&overlapSafe&&riskMoveSafe(sim.source,r.stock,sim.amount);
      });
      if(!dest) continue;
      const destKey=txt(dest.stock.ticker).toUpperCase(), destSector=txt(dest.stock.sector)||'Sem setor', srcSector=txt(sim.source.sector)||'Sem setor';
      usedDest.add(destKey);
      sectorDeltas.set(srcSector,(sectorDeltas.get(srcSector)||0)-sim.amount);
      sectorDeltas.set(destSector,(sectorDeltas.get(destSector)||0)+sim.amount);
      applyRiskMove(sim.source,dest.stock,sim.amount);
      totalConvDelta+=dest.convDelta; totalOverlapDelta+=dest.overlapDelta; totalMoved+=sim.amount;
      moves.push({from:sim.source,to:dest.stock,amount:sim.amount,convDelta:dest.convDelta,overlapDelta:dest.overlapDelta});
    }
    return {moves,totalConvDelta,totalOverlapDelta,totalMoved};
  }

  function renderMultiMovePlan(plan){
    if(!plan?.moves?.length) return '<p class="market-case-note">Não encontrei um plano automático robusto. Experimenta o Rebalancer manual: a Vestra agora mostra candidatos aceitáveis com alertas em vez de esconder tudo.</p>';
    const impact=plan.totalConvDelta>0&&plan.totalOverlapDelta<=1?'Melhora':plan.totalConvDelta<0||plan.totalOverlapDelta>=4?'Piora':'Neutro';
    return `<div class="market-plan-summary"><strong>${impact}</strong><span>${euro(plan.totalMoved)} realocados · Δ convicção ${plan.totalConvDelta>=0?'+':''}${plan.totalConvDelta.toFixed(2)} · Δ overlap ${plan.totalOverlapDelta>=0?'+':''}${plan.totalOverlapDelta.toFixed(1)} pp</span></div><div class="market-plan-list">${plan.moves.map((m,i)=>`<div class="market-plan-row"><span class="market-rebalance-rank">${i+1}</span><div><strong>${esc(m.from.ticker)} → ${esc(m.to.ticker)} · ${euro(m.amount)}</strong><small>Δ convicção ${m.convDelta>=0?'+':''}${m.convDelta.toFixed(2)} · overlap ${m.overlapDelta>=0?'+':''}${m.overlapDelta.toFixed(1)} pp</small></div></div>`).join('')}</div><p class="market-case-note">Plano indicativo e conservador: só inclui movimentos com melhoria líquida positiva e sem agravamento material dos limites. Não considera impostos, spreads, comissões, liquidez nem preferências pessoais.</p>`;
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
    const portfolioBase=researchUniverseValue(assets)||analysed;
    const src=rows.find(r=>txt(r.stock.ticker).toUpperCase()===source); if(!src) return {error:'Posição de origem não encontrada.'};
    const move=Math.max(0,Math.min(n(amount)||0,src.value)); if(move<=0) return {error:'Indica um montante válido.'};
    const srcConv=portfolioConviction(src.stock); if(srcConv==null) return {error:'A posição de origem não tem convicção calculável.'};
    const sectors=new Map(); for(const r of rows){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const etfs=rows.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/portfolioBase*100}));
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
      const sectorPct=sectorValue/portfolioBase*100;
      const positionPct=(existingValue+move)/portfolioBase*100;
      const indirect=isFund(stock)?0:indirectExposurePct(stock,etfs);
      const decision=evaluatePortfolioMove({mode:'replace',sourceStock:src.stock,destination:stock,rows,amount:move,totalAfter:portfolioBase,sourceConv:srcConv,destinationConv:conv,positionPct,sectorPct,indirect,sourceIndirect:srcIndirect});
      const {targets,maxPos,maxSector,riskPenalty,overlapDelta,convictionGain,convDelta,autoEligible,warnings}=decision;
      const positionHeadroom=maxPos-positionPct, sectorHeadroom=maxSector-sectorPct;
      const diversifies=destSector!==srcSector && (sectors.get(destSector)||0)/portfolioBase*100<Math.min(20,maxSector*.75);
      const tiltBonus=portfolioTiltBonus(stock,targets.tilt);
      return {stock,conv,convictionGain,convDelta,positionPct,sectorPct,positionHeadroom,sectorHeadroom,indirect,overlapDelta,riskPenalty,diversifies,tiltBonus,existing:!!existing,targets,tier:decision.evidence.tier,warnings,autoEligible};
    }).filter(Boolean).sort((a,b)=>{
      const rank={preferred:0,acceptable:1,research:2};
      return Number(b.autoEligible)-Number(a.autoEligible)
        ||(rank[a.tier]-rank[b.tier])
        ||b.convictionGain-a.convictionGain
        ||a.overlapDelta-b.overlapDelta
        ||a.riskPenalty-b.riskPenalty
        ||Number(b.diversifies)-Number(a.diversifies)
        ||b.sectorHeadroom-a.sectorHeadroom
        ||b.positionHeadroom-a.positionHeadroom
        ||b.tiltBonus-a.tiltBonus;
    }).slice(0,5);
    return {source:src.stock,amount:move,sourceConv:srcConv,results:ranked};
  }

  function renderRebalanceResults(sim){
    if(sim?.error) return `<p class="market-case-note">${esc(sim.error)}</p>`;
    if(!sim?.results?.length) return '<p class="market-case-note">Sem candidatos sequer para research. Revê o universo de dados ou os Portfolio Targets.</p>';
    const t=loadPortfolioTargets();
    const tierLabel=r=>r.autoEligible?'Elegível p/ plano':r.tier==='preferred'?'Preferido · manual':r.tier==='acceptable'?'Aceitável · manual':'Research';
    return `<div class="market-target-summary">Limites: posição ${t.maxPosition}% · setor ${t.maxSector}% · ${t.overlap==='reduce'?'reduzir overlap':'overlap neutro'} · ${esc(t.tilt)}</div><div class="market-rebalance-list">${sim.results.map((r,i)=>`<button type="button" class="market-rebalance-row" data-market-ticker="${esc(r.stock.ticker)}"><span class="market-rebalance-rank">${i+1}</span><span><strong>${esc(r.stock.ticker)} · ${esc(r.stock.name||'')}</strong><small>${tierLabel(r)} · ${r.existing?'já em carteira':'nova posição'} · conv. ${Math.round(r.conv)} · ganho ${r.convictionGain>=0?'+':''}${r.convictionGain.toFixed(1)} · peso após ${r.positionPct.toFixed(1)}% · setor ${r.sectorPct.toFixed(0)}%</small><small>Δ carteira ${r.convDelta>=0?'+':''}${r.convDelta.toFixed(2)} · overlap ${r.overlapDelta>=0?'+':''}${r.overlapDelta.toFixed(1)} pp${r.warnings?.length?' · ⚠ '+esc(r.warnings.slice(0,2).join(' · ')):''}</small></span></button>`).join('')}</div><p class="market-case-note">A ordem usa critérios explícitos: elegibilidade, evidência, ganho de convicção, overlap, Risk Budget, diversificação e headroom. Não existe um score composto de Portfolio Fit. Os restantes ficam visíveis apenas para comparação manual.</p>`;
  }

  function freshCapitalPlan(amount){
    const fresh=Math.max(0,n(amount)||0); if(fresh<50) return {error:'Indica pelo menos 50 € de novo capital.'};
    const assets=portfolioAssets().slice().filter(researchEligibleAsset);
    const researchTotal=assets.reduce((sum,a)=>sum+portfolioValue(a),0);
    const rowMap=new Map();
    for(const a of assets){
      const t=assetTicker(a); if(!t) continue; const base=t.replace(/\.[A-Z]+$/,'');
      const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===base); if(!stock) continue;
      const key=txt(stock.ticker).toUpperCase(); const prev=rowMap.get(key)||{stock,value:0}; prev.value+=portfolioValue(a); rowMap.set(key,prev);
    }
    const rows=[...rowMap.values()]; const analysed=rows.reduce((sum,r)=>sum+r.value,0)||1; const currentBase=researchTotal||analysed; const afterTotal=currentBase+fresh;
    const sectors=new Map(); for(const r of rows){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const held=new Map(rows.map(r=>[txt(r.stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,''),r]));
    const etfs=rows.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/currentBase*100}));
    const targets=loadPortfolioTargets(), maxPos=Math.max(3,Math.min(30,n(targets.maxPosition)||10)), maxSector=Math.max(10,Math.min(60,n(targets.maxSector)||25));
    const universe=M.stocks.filter(x=>!isFund(x)&&n(x.score)!=null&&!['watch','high','severe'].includes(txt(x.risk_gate)));
    const candidates=universe.map(stock=>{
      const conv=portfolioConviction(stock); if(conv==null) return null;
      const base=txt(stock.ticker).toUpperCase().replace(/\.[A-Z]+$/,''); const existing=held.get(base); const existingValue=existing?.value||0;
      const sector=txt(stock.sector)||'Sem setor', sectorValue=sectors.get(sector)||0, indirect=isFund(stock)?0:indirectExposurePct(stock,etfs);
      const strictPosCapacity=Math.max(0,afterTotal*maxPos/100-existingValue), strictSectorCapacity=Math.max(0,afterTotal*maxSector/100-sectorValue);
      const capacity=Math.min(strictPosCapacity,strictSectorCapacity,fresh); if(capacity<50) return null;
      const positionPct=(existingValue+Math.min(capacity,fresh))/afterTotal*100, sectorPct=(sectorValue+Math.min(capacity,fresh))/afterTotal*100;
      const decision=evaluatePortfolioMove({mode:'fresh',destination:stock,rows,amount:Math.min(capacity,fresh),totalAfter:afterTotal,destinationConv:conv,positionPct,sectorPct,indirect});
      const {tier}=decision.evidence;
      // Fresh Capital must consume the canonical decision gate. Rebuilding only
      // part of the rule here can bypass risk-budget or target constraints.
      const baseEligible=decision.autoEligible;
      const sectorNow=sectorValue/currentBase*100, sectorHeadroom=maxSector-sectorNow, positionNow=existingValue/currentBase*100;
      const underweightExisting=!!existing&&positionNow<maxPos*.65;
      const tiltBonus=portfolioTiltBonus(stock,targets.tilt);
      const warnings=[...decision.evidence.warnings];
      return {stock,conv,capacity,existingValue,sector,sectorValue,sectorHeadroom,indirect,tier,warnings,baseEligible,underweightExisting,tiltBonus};
    }).filter(Boolean).sort((a,b)=>{
      const rank={preferred:0,acceptable:1,research:2};
      return Number(b.baseEligible)-Number(a.baseEligible)
        ||(rank[a.tier]-rank[b.tier])
        ||b.conv-a.conv
        ||b.sectorHeadroom-a.sectorHeadroom
        ||a.indirect-b.indirect
        ||Number(b.underweightExisting)-Number(a.underweightExisting)
        ||b.tiltBonus-a.tiltBonus;
    });
    const baselineRisk=portfolioRiskProfile(rows,afterTotal);
    const riskPct=(group,name)=>baselineRisk[group].find(x=>x.name===name)?.pct||0;
    const riskAdds={factors:new Map(),currencies:new Map(),regions:new Map()};
    const addRisk=(group,name,delta)=>riskAdds[group].set(name,(riskAdds[group].get(name)||0)+delta);
    const riskAddSafe=(stock,amount)=>{
      const delta=amount/afterTotal*100, checks=[];
      for(const name of stockRiskTags(stock)) checks.push(['factors',name,delta,n(targets.maxFactor)||45]);
      checks.push(['currencies',stockCurrency(stock),delta,n(targets.maxCurrency)||70]);
      checks.push(['regions',stockRegion(stock),delta,n(targets.maxRegion)||70]);
      return checks.every(([group,name,inc,limit])=>{
        const current=riskPct(group,name)+(riskAdds[group].get(name)||0), next=current+inc;
        return current>limit ? next<=current+.01 : next<=limit+.01;
      });
    };
    const applyRiskAdd=(stock,amount)=>{
      const delta=amount/afterTotal*100;
      for(const name of stockRiskTags(stock)) addRisk('factors',name,delta);
      addRisk('currencies',stockCurrency(stock),delta);
      addRisk('regions',stockRegion(stock),delta);
    };
    const allocationsByTicker=new Map(), sectorAdds=new Map(); let remaining=fresh;
    const eligible=candidates.filter(c=>c.baseEligible).slice(0,5);
    let progressed=true;
    while(remaining>=50&&progressed){
      progressed=false;
      for(const cand of eligible){
        if(remaining<50) break;
        const key=txt(cand.stock.ticker).toUpperCase(), current=allocationsByTicker.get(key)||0;
        const sectorRoom=Math.max(0,afterTotal*maxSector/100-cand.sectorValue-(sectorAdds.get(cand.sector)||0));
        const positionRoom=Math.max(0,cand.capacity-current);
        const tranche=Math.min(50,remaining,sectorRoom,positionRoom);
        if(tranche<50||!riskAddSafe(cand.stock,tranche)) continue;
        allocationsByTicker.set(key,current+tranche);
        sectorAdds.set(cand.sector,(sectorAdds.get(cand.sector)||0)+tranche);
        applyRiskAdd(cand.stock,tranche);
        remaining-=tranche; progressed=true;
      }
    }
    const allocations=eligible.map(c=>{
      const amount=allocationsByTicker.get(txt(c.stock.ticker).toUpperCase())||0;
      if(amount<50)return null;
      return {...c,amount,positionPct:(c.existingValue+amount)/afterTotal*100,sectorPct:(c.sectorValue+(sectorAdds.get(c.sector)||0))/afterTotal*100};
    }).filter(Boolean);
    const currentConvRows=rows.map(r=>({...r,conv:portfolioConviction(r.stock)})).filter(r=>r.conv!=null&&r.value>0), convBase=currentConvRows.reduce((a,r)=>a+r.value,0)||1;
    const currentConv=currentConvRows.reduce((a,r)=>a+r.value*r.conv,0)/convBase;
    const added=allocations.reduce((a,x)=>a+x.amount,0), afterConv=(currentConv*convBase+allocations.reduce((a,x)=>a+x.amount*x.conv,0))/(convBase+added||1);
    return {fresh,allocated:added,remaining:fresh-added,currentConv,afterConv,allocations,manual:candidates.filter(x=>!x.baseEligible).slice(0,3),targets};
  }

  function renderFreshCapitalPlan(plan){
    if(plan?.error) return `<p class="market-case-note">${esc(plan.error)}</p>`;
    if(!plan?.allocations?.length){
      const manual=plan?.manual?.length?`<div class="market-fresh-list">${plan.manual.map(x=>`<button type="button" class="market-fresh-row" data-market-ticker="${esc(x.stock.ticker)}"><span><strong>${esc(x.stock.ticker)}</strong><small>Comparação manual · conv. ${Math.round(x.conv)} · ${esc(x.sector)}</small><small>${x.warnings?.length?'⚠ '+esc(x.warnings.slice(0,2).join(' · ')):'Não cumpre os filtros automáticos.'}</small></span></button>`).join('')}</div>`:''; 
      return `<p class="market-case-note">Não encontrei destinos robustos para distribuição automática dentro dos targets atuais. O capital fica por alocar.</p>${manual}`;
    }
    return `<div class="market-fresh-summary"><strong>${euro(plan.allocated)} distribuídos</strong><span>Convicção ponderada ${plan.currentConv.toFixed(1)} → ${plan.afterConv.toFixed(1)}${plan.remaining>=50?` · ${euro(plan.remaining)} ficam por alocar`:''}</span></div><div class="market-fresh-list">${plan.allocations.map((x,i)=>`<button type="button" class="market-fresh-row" data-market-ticker="${esc(x.stock.ticker)}"><span class="market-rebalance-rank">${i+1}</span><span><strong>${esc(x.stock.ticker)} · ${euro(x.amount)}</strong><small>Elegível p/ capital novo · ${x.existingValue>0?'reforço existente':'nova posição'} · conv. ${Math.round(x.conv)} · ${esc(x.sector)}</small><small>Peso ${x.positionPct.toFixed(1)}% · setor ${x.sectorPct.toFixed(1)}%${x.warnings?.length?' · ⚠ '+esc(x.warnings.slice(0,2).join(' · ')):''}</small></span></button>`).join('')}</div><p class="market-case-note">A distribuição automática usa apenas candidatos com evidência forte, dentro dos targets e sem pressão material de risco/overlap. A ordem usa critérios explícitos — convicção, headroom setorial, overlap e tilt — sem voltar a pontuar valuation fora da Conviction. O montante que não cumprir estes critérios fica por alocar.</p>`;
  }

  function openTool(tool){
    ensureLoaded().then(()=>{
      const sh=$m('marketSheet'), c=$m('marketSheetContent'); if(!sh||!c)return;
      sh.hidden=false; sh.setAttribute('aria-hidden','false'); document.documentElement.classList.add('modal-open'); document.body.classList.add('modal-open'); sh.dataset.ticker='';
      sh.dataset.tool=tool||''; sh.dataset.returnView=tool==='portfolio'?(document.body?.dataset?.view==='assets'?'assets':'market'):'';
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
        const researchTotal=researchUniverseValue(assets);
        const analysed=rows.reduce((sum,r)=>sum+r.value,0);
        const first=rows.slice(0,8), rest=rows.slice(8);
        const researchRows = first.map(r=>renderRow(r.stock,`${[...r.classes].join(' · ')} · ${euro(r.value)}${r.stock.thesis_direction_label?' · '+r.stock.thesis_direction_label:''}`)).join('');
        const restRows = rest.length?`<details class="market-detail-disclosure"><summary>Ver mais ${rest.length} posições analisáveis</summary><div class="market-list" style="margin-top:7px">${rest.map(r=>renderRow(r.stock,`${[...r.classes].join(' · ')} · ${euro(r.value)}`)).join('')}</div></details>`:'';
        const aggregateAssets=(list)=>{ const m=new Map(); for(const a of list){ const key=assetTicker(a)||`${txt(a.class)}|${txt(a.name)}`; const prev=m.get(key)||{...a,value:0}; prev.value+=portfolioValue(a); m.set(key,prev); } return [...m.values()].sort((a,b)=>portfolioValue(b)-portfolioValue(a)); };
        const cryptoGrouped=aggregateAssets(crypto), otherGrouped=aggregateAssets(other);
        const assetPlainRow=(a,tone='other')=>`<div class="market-asset-row"><div><div class="market-asset-row__title"><strong>${esc(a.name||assetTicker(a)||'Ativo')}</strong><span class="market-class-badge market-class-badge--${tone}">${esc(a.class||'Outro')}</span></div><div class="market-asset-row__meta">${assetTicker(a)?esc(assetTicker(a))+' · ':''}${tone==='crypto'?'Criptoativo — métricas empresariais não se aplicam.':'Gerido na Carteira, fora do scanner fundamental.'}</div></div><div class="market-asset-row__value">${euro(portfolioValue(a))}</div></div>`;
        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">CARTEIRA × MERCADO</div><h2>As minhas posições</h2><p>Primeiro o que é analisável. Cripto e outros ativos ficam separados para não serem confundidos com empresas.</p></div><button class="market-close" data-market-close>×</button></div>
          <div class="market-portfolio-summary" data-vpu-positions="${assets.length}" data-vpu-research="${rows.length}" data-vpu-coverage="${researchTotal>0?Math.round(analysed/researchTotal*100):0}"><div class="market-portfolio-kpi"><small>Posições</small><strong>${assets.length}</strong></div><div class="market-portfolio-kpi"><small>Com research</small><strong>${rows.length}</strong></div><div class="market-portfolio-kpi"><small>Cobertura</small><strong>${researchTotal>0?Math.round(analysed/researchTotal*100):0}%</strong></div></div>
          ${portfolioIntelligence(rows,researchTotal)}
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
      // Replace the previous tool first, then notify navigation companions once.
      notifyMarketSheetChanged('tool-open');
      // WebKit can retain the old document anchor when scrollTop is reset before
      // innerHTML, reopening a portfolio half-way down its content.
      resetDossierViewport();
    });
  }

  function compareNow(){
    const input=$m('marketCompareInput'), out=$m('marketCompareResult'); if(!input||!out)return;
    const ss=input.value.split(',').map(x=>M.byTicker.get(x.trim().toUpperCase())).filter(Boolean).slice(0,4);
    if(!ss.length){out.innerHTML='<div class="market-empty">Não encontrei esses tickers.</div>';return;}
    const metrics=[['Score Vestra','score',v=>num(v)],['Qualidade','quality_pct',v=>num(v)],['Growth','growth_pct',v=>num(v)],['Valuation','value_pct',v=>num(v)],['Forward P/E','forward_pe',v=>num(v)],['ROE','roe',v=>pct(v)],['Receita YoY','revenue_growth',v=>pct(v)]];
    out.innerHTML=`<div class="market-detail-card" style="overflow:auto"><table class="market-table"><thead><tr><th>Métrica</th>${ss.map(s=>`<th>${esc(s.ticker)}</th>`).join('')}</tr></thead><tbody>${metrics.map(([l,k,f])=>`<tr><td>${l}</td>${ss.map(s=>`<td>${f(s[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

      // v2.6: bounded grids no longer need custom touch interception.

  function handleDecisionClick(e){
    const btn=e.target.closest?.('[data-decision-jump]');
    if(!btn) return;
    const kind=btn.dataset.decisionJump||'', value=btn.dataset.decisionValue||'';
    e.preventDefault();
    const scrollTo=el=>{ if(el) el.scrollIntoView?.({behavior:'smooth',block:'start'}); };
    if(kind==='ticker'&&value){ openTicker(value); return; }
    if(kind==='riskbudget'){ scrollTo(document.querySelector('.market-risk-budget')); return; }
    if(kind==='targets'){ scrollTo(document.querySelector('.market-target-fit')||document.querySelector('.market-target-engine')); return; }
    if(kind==='rebalancer'){ scrollTo(document.querySelector('.market-rebalancer')); return; }
    if(kind==='etfoptimize'){ scrollTo(document.querySelector('.market-etf-optimize')); return; }
    if(kind==='health'){ scrollTo(document.querySelector('.market-health-timeline')); return; }
    if(kind==='stress'){
      const box=document.querySelector('.market-stress-test'); scrollTo(box);
      const tab=box?.querySelector(`[data-stress-scenario="${CSS.escape(value||'rates')}"]`); tab?.click(); return;
    }
    if(kind==='actionmap'){
      const map=document.querySelector('.market-action-map'); scrollTo(map);
      if(map) applyActionMapFilter(map,value==='all'?'':value);
    }
  }

  function handleResearchQueueClick(e){
    const btn=e.target.closest?.('[data-queue-status]'); if(!btn)return;
    const row=btn.closest('.market-research-queue-row'); if(!row)return;
    e.preventDefault(); e.stopPropagation();
    setResearchQueueState(row.dataset.queueTicker||'',btn.dataset.queueStatus||'new',row.dataset.queueSignal||'');
    if(txt($m('marketSheet')?.dataset.tool)==='portfolio'){
      openTool('portfolio');
      setTimeout(()=>document.querySelector('.market-research-queue')?.scrollIntoView?.({behavior:'smooth',block:'start'}),0);
    } else renderPrimary();
  }

  function handleCheckpointClick(e){
    const btn=e.target.closest?.('[data-checkpoint-save]'); if(!btn)return;
    const box=btn.closest('.market-research-checkpoint'); if(!box)return;
    e.preventDefault(); e.stopPropagation();
    saveResearchCheckpoint(box.dataset.checkpointTicker||'',box.querySelector('[data-checkpoint-select]')?.value||'',box.querySelector('[data-checkpoint-note]')?.value||'');
    btn.textContent='Guardado'; setTimeout(()=>{btn.textContent='Guardar';},900);
  }

  function handleActionMapClick(e){
    const btn=e.target.closest?.('[data-action-filter]');
    if(!btn) return;
    const map=btn.closest('.market-action-map');
    if(!map) return;
    e.preventDefault();
    const requested=btn.dataset.actionFilter||'';
    const active=map.dataset.actionFilter||'';
    applyActionMapFilter(map,active===requested?'':requested);
  }

  const marketEventRoots=[$m('viewMarket'),$m('marketSheet')].filter(Boolean);
  function addMarketSurfaceListener(type,handler){
    marketEventRoots.forEach(root=>root.addEventListener(type,handler));
  }

  addMarketSurfaceListener('click', e=>{
    const mode=e.target.closest('[data-market-mode]'); if(mode){const nextMode=mode.dataset.marketMode; if(nextMode==='funds'&&M.mode!=='funds'){ M.fundTheme=''; M.fundLimit=100; } M.mode=nextMode; document.querySelectorAll('[data-market-mode]').forEach(x=>x.classList.toggle('is-active',x===mode)); renderPrimary(); if(M.mode==='smart') loadCongressLive().then(()=>renderPrimary());}
    const sec=e.target.closest('[data-market-sector]'); if(sec){M.sector=sec.dataset.marketSector;renderPrimary();}
    const fundTheme=e.target.closest('[data-market-fund-theme]'); if(fundTheme){M.fundTheme=fundTheme.dataset.marketFundTheme||'';M.fundLimit=100;renderPrimary();return;}
    const fundMore=e.target.closest('[data-market-fund-more]'); if(fundMore){M.fundLimit+=100;renderPrimary();return;}
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

    // Keep all Market click ownership on this single delegated listener. The
    // order mirrors the former listeners so behaviour stays stable while each
    // tap avoids four extra document-level callbacks.
    handleDecisionClick(e);
    handleResearchQueueClick(e);
    handleCheckpointClick(e);
    handleActionMapClick(e);
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

  const marketView=$m('viewMarket');
  let marketSearchRenderTimer=null;
  function scheduleMarketSearchPrimaryRender(){
    if(marketSearchRenderTimer!==null) clearTimeout(marketSearchRenderTimer);
    marketSearchRenderTimer=setTimeout(()=>{
      marketSearchRenderTimer=null;
      renderPrimary();
    },90);
  }
  marketView?.addEventListener('change', e=>{
    if(e.target.matches('[data-market-sector-select]') && e.target.value){ M.sector=e.target.value; renderPrimary(); }
  });

  marketView?.addEventListener('input', e=>{
    if(e.target.id==='marketSearch'){
      M.query=e.target.value.trim();
      ensureLoaded().then(()=>{
        // Suggestions stay immediate, while the heavier market surface update is
        // coalesced across rapid keystrokes so WebKit does not rebuild the full
        // results DOM on every character.
        renderSearchSuggestions();
        scheduleMarketSearchPrimaryRender();
      });
    }
  });

  marketView?.addEventListener('focusin', e=>{
    if(e.target?.id==='marketSearch' && M.query) ensureLoaded().then(renderSearchSuggestions);
  });
  marketView?.addEventListener('focusout', e=>{
    if(e.target?.id==='marketSearch') setTimeout(()=>{
      const active=document.activeElement;
      if(!active?.closest?.('#marketSuggestions')) hideSearchSuggestions();
    },140);
  });

  loadWatchlist();
  window.VestraMarket={ensureLoaded,openTicker,openPortfolioAsset,resolvePortfolioStock,upsertRemoteStock,toggleWatch};

  function applyActionMapFilter(map,requested=''){
    if(!map)return;
    const next=requested||'';
    map.dataset.actionFilter=next;
    map.querySelectorAll('[data-action-filter]').forEach(x=>x.classList.toggle('is-active',next&&x.dataset.actionFilter===next));
    let shown=0;
    map.querySelectorAll('.market-action-row[data-action-key]').forEach(row=>{
      const key=row.dataset.actionKey||'';
      const visible=!next||(next==='attention'?['review','replace'].includes(key):key===next);
      row.hidden=!visible;
      if(visible) shown++;
    });
    map.querySelectorAll('.market-detail-disclosure').forEach(d=>{
      const any=[...d.querySelectorAll('.market-action-row[data-action-key]')].some(r=>!r.hidden);
      d.hidden=!!next&&!any;
      d.open=!!next&&any;
    });
    const status=map.querySelector('[data-action-filter-status]');
    if(status){
      const labels={reinforce:'a reforçar',hold:'a manter',review:'a rever',replace:'a substituir',attention:'a rever/substituir'};
      status.textContent=next?`${shown} ${shown===1?'posição':'posições'} ${labels[next]||''}`:'Mostrar todas as posições';
    }
    map.querySelector('.market-action-list')?.scrollIntoView?.({behavior:'smooth',block:'nearest'});
  }

})();
