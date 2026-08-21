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
    region: 'all'
  };

  const $m = id => document.getElementById(id);
  const n = v => Number.isFinite(Number(v)) ? Number(v) : null;
  const txt = v => String(v ?? '').trim();
  const esc = v => txt(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct = v => n(v) == null ? '—' : `${(Math.abs(n(v)) <= 1 ? n(v)*100 : n(v)).toFixed(1)}%`;
  const num = v => n(v) == null ? '—' : new Intl.NumberFormat('pt-PT',{maximumFractionDigits:1}).format(n(v));
  const money = (v, c='USD') => n(v) == null ? '—' : new Intl.NumberFormat('pt-PT',{style:'currency',currency:c || 'USD',maximumFractionDigits:2}).format(n(v));
  const compact = v => n(v) == null ? '—' : new Intl.NumberFormat('pt-PT',{notation:'compact',maximumFractionDigits:1}).format(n(v));

  function portfolioTickers(){
    try {
      const a = (typeof state !== 'undefined' && state && Array.isArray(state.assets)) ? state.assets : [];
      return new Set(a.flatMap(x => [x.yahooTicker,x.ticker,x.symbol]).map(txt).map(x=>x.toUpperCase()).filter(Boolean));
    } catch { return new Set(); }
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
      M.loaded = true;
      renderPrimary();
    })().catch(err=>{
      const el=$m('marketPrimary'); if(el) el.innerHTML=`<div class="market-empty">Não foi possível carregar os dados de mercado.<br><small>${esc(err.message)}</small></div>`;
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
    return `<div class="market-row" data-market-ticker="${esc(s.ticker)}">
      <div><div class="market-row__title"><span class="market-row__ticker">${esc(s.ticker)}</span><span class="market-row__name">${esc(s.name||'')}</span></div><div class="market-row__meta">${esc(sub)}</div></div>
      <div class="market-score ${scoreClass(s.score)}">${n(s.score)==null?'—':Math.round(n(s.score))}</div>
    </div>`;
  }

  function renderDiscover(){
    const sectors = [...new Set(M.stocks.filter(s=>!isFund(s)&&s.sector).map(s=>s.sector))].sort().slice(0,25);
    const qs = M.query.toLowerCase();
    let rows = qs ? M.stocks.filter(s=>!isFund(s) && `${s.ticker} ${s.name} ${s.sector} ${s.industry}`.toLowerCase().includes(qs)) : bestStocks();
    if(M.sector!=='all') rows=rows.filter(s=>s.sector===M.sector);
    rows=rows.slice(0,20);
    return `<section class="market-section"><div class="market-section__head"><div><h3>${qs?'Resultados':'Ideias com melhor sinal'}</h3><p>${qs?'Pesquisa no universo global':'Qualidade, crescimento, balanço, cash flow e valuation'}</p></div><span class="market-data-age">${ageText()}</span></div>
      <div class="market-chipbar"><button class="market-chip ${M.sector==='all'?'is-active':''}" data-market-sector="all">Todos</button>${sectors.slice(0,8).map(x=>`<button class="market-chip ${M.sector===x?'is-active':''}" data-market-sector="${esc(x)}">${esc(x)}</button>`).join('')}</div>
      <div class="market-list">${rows.length?rows.map(s=>renderRow(s)).join(''):'<div class="market-empty">Sem resultados com estes filtros.</div>'}</div></section>`;
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

  function renderSmart(){
    let rows=M.stocks.filter(s=>!isFund(s)&&((n(s.insider_buy_count_30d)||0)>0 || (Array.isArray(s.congress_trades)&&s.congress_trades.length)))
      .sort((a,b)=>smartRank(b)-smartRank(a)).slice(0,20);
    return `<section class="market-section"><div class="market-section__head"><div><h3>Smart money</h3><p>Compras de insiders e atividade declarada no Congresso dos EUA</p></div><span class="market-data-age">${ageText()}</span></div><div class="market-list">${rows.map(s=>renderRow(s,`${n(s.insider_buy_count_30d)||0} compras insider · ${Array.isArray(s.congress_trades)?s.congress_trades.length:0} trades Congresso`)).join('')||'<div class="market-empty">Sem atividade relevante.</div>'}</div></section>`;
  }

  function renderPrimary(){
    const root=$m('marketPrimary'); if(!root || !M.loaded) return;
    root.innerHTML = M.mode==='funds'?renderFunds():M.mode==='smart'?renderSmart():renderDiscover();
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

  function detailBase(s){
    return `<div class="market-detail-head"><div><div class="market-kicker">${esc(isFund(s)?'ETF / Fundo':s.sector||'Empresa')}</div><h2>${esc(s.ticker)}</h2><p>${esc(s.name||'')}</p></div><button class="market-close" data-market-close>×</button></div>
      ${sparkSvg(s.price_history_1y)}
      <div class="market-metrics"><div class="market-metric"><small>Score Vestra</small><strong>${n(s.score)==null?'—':Math.round(s.score)}/100</strong></div><div class="market-metric"><small>Preço</small><strong>${money(s.current_price,s.currency)}</strong></div><div class="market-metric"><small>Forward P/E</small><strong>${num(s.forward_pe)}</strong></div><div class="market-metric"><small>ROE</small><strong>${pct(s.roe)}</strong></div><div class="market-metric"><small>Receita YoY</small><strong>${pct(s.revenue_growth)}</strong></div><div class="market-metric"><small>FCF yield</small><strong>${pct(s.fcf_yield)}</strong></div></div>
      <div class="market-tabs"><button class="market-tab is-active" data-detail-tab="overview">Overview</button><button class="market-tab" data-detail-tab="growth">Growth</button><button class="market-tab" data-detail-tab="valuation">Valuation</button><button class="market-tab" data-detail-tab="smart">Smart money</button><button class="market-tab" data-detail-tab="news">Notícias</button></div><div id="marketDetailBody"></div>`;
  }

  function renderDetailTab(s,tab){
    const body=$m('marketDetailBody'); if(!body) return;
    if(tab==='overview') body.innerHTML=`<div class="market-detail-card"><h4>${esc(s.thesis_type||'Tese')}</h4><p>${esc(s.thesis_summary||s.business_summary||'Sem síntese disponível.')}</p></div><div class="market-detail-card"><h4>Pilares</h4>${dimRows(s)}</div>${Array.isArray(s.thesis_risks)&&s.thesis_risks.length?`<div class="market-detail-card"><h4>Riscos</h4><ul>${s.thesis_risks.slice(0,6).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}`;
    if(tab==='growth') body.innerHTML=`<div class="market-detail-card"><h4>Crescimento e resultados</h4><div class="market-metrics"><div class="market-metric"><small>Receita YoY</small><strong>${pct(s.revenue_yoy_latest??s.revenue_growth)}</strong></div><div class="market-metric"><small>Lucro YoY</small><strong>${pct(s.net_income_yoy_latest??s.earnings_growth)}</strong></div><div class="market-metric"><small>EPS YoY</small><strong>${pct(s.eps_yoy_latest)}</strong></div><div class="market-metric"><small>Margem líquida</small><strong>${pct(s.net_margin_latest??s.profit_margin)}</strong></div><div class="market-metric"><small>ROCE proxy</small><strong>${pct(s.roce_proxy)}</strong></div><div class="market-metric"><small>FCF</small><strong>${compact(s.free_cash_flow)}</strong></div></div></div>`;
    if(tab==='valuation') body.innerHTML=`<div class="market-detail-card"><h4>Valuation</h4><div class="market-metrics"><div class="market-metric"><small>P/E</small><strong>${num(s.trailing_pe)}</strong></div><div class="market-metric"><small>Forward P/E</small><strong>${num(s.forward_pe)}</strong></div><div class="market-metric"><small>P/B</small><strong>${num(s.price_to_book)}</strong></div><div class="market-metric"><small>EV/EBITDA</small><strong>${num(s.enterprise_to_ebitda)}</strong></div><div class="market-metric"><small>vs sector P/E</small><strong>${pct(s.trailing_pe_vs_sector_pct)}</strong></div><div class="market-metric"><small>Dividend yield</small><strong>${pct(s.dividend_yield)}</strong></div></div></div>`;
    if(tab==='smart') {
      const ins=Array.isArray(s.insider_transactions)?s.insider_transactions.slice(0,8):[];
      const con=Array.isArray(s.congress_trades)?s.congress_trades.slice(0,8):[];
      body.innerHTML=`<div class="market-detail-card"><h4>Insiders · 30 dias</h4><p>${n(s.insider_buy_count_30d)||0} compras (${money(s.insider_buy_value_30d,'USD')}) · ${n(s.insider_sell_count_30d)||0} vendas (${money(s.insider_sell_value_30d,'USD')})</p>${ins.length?`<ul>${ins.map(x=>`<li>${esc(x.name||x.insider||'Insider')} · ${esc(x.transaction_type||x.type||'')} · ${money(x.value||x.transaction_value,'USD')}</li>`).join('')}</ul>`:''}</div><div class="market-detail-card"><h4>Congresso</h4>${con.length?`<ul>${con.map(x=>`<li>${esc(x.representative||x.name||'')} · ${esc(x.type||x.transaction||'')} · ${esc(x.amount||'')}</li>`).join('')}</ul>`:'<p>Sem operações recentes registadas.</p>'}</div>`;
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

  function openTicker(ticker){
    const s=M.byTicker.get(txt(ticker).toUpperCase()); if(!s) return;
    const sh=$m('marketSheet'), content=$m('marketSheetContent'); if(!sh||!content)return;
    content.innerHTML=detailBase(s); sh.hidden=false; sh.setAttribute('aria-hidden','false'); document.body.classList.add('modal-open');
    sh.dataset.ticker=s.ticker; renderDetailTab(s,'overview');
  }
  function closeSheet(){ const sh=$m('marketSheet'); if(!sh)return; sh.hidden=true; sh.setAttribute('aria-hidden','true'); document.body.classList.remove('modal-open'); }

  function openTool(tool){
    ensureLoaded().then(()=>{
      const sh=$m('marketSheet'), c=$m('marketSheetContent'); if(!sh||!c)return;
      sh.hidden=false; sh.setAttribute('aria-hidden','false'); document.body.classList.add('modal-open'); sh.dataset.ticker='';
      if(tool==='portfolio'){
        const p=portfolioTickers(); const rows=[...p].map(t=>M.byTicker.get(t)||M.stocks.find(s=>txt(s.ticker).toUpperCase().replace(/\.[A-Z]+$/,'')===t.replace(/\.[A-Z]+$/,''))).filter(Boolean);
        c.innerHTML=`<div class="market-detail-head"><div><div class="market-kicker">PORTFÓLIO</div><h2>As minhas posições</h2><p>Leitura fundamental das posições que a Vestra reconhece.</p></div><button class="market-close" data-market-close>×</button></div><div class="market-list">${rows.length?rows.map(s=>renderRow(s,`${s.thesis_type||''}${s.thesis_direction_label?' · '+s.thesis_direction_label:''}`)).join(''):'<div class="market-empty">Ainda não encontrei tickers do teu portfólio no universo do scanner.</div>'}</div>`;
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

  document.addEventListener('click', e=>{
    const marketNav=e.target.closest('[data-view="market"]'); if(marketNav) setTimeout(ensureLoaded,0);
    const mode=e.target.closest('[data-market-mode]'); if(mode){M.mode=mode.dataset.marketMode; document.querySelectorAll('[data-market-mode]').forEach(x=>x.classList.toggle('is-active',x===mode)); renderPrimary();}
    const sec=e.target.closest('[data-market-sector]'); if(sec){M.sector=sec.dataset.marketSector;renderPrimary();}
    const row=e.target.closest('[data-market-ticker]'); if(row){ensureLoaded().then(()=>openTicker(row.dataset.marketTicker));}
    const close=e.target.closest('[data-market-close]'); if(close) closeSheet();
    const sh=$m('marketSheet'); if(sh&&e.target===sh) closeSheet();
    const tab=e.target.closest('[data-detail-tab]'); if(tab&&sh?.dataset.ticker){document.querySelectorAll('.market-tab').forEach(x=>x.classList.toggle('is-active',x===tab)); const s=M.byTicker.get(sh.dataset.ticker.toUpperCase()); if(s)renderDetailTab(s,tab.dataset.detailTab);}
    const tool=e.target.closest('[data-market-tool]'); if(tool) openTool(tool.dataset.marketTool);
    if(e.target.closest('#marketCompareGo')) compareNow();
  });

  document.addEventListener('input', e=>{
    if(e.target.id==='marketSearch'){
      M.query=e.target.value.trim(); ensureLoaded().then(()=>renderPrimary());
    }
  });

  window.VestraMarket={ensureLoaded,openTicker};
})();
