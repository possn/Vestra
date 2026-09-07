/* Vestra Market stock theme discovery + tool hierarchy v1.2 */
(() => {
  'use strict';

  const THEME_DEFS = [
    ['technology', 'Tecnologia', s => s.sector === 'Technology'],
    ['semiconductors', 'Semicondutores', s => /semiconductor|chip|microprocessor|integrated circuit/i.test(s.text)],
    ['ai_robotics', 'IA & Robótica', s => /artificial intelligence|machine learning|robotics|robotic|automation/i.test(s.text)],
    ['cybersecurity', 'Cibersegurança', s => /cybersecurity|cyber security|information security|network security/i.test(s.text)],
    ['healthcare', 'Saúde', s => s.sector === 'Healthcare'],
    ['biotech', 'Biotecnologia', s => /biotech|biotechnology|biopharma|biopharmaceutical/i.test(s.text)],
    ['financials', 'Financeiro', s => s.sector === 'Financial Services'],
    ['industrials', 'Indústria', s => s.sector === 'Industrials'],
    ['defense', 'Defesa & Aeroespacial', s => /aerospace|defen[cs]e|military/i.test(s.text)],
    ['energy', 'Energia', s => s.sector === 'Energy'],
    ['clean_energy', 'Energia limpa', s => /renewable|solar|wind energy|clean energy|hydrogen|fuel cell/i.test(s.text)],
    ['nuclear', 'Nuclear & Urânio', s => /nuclear|uranium/i.test(s.text)],
    ['water', 'Água', s => /water|wastewater|desalination/i.test(s.text)],
    ['agriculture', 'Agricultura', s => /agricultur|farm|fertili[sz]er|crop|seed|grain/i.test(s.text)],
    ['consumer', 'Consumo', s => /^Consumer /.test(s.sector)],
    ['real_estate', 'Imobiliário', s => s.sector === 'Real Estate' || /reit|real estate/i.test(s.text)],
    ['utilities', 'Utilities', s => s.sector === 'Utilities'],
    ['materials', 'Materiais', s => s.sector === 'Basic Materials'],
  ];

  const WATCH_KEY = 'vestra-market-watchlist-v1';
  let selectedTheme = '';
  let stockBrowserActive = false;
  let observer = null;
  let renderQueued = false;

  const text = value => String(value ?? '').trim();
  const number = value => {
    if (value === null || value === undefined || value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };
  const escapeHtml = value => text(value).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));

  function isFund(stock) {
    const q = text(stock?.quote_type).toUpperCase();
    const name = text(stock?.name).toUpperCase();
    return q === 'ETF' || q === 'MUTUALFUND' || /\bETF\b|ISHARES|VANGUARD|XTRACKERS|SPDR|LYXOR|AMUNDI|WISDOMTREE|INVESCO/.test(name);
  }

  function normalizedStock(stock) {
    return {
      stock,
      sector: text(stock?.sector),
      text: [stock?.ticker, stock?.name, stock?.sector, stock?.industry, stock?.category, stock?.theme, stock?.style, stock?.description, stock?.long_business_summary, stock?.business_summary].map(text).join(' '),
    };
  }

  function stocks() {
    const rows = window.VestraMarketStaticUniverse?.getStocks?.();
    return Array.isArray(rows) ? rows.filter(stock => !isFund(stock) && text(stock?.ticker)) : [];
  }

  function watchedTickers() {
    try {
      const rows = JSON.parse(localStorage.getItem(WATCH_KEY) || '[]');
      return new Set((Array.isArray(rows) ? rows : []).map(x => text(x).toUpperCase()).filter(Boolean));
    } catch (_) {
      return new Set();
    }
  }

  function scoreClass(score) {
    const value = number(score);
    return value == null ? 'market-score--soft' : value >= 70 ? '' : value >= 55 ? 'market-score--soft' : 'market-score--risk';
  }

  function rowHtml(stock, watched) {
    const ticker = text(stock?.ticker);
    const score = number(stock?.score);
    const meta = [text(stock?.sector), text(stock?.industry)].filter(Boolean).join(' · ');
    const isWatched = watched.has(ticker.toUpperCase());
    return `<div class="market-row" data-market-ticker="${escapeHtml(ticker)}">
      <div>
        <div class="market-row__title"><span class="market-row__ticker">${escapeHtml(ticker)}</span><span class="market-row__name">${escapeHtml(stock?.name || '')}</span></div>
        <div class="market-row__meta">${escapeHtml(meta || 'Empresa')}</div>
      </div>
      <div class="market-row__end">
        <button class="market-watch ${isWatched ? 'is-active' : ''}" data-market-watch="${escapeHtml(ticker)}" aria-label="${isWatched ? 'Remover da lista' : 'Guardar para acompanhar'}">${isWatched ? '★' : '☆'}</button>
        <div class="market-score ${scoreClass(score)}">${score == null ? '—' : Math.round(score)}</div>
      </div>
    </div>`;
  }

  function availableThemes(rows) {
    const normalized = rows.map(normalizedStock);
    return THEME_DEFS.map(([key, label, match]) => ({
      key,
      label,
      count: normalized.reduce((sum, item) => sum + (match(item) ? 1 : 0), 0),
      match,
    })).filter(theme => theme.count > 0);
  }

  function isStocksMode() { return stockBrowserActive; }

  function hasSearch() {
    return Boolean(text(document.getElementById('marketSearch')?.value));
  }

  function renderStockThemes() {
    const root = document.getElementById('marketPrimary');
    if (!root || !isStocksMode() || hasSearch()) return;
    const rows = stocks();
    if (!rows.length) return;

    const themes = availableThemes(rows);
    if (!selectedTheme) {
      if (root.querySelector('.market-stock-theme-grid')) return;
      root.innerHTML = `<section class="market-section market-stock-discovery">
        <div class="market-section__head">
          <div><h3>Escolher ações por tema</h3><p>Escolhe a área que queres explorar. Depois mostramos as empresas desse tema, ordenadas pelo Score Vestra já existente.</p></div>
          <span class="market-data-age">${rows.length} ações</span>
        </div>
        <div class="market-stock-theme-grid" role="group" aria-label="Temas de ações">
          ${themes.map(theme => `<button type="button" class="market-stock-theme" data-market-stock-theme="${escapeHtml(theme.key)}"><strong>${escapeHtml(theme.label)}</strong><span>${theme.count} ${theme.count === 1 ? 'empresa' : 'empresas'}</span></button>`).join('')}
        </div>
      </section>`;
      return;
    }

    const theme = themes.find(item => item.key === selectedTheme);
    if (!theme) {
      selectedTheme = '';
      renderStockThemes();
      return;
    }
    if (root.querySelector(`.market-stock-results[data-stock-theme="${CSS.escape(selectedTheme)}"]`)) return;

    const matches = rows.map(normalizedStock)
      .filter(theme.match)
      .map(item => item.stock)
      .sort((a, b) => {
        const as=number(a?.score), bs=number(b?.score);
        if(as==null && bs!=null) return 1;
        if(bs==null && as!=null) return -1;
        return (bs||0)-(as||0) || text(a?.name).localeCompare(text(b?.name));
      });
    const visible = matches.slice(0, 100);
    const watched = watchedTickers();

    root.innerHTML = `<section class="market-section market-stock-discovery market-stock-results" data-stock-theme="${escapeHtml(selectedTheme)}">
      <div class="market-section__head">
        <div><h3>${escapeHtml(theme.label)}</h3><p>Universo temático completo disponível. Empresas sem Score também aparecem; o Score continua separado e não é inventado.</p></div>
        <button type="button" class="market-stock-change-theme" data-market-stock-theme="">Mudar tema</button>
      </div>
      <div class="market-list">${visible.length ? visible.map(stock => rowHtml(stock, watched)).join('') : '<div class="market-empty">Sem empresas com Score disponível neste tema.</div>'}</div>
      ${matches.length > visible.length ? `<div class="market-stock-count">A mostrar ${visible.length} de ${matches.length} empresas</div>` : ''}
    </section>`;
  }

  function queueRender() {
    if (renderQueued) return;
    renderQueued = true;
    queueMicrotask(() => {
      renderQueued = false;
      renderStockThemes();
    });
  }

  function promoteTools() {
    const old = document.querySelector('details.market-tools');
    const marketApp = document.getElementById('marketApp');
    const portfolioAccess = marketApp?.querySelector('.market-portfolio-access');
    if (!old || !marketApp || document.querySelector('.market-analysis-tools')) return;

    const buttons = [...old.querySelectorAll('[data-market-tool]')];
    const wanted = ['compare', 'scanner', 'theses', 'news'];
    const byTool = new Map(buttons.map(button => [button.dataset.marketTool, button]));
    const section = document.createElement('section');
    section.className = 'market-analysis-tools';
    section.innerHTML = '<div class="market-analysis-tools__head"><div><strong>Ferramentas de análise</strong><small>Comparar, rastrear e acompanhar sem ir ao fim da página.</small></div></div><div class="market-analysis-tools__grid"></div>';
    const grid = section.querySelector('.market-analysis-tools__grid');
    wanted.forEach(tool => {
      const button = byTool.get(tool);
      if (!button) return;
      if (tool === 'compare') button.classList.add('market-tool-btn--primary');
      grid.appendChild(button);
    });
    old.remove();
    if (portfolioAccess) marketApp.insertBefore(section, portfolioAccess);
    else marketApp.insertBefore(section, document.getElementById('marketPrimary'));
  }

  function installIdeasAndStocksModes() {
    const ideas = document.querySelector('[data-market-mode="discover"]');
    if (!ideas) return;
    const ideasLabel = ideas.querySelector('strong');
    if (ideasLabel) ideasLabel.textContent = 'Ideias';
    if (document.querySelector('[data-market-stock-browser]')) return;
    const stocksButton = ideas.cloneNode(true);
    stocksButton.removeAttribute('data-market-mode');
    stocksButton.dataset.marketStockBrowser = '1';
    stocksButton.classList.remove('is-active');
    const label = stocksButton.querySelector('strong');
    if (label) label.textContent = 'Ações';
    ideas.insertAdjacentElement('afterend', stocksButton);
  }

  function setModeVisual(activeButton) {
    document.querySelectorAll('[data-market-mode], [data-market-stock-browser]').forEach(button => {
      button.classList.toggle('is-active', button === activeButton);
    });
  }

  function installStyles() {
    if (document.getElementById('vestraStockThemesToolsStyles')) return;
    const style = document.createElement('style');
    style.id = 'vestraStockThemesToolsStyles';
    style.textContent = `
      .market-stock-theme-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:4px}
      .market-stock-theme{min-width:0;border:1px solid var(--line);background:var(--card2);color:var(--text);border-radius:16px;padding:12px;text-align:left;cursor:pointer}
      .market-stock-theme strong{display:block;font-size:12px;line-height:1.25}
      .market-stock-theme span{display:block;margin-top:4px;color:var(--muted);font-size:10px;font-weight:700}
      .market-stock-theme:active{transform:scale(.985)}
      .market-stock-change-theme{flex:0 0 auto;border:1px solid var(--line);background:var(--card2);color:var(--text2);border-radius:999px;padding:7px 10px;font:inherit;font-size:10px;font-weight:800;cursor:pointer}
      .market-stock-count{text-align:center;color:var(--muted);font-size:10px;font-weight:700;padding:10px 0 2px}
      .market-analysis-tools{border:1px solid var(--line);background:var(--card);border-radius:18px;padding:12px;box-shadow:none}
      .market-analysis-tools__head{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;margin-bottom:9px}
      .market-analysis-tools__head strong{display:block;font-size:13px}
      .market-analysis-tools__head small{display:block;color:var(--muted);font-size:10px;line-height:1.3;margin-top:2px}
      .market-analysis-tools__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
      .market-analysis-tools .market-tool-btn{min-height:58px;padding:10px 11px;border-radius:14px}
      .market-analysis-tools .market-tool-btn--primary{background:linear-gradient(145deg,var(--card2),rgba(32,129,126,.10));border-color:rgba(32,129,126,.32)}
      .market-analysis-tools .market-tool-btn--primary::before{content:'↔ ';color:var(--vio)}
      @media(min-width:640px){.market-stock-theme-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.market-analysis-tools__grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
    `;
    document.head.appendChild(style);
  }

  function installObserver() {
    const root = document.getElementById('marketPrimary');
    if (!root || observer) return;
    observer = new MutationObserver(queueRender);
    observer.observe(root, { childList: true });
  }

  function boot() {
    installStyles();
    installIdeasAndStocksModes();
    promoteTools();
    installObserver();
    queueRender();
  }

  document.addEventListener('click', event => {
    const theme = event.target.closest?.('[data-market-stock-theme]');
    if (theme) {
      selectedTheme = theme.dataset.marketStockTheme || '';
      document.getElementById('marketPrimary')?.querySelector('.market-stock-discovery')?.remove();
      queueRender();
      return;
    }
    const stocksMode = event.target.closest?.('[data-market-stock-browser]');
    if (stocksMode) {
      event.preventDefault();
      stockBrowserActive = true;
      selectedTheme = '';
      setModeVisual(stocksMode);
      queueRender();
      return;
    }
    const mode = event.target.closest?.('[data-market-mode]');
    if (mode) {
      stockBrowserActive = false;
      selectedTheme = '';
      setModeVisual(mode);
      if (mode.dataset.marketMode === 'discover') setTimeout(queueRender, 0);
    }
  });

  document.addEventListener('input', event => {
    if (event.target?.id === 'marketSearch') setTimeout(queueRender, 0);
  });
  window.addEventListener('vestra:market-ready', queueRender);

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  window.VestraMarketStockThemesTools = Object.freeze({
    render: queueRender,
    getSelectedTheme: () => selectedTheme,
    version: '1.2',
  });
})();