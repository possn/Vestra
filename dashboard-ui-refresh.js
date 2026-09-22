/* Vestra Dashboard UI Refresh v1.6 — editorial daily brief + portfolio context. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraDashboardUiRefreshStyle';
  const PULSE_ID = 'dashboardPortfolioPulseCard';
  const HISTORY_SUMMARY_ID = 'snapshotHistorySummary';
  const UPCOMING_TILE_ID = 'dashboardUpcomingDividendsTile';
  const TODAY_HEADING_ID = 'dashboardTodayHeading';
  const PORTFOLIO_HEADING_ID = 'dashboardPortfolioHeading';
  const TODAY_BRIEF_ID = 'dashboardTodayBrief';
  let historyOpen = false;
  let historyObserver = null;
  let healthObserver = null;
  let todayObserver = null;
  let todayRenderQueued = false;

  const shared = window.VestraUtils;
  if (!shared || typeof shared.text !== 'function' || typeof shared.finiteOrNull !== 'function' ||
      typeof shared.parseLocalDay !== 'function' || typeof shared.formatMoney !== 'function' ||
      typeof shared.formatPercent !== 'function' || typeof shared.canonicalTicker !== 'function') {
    throw new Error('VestraDashboardUiRefresh requires VestraUtils presentation helpers');
  }
  const { text, finiteOrNull: num, parseLocalDay: parseDay, canonicalTicker } = shared;

  const dividendNormalization = window.VestraBrokerNormalization;
  if (!dividendNormalization || typeof dividendNormalization.getDividendNet !== 'function') {
    throw new Error('VestraDashboardUiRefresh requires VestraBrokerNormalization.getDividendNet');
  }
  const { getDividendNet } = dividendNormalization;

  function getState() {
    try { return (typeof state !== 'undefined' && state) ? state : null; }
    catch (_) { return null; }
  }

  function currency() {
    return text(getState()?.settings?.currency) || 'EUR';
  }

  function fmtMoney(value) {
    return shared.formatMoney(value, { currency: currency(), locale: 'pt-PT', maximumFractionDigits: 0 });
  }

  function fmtPct(value) {
    return shared.formatPercent(value, { locale: 'pt-PT', maximumFractionDigits: 1, minimumFractionDigits: 1, sign: true });
  }

  function historyRows() {
    const rows = Array.isArray(getState()?.history) ? getState().history : [];
    return rows.map(row => ({ ...row, _date: parseDay(row?.dateISO), _net: num(row?.net) }))
      .filter(row => row._date && row._net !== null)
      .sort((a, b) => a._date - b._date);
  }

  function nearestAtOrBefore(rows, target) {
    for (let i = rows.length - 1; i >= 0; i -= 1) {
      if (rows[i]._date <= target) return rows[i];
    }
    return null;
  }

  function changeVs(latest, base) {
    if (!latest || !base || !base._net) return null;
    return ((latest._net - base._net) / Math.abs(base._net)) * 100;
  }

  function pulseMetrics(now = new Date()) {
    const rows = historyRows();
    if (!rows.length) return { rows, latest: null, seven: null, thirty: null, drawdown90: null };
    const latest = rows[rows.length - 1];
    const d7 = new Date(latest._date); d7.setDate(d7.getDate() - 7);
    const d30 = new Date(latest._date); d30.setDate(d30.getDate() - 30);
    const d90 = new Date(latest._date); d90.setDate(d90.getDate() - 90);
    const b7 = nearestAtOrBefore(rows, d7);
    const b30 = nearestAtOrBefore(rows, d30);
    const recent = rows.filter(row => row._date >= d90);
    const peak = recent.length ? Math.max(...recent.map(row => row._net)) : latest._net;
    const drawdown90 = peak > 0 ? ((latest._net - peak) / peak) * 100 : null;
    return {
      rows,
      latest,
      seven: changeVs(latest, b7),
      thirty: changeVs(latest, b30),
      drawdown90,
    };
  }

  function assetTicker(asset) {
    return canonicalTicker(asset?.yahooTicker || asset?.ticker || asset?.symbol || '');
  }

  function dividendTicker(dividend) {
    const notes = text(dividend?.notes);
    const yahoo = /(?:^|·|\s)Yahoo=([^·\s]+)/i.exec(notes)?.[1];
    const ticker = /(?:^|·|\s)Ticker=([^·\s]+)/i.exec(notes)?.[1];
    return canonicalTicker(yahoo || ticker || dividend?.ticker || '');
  }

  function latestObservedPaymentFor(asset) {
    const s = getState();
    const dividends = Array.isArray(s?.dividends) ? s.dividends : [];
    const ticker = assetTicker(asset);
    const assetId = text(asset?.id);
    const assetName = text(asset?.name).toLowerCase();
    const rows = dividends.map(dividend => ({
      dividend,
      date: parseDay(dividend?.date),
      net: getDividendNet(dividend),
      ticker: dividendTicker(dividend),
    })).filter(row => {
      if (!row.date || row.net === null || row.net <= 0 || row.dividend?.isAdjustment) return false;
      if (assetId && text(row.dividend?.assetId) === assetId) return true;
      if (ticker && row.ticker === ticker) return true;
      return assetName && text(row.dividend?.assetName).toLowerCase() === assetName;
    }).sort((a, b) => b.date - a.date);
    if (!rows.length) return null;
    const latest = rows[0].date;
    const samePaymentWindow = rows.filter(row => Math.abs(row.date - latest) <= 3 * 86400000);
    return samePaymentWindow.reduce((sum, row) => sum + row.net, 0);
  }

  function upcomingDividendEstimate(now = new Date()) {
    const s = getState();
    const assets = Array.isArray(s?.assets) ? s.assets : [];
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const end = new Date(start); end.setDate(end.getDate() + 30);
    const seen = new Set();
    const upcoming = [];

    for (const asset of assets) {
      const payDate = parseDay(asset?._yahooDiv?.payDate);
      if (!payDate || payDate < start || payDate > end) continue;
      const key = assetTicker(asset) || text(asset?.id) || text(asset?.name).toLowerCase();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      upcoming.push({ asset, payDate, estimate: latestObservedPaymentFor(asset) });
    }

    const known = upcoming.filter(row => num(row.estimate) !== null && row.estimate > 0);
    const total = known.length ? known.reduce((sum, row) => sum + row.estimate, 0) : null;
    return { count: upcoming.length, knownCount: known.length, total, upcoming };
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'dashboard-ui-refresh.css?v=1.0';
    document.head.appendChild(link);
  }

  function pulseValueClass(value) {
    const n = num(value);
    return n > 0.005 ? ' is-up' : n < -0.005 ? ' is-down' : '';
  }

  function renderPulse() {
    const dashboard = document.getElementById('viewDashboard');
    if (!dashboard) return;
    const metrics = pulseMetrics();
    let card = document.getElementById(PULSE_ID);
    if (!card) {
      card = document.createElement('div');
      card.id = PULSE_ID;
      card.className = 'card dashboard-pulse-card';
    }
    const latest = metrics.latest;
    const dateLabel = latest ? new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short' }).format(latest._date).replace('.', '') : 'Sem histórico';
    const drawdown = metrics.drawdown90;
    const drawLabel = drawdown === null ? '—' : Math.abs(drawdown) < .05 ? 'No máximo' : fmtPct(drawdown);
    card.innerHTML = `
      <div class="dashboard-pulse-head">
        <div><div class="dashboard-pulse-kicker">Tendência</div><div class="dashboard-pulse-title">Pulso patrimonial</div></div>
        <div class="dashboard-pulse-date">${dateLabel}</div>
      </div>
      <div class="dashboard-pulse-grid">
        <div class="dashboard-pulse-metric"><div class="dashboard-pulse-label">7 dias</div><div class="dashboard-pulse-value${pulseValueClass(metrics.seven)}">${fmtPct(metrics.seven)}</div></div>
        <div class="dashboard-pulse-metric"><div class="dashboard-pulse-label">30 dias</div><div class="dashboard-pulse-value${pulseValueClass(metrics.thirty)}">${fmtPct(metrics.thirty)}</div></div>
        <div class="dashboard-pulse-metric"><div class="dashboard-pulse-label">Máximo 90d</div><div class="dashboard-pulse-value${pulseValueClass(drawdown)}">${drawLabel}</div></div>
      </div>
      <div class="dashboard-pulse-sub">Último património registado: ${latest ? fmtMoney(latest._net) : '—'} · calculado a partir dos snapshots locais.</div>`;

    const quick = dashboard.querySelector('.kpi-quick');
    if (quick) quick.insertAdjacentElement('afterend', card);
    else {
      const hero = dashboard.querySelector('.card.hero');
      if (hero) hero.insertAdjacentElement('afterend', card);
      else dashboard.prepend(card);
    }
  }

  function editorialHeading(id, kicker, title, copy) {
    let node = document.getElementById(id);
    if (!node) {
      node = document.createElement('header');
      node.id = id;
      node.className = 'dashboard-editorial-heading';
    }
    node.innerHTML = `<span class="dashboard-editorial-heading__kicker">${kicker}</span><h2>${title}</h2><p>${copy}</p>`;
    return node;
  }

  function ensureEditorialHierarchy() {
    const dashboard = document.getElementById('viewDashboard');
    if (!dashboard) return;

    const hero = dashboard.querySelector('.card.hero');
    const today = editorialHeading(
      TODAY_HEADING_ID,
      'EM 30 SEGUNDOS',
      'O que importa hoje',
      'Sentimento do mercado, eventos e notícias com impacto potencial — primeiro o sinal, depois o detalhe.'
    );
    if (hero && hero.nextElementSibling !== today) hero.insertAdjacentElement('afterend', today);

    const quick = dashboard.querySelector('.kpi-quick');
    const portfolio = editorialHeading(
      PORTFOLIO_HEADING_ID,
      'A TUA CARTEIRA',
      'O património em contexto',
      'Rendimento, tendência e evolução apresentados como uma leitura única, sem repetir métricas.'
    );
    if (quick && quick.previousElementSibling !== portfolio) quick.insertAdjacentElement('beforebegin', portfolio);
  }

  function todaySignal(label, value, detail = '') {
    const row = document.createElement('div');
    row.className = 'dashboard-today-brief__row';
    const kicker = document.createElement('span');
    kicker.className = 'dashboard-today-brief__label';
    kicker.textContent = label;
    const body = document.createElement('div');
    body.className = 'dashboard-today-brief__body';
    const strong = document.createElement('strong');
    strong.textContent = value;
    body.appendChild(strong);
    if (detail) {
      const small = document.createElement('small');
      small.textContent = detail;
      body.appendChild(small);
    }
    row.append(kicker, body);
    return row;
  }

  function renderTodayBrief() {
    const dashboard = document.getElementById('viewDashboard');
    const heading = document.getElementById(TODAY_HEADING_ID);
    if (!dashboard || !heading) return false;

    const sentiment = document.getElementById('vestraMarketSentimentCard');
    const score = text(sentiment?.querySelector('.dms-score')?.textContent).replace(/\s+/g, '');
    const sentimentLabel = text(sentiment?.querySelector('.dms-label')?.textContent);
    const sentimentReason = text(sentiment?.querySelector('.dms-head p')?.textContent);

    const event = document.querySelector('#dashboardWeeklyEventsCard .weekly-event');
    const eventDay = text(event?.querySelector('.weekly-event__day')?.textContent);
    const eventTitle = text(event?.querySelector('.weekly-event__ticker')?.textContent);
    const eventType = text(event?.querySelector('.weekly-event__type')?.textContent);

    const news = document.querySelector('#vestraDailyNewsCard .vestra-daily-news-item');
    const newsTitle = text(news?.querySelector('strong')?.textContent);
    const newsBadge = text(news?.querySelector('.vestra-daily-news-badge')?.textContent);

    const signature = [score, sentimentLabel, sentimentReason, eventDay, eventTitle, eventType, newsTitle, newsBadge].join('|');
    let brief = document.getElementById(TODAY_BRIEF_ID);
    if (!brief) {
      brief = document.createElement('section');
      brief.id = TODAY_BRIEF_ID;
      brief.className = 'dashboard-today-brief';
    }
    if (brief.dataset.signature !== signature) {
      brief.replaceChildren();
      const head = document.createElement('div');
      head.className = 'dashboard-today-brief__head';
      const copy = document.createElement('div');
      copy.innerHTML = '<span>LEITURA DO DIA</span><strong>Três sinais para orientar a leitura</strong>';
      head.appendChild(copy);
      brief.appendChild(head);

      const rows = document.createElement('div');
      rows.className = 'dashboard-today-brief__rows';
      if (score || sentimentLabel) rows.appendChild(todaySignal('MERCADO', [score, sentimentLabel].filter(Boolean).join(' · '), sentimentReason));
      if (eventTitle) rows.appendChild(todaySignal('PRÓXIMO EVENTO', [eventDay, eventTitle].filter(Boolean).join(' · '), eventType));
      if (newsTitle) rows.appendChild(todaySignal(newsBadge || 'NOTÍCIA', newsTitle));
      if (!rows.childElementCount) rows.appendChild(todaySignal('A CARREGAR', 'A recolher os sinais do dia…', 'O resumo aparece assim que sentimento, eventos ou notícias estiverem disponíveis.'));
      brief.appendChild(rows);
      brief.dataset.signature = signature;
    }
    if (heading.nextElementSibling !== brief) heading.insertAdjacentElement('afterend', brief);
    return true;
  }

  function queueTodayBrief() {
    if (todayRenderQueued) return;
    todayRenderQueued = true;
    requestAnimationFrame(() => {
      todayRenderQueued = false;
      renderTodayBrief();
    });
  }

  function renderUpcomingDividendTile(now = new Date()) {
    const grid = document.querySelector('#viewDashboard .kpi-quick__grid');
    if (!grid) return;
    let tile = document.getElementById(UPCOMING_TILE_ID);
    if (!tile) {
      tile = document.createElement('div');
      tile.id = UPCOMING_TILE_ID;
      tile.className = 'kpi-quick__cell dashboard-upcoming-dividends';
      grid.appendChild(tile);
    }
    const estimate = upcomingDividendEstimate(now);
    const value = estimate.total !== null ? fmtMoney(estimate.total) : '—';
    let sub = 'sem pagamentos previstos';
    if (estimate.count > 0 && estimate.total !== null) sub = `${estimate.count} ${estimate.count === 1 ? 'pagamento previsto' : 'pagamentos previstos'}`;
    else if (estimate.count > 0) sub = `${estimate.count} ${estimate.count === 1 ? 'pagamento sem estimativa' : 'pagamentos sem estimativa'}`;
    tile.innerHTML = `<div class="kpi-quick__k">Próximos 30 dias</div><div class="kpi-quick__v">${value}</div><div class="kpi-quick__s">${sub}</div>`;
  }

  function renderPortfolioHealth() {
    const alert = document.getElementById('negReturnAlert');
    if (!alert || alert.style.display === 'none') return;
    let twr = null;
    try { twr = typeof calcTWR === 'function' ? calcTWR() : null; } catch (_) {}
    const annual = num(twr?.annualised);
    if (annual === null || annual >= -5) return;
    if (alert.dataset.dashboardHealthAnnual === String(annual) && alert.querySelector('.dashboard-health-card__body')) return;
    alert.dataset.dashboardHealthAnnual = String(annual);
    alert.className = 'dashboard-health-card';
    alert.innerHTML = `
      <div class="dashboard-health-card__body">
        <div class="dashboard-health-card__head">
          <div><div class="dashboard-health-card__kicker">Saúde do património</div><div class="dashboard-health-card__title">Retorno real sob pressão</div></div>
          <div class="dashboard-health-card__status">Atenção</div>
        </div>
        <div class="dashboard-health-card__metric">TWR anualizado ${fmtPct(annual)}/ano</div>
        <div class="dashboard-health-card__sub">Abaixo da inflação</div>
        <div class="dashboard-health-card__copy">O portefólio está a perder valor em termos reais. Usa esta leitura como sinal para rever alocação, custos e posições com pior contribuição.</div>
      </div>`;
  }

  function historySummaryText(rows) {
    if (!rows.length) return 'Ainda sem registos';
    const latest = rows[rows.length - 1];
    const date = new Intl.DateTimeFormat('pt-PT', { day: 'numeric', month: 'short' }).format(latest._date).replace('.', '');
    return `${date} · ${fmtMoney(latest._net)} · ${rows.length} registos`;
  }

  function syncHistoryCompact() {
    const table = document.getElementById('snapshotTable');
    if (!table) return;
    const card = table.closest('.card');
    if (!card) return;
    let summary = document.getElementById(HISTORY_SUMMARY_ID);
    if (!summary) {
      summary = document.createElement('div');
      summary.id = HISTORY_SUMMARY_ID;
      summary.className = 'snapshot-history-summary';
      table.insertAdjacentElement('beforebegin', summary);
    }
    const rows = historyRows();
    summary.innerHTML = `<div class="snapshot-history-summary__main"><div class="snapshot-history-summary__title">Histórico diário</div><div class="snapshot-history-summary__sub">${historySummaryText(rows)}</div></div><button type="button" class="snapshot-history-summary__btn">${historyOpen ? 'Fechar' : `Ver histórico${rows.length ? ` (${rows.length})` : ''}`}</button>`;
    const button = summary.querySelector('button');
    if (button) button.addEventListener('click', () => {
      historyOpen = !historyOpen;
      table.hidden = !historyOpen;
      const clear = document.getElementById('btnTrendClear');
      if (clear) clear.style.visibility = historyOpen ? '' : 'hidden';
      syncHistoryCompact();
    }, { once: true });
    table.hidden = !historyOpen;
    const clear = document.getElementById('btnTrendClear');
    if (clear) clear.style.visibility = historyOpen ? '' : 'hidden';
  }

  function normalizeBottomNav() {
    const icon = document.querySelector('#navCashflow .navico');
    if (icon) icon.textContent = '↕︎';
  }

  function installObserver() {
    const table = document.getElementById('snapshotTable');
    if (table && !historyObserver) {
      historyObserver = new MutationObserver(() => syncHistoryCompact());
      historyObserver.observe(table, { childList: true, subtree: true });
    }
    const dashboard = document.getElementById('viewDashboard');
    if (dashboard && !todayObserver) {
      todayObserver = new MutationObserver(queueTodayBrief);
      todayObserver.observe(dashboard, { childList: true, subtree: true, characterData: true });
    }
    const alert = document.getElementById('negReturnAlert');
    if (alert && !healthObserver) {
      healthObserver = new MutationObserver(() => queueMicrotask(renderPortfolioHealth));
      healthObserver.observe(alert, { childList: true, attributes: true, attributeFilter: ['style'] });
    }
  }

  function refresh() {
    ensureStyles();
    normalizeBottomNav();
    ensureEditorialHierarchy();
    renderTodayBrief();
    renderPulse();
    renderUpcomingDividendTile();
    renderPortfolioHealth();
    syncHistoryCompact();
    installObserver();
  }

  function boot() {
    refresh();
    window.addEventListener('vestra:app-ready', refresh);
    window.addEventListener('vestra:market-ready', refresh);
    document.addEventListener('click', event => {
      if (event.target?.closest?.('[data-view="dashboard"], [data-view="cashflow"]')) setTimeout(refresh, 60);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  window.VestraDashboardUiRefresh = Object.freeze({ refresh, pulseMetrics, upcomingDividendEstimate, renderPortfolioHealth, ensureEditorialHierarchy, version: '1.6' });
})();