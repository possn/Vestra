/* Vestra Market analysis tools runtime v1.1 */
(() => {
  'use strict';

  const TOOL_SET = new Set(['compare', 'scanner', 'theses', 'news']);
  const text = value => String(value ?? '').trim();
  const num = value => {
    if (value === null || value === undefined || value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };
  const esc = value => text(value).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
  const pct = value => num(value) == null ? '—' : `${(Math.abs(num(value)) <= 1 ? num(value) * 100 : num(value)).toFixed(1)}%`;
  const fmt = value => num(value) == null ? '—' : new Intl.NumberFormat('pt-PT',{maximumFractionDigits:1}).format(num(value));

  let compareSelected = [];
  let scannerStrategy = 'best_opportunities';
  let newsCache = null;
  let scannerReady = false;

  function stocks() {
    const rows = window.VestraMarketStaticUniverse?.getStocks?.();
    return Array.isArray(rows) ? rows : [];
  }

  function isFund(stock) {
    const q = text(stock?.quote_type).toUpperCase();
    const name = text(stock?.name).toUpperCase();
    return q === 'ETF' || q === 'MUTUALFUND' || /\bETF\b|ISHARES|VANGUARD|XTRACKERS|SPDR|LYXOR|AMUNDI|WISDOMTREE|INVESCO/.test(name);
  }

  async function ensureMarket() {
    try { await window.VestraMarket?.ensureLoaded?.(); } catch (_) {}
  }

  function openSheet(tool) {
    const sheet = document.getElementById('marketSheet');
    const content = document.getElementById('marketSheetContent');
    if (!sheet || !content) return null;
    sheet.hidden = false;
    sheet.setAttribute('aria-hidden', 'false');
    sheet.dataset.ticker = '';
    sheet.dataset.tool = tool;
    sheet.classList.add('market-sheet--tool-runtime');
    document.body.classList.add('modal-open');
    content.innerHTML = '';
    requestAnimationFrame(() => sheet.querySelector('.market-sheet__panel')?.scrollTo?.({ top: 0, behavior: 'auto' }));
    return content;
  }

  function closeSheet() {
    const sheet = document.getElementById('marketSheet');
    if (!sheet) return;
    sheet.hidden = true;
    sheet.setAttribute('aria-hidden', 'true');
    sheet.dataset.tool = '';
    sheet.classList.remove('market-sheet--tool-runtime');
    document.body.classList.remove('modal-open');
  }

  function header(kicker, title, subtitle) {
    return `<div class="market-detail-head market-tool-runtime__head"><div><div class="market-kicker">${esc(kicker)}</div><h2>${esc(title)}</h2><p>${esc(subtitle)}</p></div></div>`;
  }

  function stockRow(stock, meta='') {
    const score = num(stock?.score);
    return `<button type="button" class="market-row market-tool-runtime__row" data-tool-open-ticker="${esc(stock?.ticker)}"><div><div class="market-row__title"><span class="market-row__ticker">${esc(stock?.ticker)}</span><span class="market-row__name">${esc(stock?.name)}</span></div><div class="market-row__meta">${esc(meta || [stock?.sector, stock?.industry].filter(Boolean).join(' · '))}</div></div><div class="market-score ${score == null ? 'market-score--soft' : score < 55 ? 'market-score--risk' : score < 70 ? 'market-score--soft' : ''}">${score == null ? '—' : Math.round(score)}</div></button>`;
  }

  function compareCandidates(query) {
    const q = text(query).toLowerCase();
    if (!q) return [];
    const selected = new Set(compareSelected.map(stock => text(stock?.ticker).toUpperCase()));
    return stocks().filter(stock => !isFund(stock) && !selected.has(text(stock?.ticker).toUpperCase())).map(stock => {
      const ticker = text(stock?.ticker);
      const name = text(stock?.name);
      const hay = `${ticker} ${name} ${text(stock?.sector)} ${text(stock?.industry)}`.toLowerCase();
      let rank = hay.startsWith(q) ? 0 : ticker.toLowerCase().startsWith(q) ? 0 : name.toLowerCase().startsWith(q) ? 1 : hay.includes(q) ? 2 : 9;
      return { stock, rank };
    }).filter(item => item.rank < 9).sort((a,b) => a.rank - b.rank || (num(b.stock?.score) || 0) - (num(a.stock?.score) || 0)).slice(0,8).map(item => item.stock);
  }

  function renderCompare(content) {
    const chips = compareSelected.map(stock => `<button type="button" class="market-tool-runtime__selected" data-compare-remove="${esc(stock.ticker)}">${esc(stock.ticker)} <span>×</span></button>`).join('');
    content.innerHTML = `${header('COMPARAR','Empresas lado a lado','Pesquisa por nome ou ticker e escolhe até 4 empresas.')}
      <div class="market-tool-runtime__search"><input id="marketCompareSearch" autocomplete="off" placeholder="Ex.: ASML, Microsoft, Novo Nordisk…"/><div id="marketCompareSuggestions" class="market-tool-runtime__suggestions"></div></div>
      <div class="market-tool-runtime__selected-wrap">${chips || '<span class="market-tool-runtime__muted">Ainda não escolheste empresas.</span>'}</div>
      <button type="button" class="btn btn--primary market-tool-runtime__go" id="marketCompareRuntimeGo" ${compareSelected.length < 2 ? 'disabled' : ''}>Comparar ${compareSelected.length ? `(${compareSelected.length})` : ''}</button>
      <div id="marketCompareRuntimeResult"></div>`;
  }

  function renderCompareTable() {
    const out = document.getElementById('marketCompareRuntimeResult');
    if (!out || compareSelected.length < 2) return;
    const metrics = [
      ['Score','score',fmt],['Qualidade','quality_pct',fmt],['Growth','growth_pct',fmt],['Valuation','value_pct',fmt],
      ['Forward P/E','forward_pe',fmt],['ROE','roe',pct],['Receita YoY','revenue_growth',pct],['FCF yield','fcf_yield',pct],['Margem operacional','operating_margin',pct]
    ];
    out.innerHTML = `<div class="market-detail-card market-tool-runtime__table"><table class="market-table"><thead><tr><th>Métrica</th>${compareSelected.map(s => `<th>${esc(s.ticker)}</th>`).join('')}</tr></thead><tbody>${metrics.map(([label,key,format]) => `<tr><td>${esc(label)}</td>${compareSelected.map(s => `<td>${format(s?.[key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  async function ensureScanner() {
    await ensureMarket();
    const controller = window.VestraMarketScannerData?.runtimeController?.();
    if (!controller) return false;
    if (!controller.isReady?.()) {
      try { await controller.load(); } catch (_) { return false; }
    }
    scannerReady = true;
    return true;
  }

  const STRATEGIES = [
    ['best_opportunities','Oportunidades'],['quality_at_fair_price','Qualidade + preço'],['growth_at_reasonable_price','Growth'],
    ['deep_value','Value'],['low_52w','Mínimos 52s'],['insider_accumulation','Insiders'],['turnarounds','Turnarounds'],['dividend_growers','Dividendos']
  ];

  function scannerResult(stock, key) {
    return stock?.scanner_results && typeof stock.scanner_results === 'object' ? stock.scanner_results[key] : null;
  }

  function renderScannerRows(content) {
    const rows = stocks().filter(stock => !isFund(stock) && scannerResult(stock, scannerStrategy)).sort((a,b) => (num(scannerResult(b,scannerStrategy)?.score) || 0) - (num(scannerResult(a,scannerStrategy)?.score) || 0));
    const result = content.querySelector('#marketScannerRuntimeRows');
    if (!result) return;
    result.innerHTML = rows.length ? rows.slice(0,50).map(stock => {
      const r = scannerResult(stock, scannerStrategy);
      const meta = [text(r?.label), num(r?.score) == null ? '' : `Scanner ${Math.round(num(r.score))}/100`, text(stock?.sector)].filter(Boolean).join(' · ');
      return stockRow(stock, meta);
    }).join('') : `<div class="market-empty"><strong>Sem resultados nesta estratégia.</strong><span>O universo foi carregado, mas esta estratégia não tem candidatos válidos agora.</span></div>`;
  }

  async function renderScanner(content) {
    content.innerHTML = `${header('SCANNER VESTRA','Estratégias inteligentes','Filtra o universo por sinais já calculados pela Vestra.')}
      <div class="market-tool-runtime__loading">A carregar estratégias…</div>`;
    const ok = await ensureScanner();
    if (!content.isConnected) return;
    if (!ok) {
      content.innerHTML = `${header('SCANNER VESTRA','Estratégias inteligentes','Filtra o universo por sinais já calculados pela Vestra.')}<div class="market-empty market-empty--error"><strong>Scanner indisponível.</strong><span>Não foi possível carregar o payload do scanner. Tenta novamente.</span><button type="button" class="btn btn--outline btn--sm" data-tool-runtime-retry="scanner">Tentar novamente</button></div>`;
      return;
    }
    const chips = STRATEGIES.map(([key,label]) => `<button type="button" class="market-chip ${key === scannerStrategy ? 'is-active' : ''}" data-tool-scanner-strategy="${key}">${esc(label)}</button>`).join('');
    content.innerHTML = `${header('SCANNER VESTRA','Estratégias inteligentes','Filtra o universo por sinais já calculados pela Vestra.')}<div class="market-tool-runtime__chips">${chips}</div><div id="marketScannerRuntimeRows" class="market-list"></div>`;
    renderScannerRows(content);
  }

  function renderTheses(content) {
    const rows = stocks().filter(stock => !isFund(stock) && ['up','down'].includes(text(stock?.thesis_direction)) && num(stock?.score) != null).sort((a,b) => {
      if (text(a.thesis_direction) !== text(b.thesis_direction)) return text(a.thesis_direction) === 'up' ? -1 : 1;
      return Math.abs(num(b.thesis_score_delta_30d) || 0) - Math.abs(num(a.thesis_score_delta_30d) || 0);
    }).slice(0,60);
    content.innerHTML = `${header('TESES','O que está a mudar','Empresas cuja tese está a melhorar ou a piorar, com acesso direto ao dossier.')}<div class="market-list">${rows.length ? rows.map(stock => stockRow(stock, `${stock.thesis_direction === 'up' ? '↑ A melhorar' : '↓ A piorar'} · Δ30d ${fmt(stock.thesis_score_delta_30d)}`)).join('') : '<div class="market-empty">Sem alterações de tese suficientes no universo atual.</div>'}</div>`;
  }

  function newsCandidates(query) {
    const q = text(query).toLowerCase();
    if (!q) return [];
    return stocks().filter(stock => !isFund(stock) && `${text(stock.ticker)} ${text(stock.name)}`.toLowerCase().includes(q)).sort((a,b) => (num(b.score)||0)-(num(a.score)||0)).slice(0,10);
  }

  async function renderNews(content) {
    content.innerHTML = `${header('NOTÍCIAS','Notícias por empresa','Pesquisa qualquer empresa do universo. A Vestra abre diretamente o feed de notícias do dossier.')}<div class="market-tool-runtime__search"><input id="marketNewsSearch" autocomplete="off" placeholder="Empresa ou ticker…"/><div id="marketNewsSuggestions" class="market-tool-runtime__suggestions"></div></div><div class="market-tool-runtime__note">Também podes abrir qualquer posição abaixo e saltar diretamente para Notícias.</div><div id="marketNewsPortfolio" class="market-list"></div>`;
    let portfolio = [];
    try {
      const assets = Array.isArray(window.state?.assets) ? window.state.assets : [];
      const all = stocks();
      const byTicker = new Map(all.map(stock => [text(stock?.ticker).toUpperCase(), stock]));
      for (const asset of assets) {
        const ticker = text(asset?.yahooTicker || asset?.ticker || asset?.symbol).toUpperCase();
        if (byTicker.has(ticker) && !portfolio.some(stock => text(stock.ticker).toUpperCase() === ticker)) portfolio.push(byTicker.get(ticker));
      }
    } catch (_) {}
    const list = content.querySelector('#marketNewsPortfolio');
    if (list) list.innerHTML = portfolio.length ? portfolio.slice(0,15).map(stock => `<button type="button" class="market-row market-tool-runtime__row" data-tool-open-news="${esc(stock.ticker)}"><div><div class="market-row__title"><span class="market-row__ticker">${esc(stock.ticker)}</span><span class="market-row__name">${esc(stock.name)}</span></div><div class="market-row__meta">Abrir notícias</div></div><span class="market-portfolio-access__arrow">›</span></button>`).join('') : '<div class="market-empty">Pesquisa uma empresa acima para ver notícias.</div>';
  }

  async function openTicker(ticker, news=false) {
    closeSheet();
    await ensureMarket();
    const nav = window.VestraNavigation;
    if (!nav?.openCompany) return false;
    let opened = false;
    try { opened = await nav.openCompany(ticker, { origin: 'market' }); } catch (_) { return false; }
    if (!opened) return false;
    if (!news) return true;
    let attempts = 0;
    const selectNews = () => {
      const tab = document.querySelector('#marketSheet [data-detail-tab="news"]');
      if (tab) { tab.click(); return; }
      if (++attempts < 20) setTimeout(selectNews, 60);
    };
    setTimeout(selectNews, 60);
    return true;
  }

  async function openTool(tool) {
    await ensureMarket();
    const content = openSheet(tool);
    if (!content) return;
    if (tool === 'compare') { compareSelected = []; renderCompare(content); }
    else if (tool === 'scanner') await renderScanner(content);
    else if (tool === 'theses') renderTheses(content);
    else if (tool === 'news') await renderNews(content);
  }

  function installStyles() {
    if (document.getElementById('vestraMarketAnalysisToolsRuntimeStyles')) return;
    const style = document.createElement('style');
    style.id = 'vestraMarketAnalysisToolsRuntimeStyles';
    style.textContent = `
      #marketSheet.market-sheet--tool-runtime>.market-sheet__panel{max-height:min(88dvh,760px)!important;overflow-y:auto!important;overscroll-behavior:contain!important;-webkit-overflow-scrolling:touch!important;padding-bottom:max(24px,env(safe-area-inset-bottom))}
      .market-tool-runtime__head{position:sticky;top:0;z-index:3;background:var(--card);padding-top:4px;padding-bottom:10px}
      .market-tool-runtime__search{position:relative;margin:4px 0 10px}.market-tool-runtime__search input{width:100%;min-height:48px;border:1px solid var(--line);border-radius:14px;background:var(--card2);color:var(--text);padding:0 14px;font:inherit}
      .market-tool-runtime__suggestions{display:grid;gap:6px;margin-top:7px}.market-tool-runtime__suggestion{width:100%;display:flex;justify-content:space-between;gap:10px;align-items:center;text-align:left;border:1px solid var(--line);background:var(--card2);color:var(--text);border-radius:12px;padding:9px 10px}.market-tool-runtime__suggestion span{min-width:0}.market-tool-runtime__suggestion strong,.market-tool-runtime__suggestion small{display:block}.market-tool-runtime__suggestion small{color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .market-tool-runtime__selected-wrap{display:flex;flex-wrap:wrap;gap:6px;min-height:34px;margin-bottom:10px}.market-tool-runtime__selected{border:1px solid rgba(32,129,126,.3);background:rgba(32,129,126,.09);color:var(--text);border-radius:999px;padding:7px 10px;font-weight:800}.market-tool-runtime__go{width:100%;margin-bottom:12px}.market-tool-runtime__muted,.market-tool-runtime__note{color:var(--muted);font-size:11px;line-height:1.4}.market-tool-runtime__note{margin:2px 0 10px}.market-tool-runtime__chips{display:flex;gap:7px;overflow-x:auto;padding:2px 0 10px;-webkit-overflow-scrolling:touch}.market-tool-runtime__chips .market-chip{flex:0 0 auto}.market-tool-runtime__row{width:100%;text-align:left}.market-tool-runtime__table{overflow-x:auto}.market-tool-runtime__loading{padding:20px;color:var(--muted);text-align:center}
    `;
    document.head.appendChild(style);
  }

  document.addEventListener('click', event => {
    const tool = event.target.closest?.('[data-market-tool]');
    if (tool && TOOL_SET.has(tool.dataset.marketTool)) {
      event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
      openTool(tool.dataset.marketTool);
      return;
    }
    if (event.target.closest?.('[data-tool-runtime-close]')) { event.preventDefault(); closeSheet(); return; }
    const suggestion = event.target.closest?.('[data-compare-add]');
    if (suggestion) {
      const stock = stocks().find(s => text(s?.ticker).toUpperCase() === text(suggestion.dataset.compareAdd).toUpperCase());
      if (stock && compareSelected.length < 4 && !compareSelected.includes(stock)) compareSelected.push(stock);
      renderCompare(document.getElementById('marketSheetContent'));
      return;
    }
    const remove = event.target.closest?.('[data-compare-remove]');
    if (remove) {
      compareSelected = compareSelected.filter(s => text(s?.ticker).toUpperCase() !== text(remove.dataset.compareRemove).toUpperCase());
      renderCompare(document.getElementById('marketSheetContent'));
      return;
    }
    if (event.target.closest?.('#marketCompareRuntimeGo')) { renderCompareTable(); return; }
    const strategy = event.target.closest?.('[data-tool-scanner-strategy]');
    if (strategy) {
      scannerStrategy = strategy.dataset.toolScannerStrategy;
      document.querySelectorAll('[data-tool-scanner-strategy]').forEach(node => node.classList.toggle('is-active', node === strategy));
      renderScannerRows(document.getElementById('marketSheetContent'));
      return;
    }
    const retry = event.target.closest?.('[data-tool-runtime-retry="scanner"]');
    if (retry) { renderScanner(document.getElementById('marketSheetContent')); return; }
    const open = event.target.closest?.('[data-tool-open-ticker]');
    if (open) { openTicker(open.dataset.toolOpenTicker, false); return; }
    const openNews = event.target.closest?.('[data-tool-open-news]');
    if (openNews) { openTicker(openNews.dataset.toolOpenNews, true); return; }
    const newsSuggestion = event.target.closest?.('[data-news-open]');
    if (newsSuggestion) { openTicker(newsSuggestion.dataset.newsOpen, true); }
  }, true);

  document.addEventListener('input', event => {
    if (event.target?.id === 'marketCompareSearch') {
      const box = document.getElementById('marketCompareSuggestions');
      if (!box) return;
      box.innerHTML = compareCandidates(event.target.value).map(stock => `<button type="button" class="market-tool-runtime__suggestion" data-compare-add="${esc(stock.ticker)}"><span><strong>${esc(stock.ticker)}</strong><small>${esc(stock.name)}</small></span><small>${esc(stock.sector || '')}</small></button>`).join('');
    }
    if (event.target?.id === 'marketNewsSearch') {
      const box = document.getElementById('marketNewsSuggestions');
      if (!box) return;
      box.innerHTML = newsCandidates(event.target.value).map(stock => `<button type="button" class="market-tool-runtime__suggestion" data-news-open="${esc(stock.ticker)}"><span><strong>${esc(stock.ticker)}</strong><small>${esc(stock.name)}</small></span><small>Notícias ›</small></button>`).join('');
    }
  }, true);

  installStyles();
  window.VestraMarketAnalysisToolsRuntime = Object.freeze({ openTool, closeSheet, version:'1.1' });
})();