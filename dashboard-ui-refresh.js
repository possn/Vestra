/* Vestra Dashboard UI Refresh v1.0 — compact history + portfolio pulse + mobile polish. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraDashboardUiRefreshStyle';
  const PULSE_ID = 'dashboardPortfolioPulseCard';
  const HISTORY_SUMMARY_ID = 'snapshotHistorySummary';
  let historyOpen = false;
  let historyObserver = null;

  const text = value => String(value ?? '').trim();
  const num = value => {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };

  function getState() {
    try { return (typeof state !== 'undefined' && state) ? state : null; }
    catch (_) { return null; }
  }

  function currency() {
    return text(getState()?.settings?.currency) || 'EUR';
  }

  function fmtMoney(value) {
    const n = num(value);
    if (n === null) return '—';
    try { return new Intl.NumberFormat('pt-PT', { style: 'currency', currency: currency(), maximumFractionDigits: 0 }).format(n); }
    catch (_) { return `${Math.round(n).toLocaleString('pt-PT')} ${currency()}`; }
  }

  function fmtPct(value) {
    const n = num(value);
    if (n === null) return '—';
    const sign = n > 0 ? '+' : '';
    return `${sign}${n.toLocaleString('pt-PT', { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;
  }

  function parseDay(value) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(text(value));
    if (!m) return null;
    const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return Number.isNaN(d.getTime()) ? null : d;
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

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .dashboard-pulse-card{overflow:hidden;background:linear-gradient(155deg,rgba(255,255,255,.92),rgba(23,123,120,.035));border-color:rgba(23,123,120,.13)!important}
      .dashboard-pulse-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:13px}
      .dashboard-pulse-kicker{font-size:10px;font-weight:850;letter-spacing:.55px;text-transform:uppercase;color:#177B78;margin-bottom:3px}
      .dashboard-pulse-title{font-size:16px;font-weight:850;letter-spacing:-.25px;color:var(--text,#17212b)}
      .dashboard-pulse-date{font-size:10px;color:var(--muted,#64748b);padding-top:2px;white-space:nowrap}
      .dashboard-pulse-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
      .dashboard-pulse-metric{padding:11px 10px;border-radius:14px;background:rgba(255,255,255,.62);border:1px solid rgba(15,23,42,.055)}
      .dashboard-pulse-label{font-size:10px;font-weight:750;color:var(--muted,#64748b);margin-bottom:4px}
      .dashboard-pulse-value{font-size:16px;font-weight:900;letter-spacing:-.25px;color:var(--text,#17212b)}
      .dashboard-pulse-value.is-up{color:#14756f}.dashboard-pulse-value.is-down{color:#b24e56}
      .dashboard-pulse-sub{margin-top:9px;font-size:10px;color:var(--muted,#64748b)}

      .snapshot-history-summary{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:12px;padding:11px 12px;border-radius:14px;background:rgba(23,123,120,.045);border:1px solid rgba(23,123,120,.09)}
      .snapshot-history-summary__main{min-width:0}
      .snapshot-history-summary__title{font-size:12px;font-weight:850;color:var(--text,#17212b);margin-bottom:2px}
      .snapshot-history-summary__sub{font-size:11px;color:var(--muted,#64748b);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .snapshot-history-summary__btn{appearance:none;border:0;background:rgba(23,123,120,.10);color:#126e6a;font-size:11px;font-weight:850;border-radius:999px;padding:8px 10px;white-space:nowrap}
      #snapshotTable[hidden]{display:none!important}

      #viewDashboard .card:not(.hero),#viewCashflow .card{border-color:rgba(31,56,66,.10);box-shadow:0 3px 14px rgba(28,45,54,.035)}
      #viewDashboard .card,#viewCashflow .card{border-radius:20px}
      .bottomnav{background:rgba(248,250,248,.90)!important;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-top-color:rgba(31,56,66,.08)!important}
      .bottomnav .navbtn{border-radius:16px;transition:transform .18s ease,background .18s ease,color .18s ease}
      .bottomnav .navbtn--active{background:rgba(23,123,120,.075);transform:translateY(-1px)}
      .bottomnav .navico{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI Symbol",sans-serif;font-weight:650}
      @media(max-width:560px){
        .dashboard-pulse-grid{gap:6px}.dashboard-pulse-metric{padding:10px 8px}.dashboard-pulse-value{font-size:15px}
        #viewDashboard .card,#viewCashflow .card{border-radius:18px}
      }
    `;
    document.head.appendChild(style);
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
    if (!table || historyObserver) return;
    historyObserver = new MutationObserver(() => syncHistoryCompact());
    historyObserver.observe(table, { childList: true, subtree: true });
  }

  function refresh() {
    ensureStyles();
    normalizeBottomNav();
    renderPulse();
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

  window.VestraDashboardUiRefresh = Object.freeze({ refresh, pulseMetrics, version: '1.0' });
})();
