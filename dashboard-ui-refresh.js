/* Vestra Dashboard UI Refresh v1.4 — compact history + portfolio pulse + passive-income insight + mobile polish. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraDashboardUiRefreshStyle';
  const PULSE_ID = 'dashboardPortfolioPulseCard';
  const HISTORY_SUMMARY_ID = 'snapshotHistorySummary';
  const UPCOMING_TILE_ID = 'dashboardUpcomingDividendsTile';
  let historyOpen = false;
  let historyObserver = null;
  let healthObserver = null;

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

    const events = document.getElementById('dashboardWeeklyEventsCard');
    const hero = dashboard.querySelector('.card.hero');
    if (events) events.insertAdjacentElement('afterend', card);
    else if (hero) hero.insertAdjacentElement('afterend', card);
    else dashboard.prepend(card);
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
    const alert = document.getElementById('negReturnAlert');
    if (alert && !healthObserver) {
      healthObserver = new MutationObserver(() => queueMicrotask(renderPortfolioHealth));
      healthObserver.observe(alert, { childList: true, attributes: true, attributeFilter: ['style'] });
    }
  }

  function refresh() {
    ensureStyles();
    normalizeBottomNav();
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

  window.VestraDashboardUiRefresh = Object.freeze({ refresh, pulseMetrics, upcomingDividendEstimate, renderPortfolioHealth, version: '1.4' });
})();