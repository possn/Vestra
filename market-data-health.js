/* Vestra Market Data Health v1.1 — lightweight operational visibility from published diagnostics. */
(() => {
  'use strict';

  const DATA_URLS = Object.freeze({
    guard: './data/coverage_guard.json',
    learned: './data/learned_tickers.json',
  });

  const text = value => String(value ?? '').trim();
  const number = value => Number.isFinite(Number(value)) ? Number(value) : null;

  async function loadJson(url) {
    try {
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) return null;
      return await response.json();
    } catch (_) {
      return null;
    }
  }

  function parseDate(value) {
    const time = Date.parse(text(value));
    return Number.isFinite(time) ? new Date(time) : null;
  }

  function ageMinutes(date, now = new Date()) {
    if (!date) return null;
    return Math.max(0, Math.round((now.getTime() - date.getTime()) / 60000));
  }

  function ageLabel(minutes) {
    if (minutes == null) return 'idade desconhecida';
    if (minutes < 2) return 'agora';
    if (minutes < 60) return `há ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `há ${hours} h`;
    const days = Math.floor(hours / 24);
    return `há ${days} d`;
  }

  function formatDate(date) {
    if (!date) return '—';
    try {
      return new Intl.DateTimeFormat('pt-PT', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      }).format(date);
    } catch (_) {
      return date.toISOString();
    }
  }

  function deriveState(guard, minutes) {
    if (!guard) return { key: 'unknown', label: 'Estado dos dados indisponível' };
    if (guard.ok === false || number(guard.violation_count) > 0) return { key: 'bad', label: 'Atenção aos dados' };
    if (minutes != null && minutes > 240) return { key: 'stale', label: 'Dados antigos' };
    return { key: 'ok', label: 'Dados atualizados' };
  }

  function model(guard, learned, now = new Date()) {
    const generatedAt = parseDate(guard?.generated_at);
    const minutes = ageMinutes(generatedAt, now);
    const rows = number(guard?.rows_checked);
    const violations = number(guard?.violation_count);
    const learnedCount = number(learned?.count) ?? (Array.isArray(learned?.rows) ? learned.rows.length : null);
    return {
      generatedAt,
      ageMinutes: minutes,
      age: ageLabel(minutes),
      state: deriveState(guard, minutes),
      rows,
      violations,
      learnedCount,
      learnedSource: text(learned?.source) || '—',
    };
  }

  function ensureStyle() {
    if (document.getElementById('vestra-data-health-style')) return;
    const style = document.createElement('style');
    style.id = 'vestra-data-health-style';
    style.textContent = `
      .vestra-data-health{margin:0 0 10px;border:1px solid var(--line);border-radius:13px;background:var(--card);overflow:hidden}
      .vestra-data-health summary{list-style:none;display:flex;align-items:center;gap:8px;padding:9px 12px;cursor:pointer;font-size:11px;font-weight:750;color:var(--text2)}
      .vestra-data-health summary::-webkit-details-marker{display:none}
      .vestra-data-health__dot{width:7px;height:7px;border-radius:999px;background:#7c8a8e;flex:0 0 auto}
      .vestra-data-health[data-state="ok"] .vestra-data-health__dot{background:#1a9b73}
      .vestra-data-health[data-state="stale"] .vestra-data-health__dot{background:#c8902f}
      .vestra-data-health[data-state="bad"] .vestra-data-health__dot{background:#c65151}
      .vestra-data-health__label{color:var(--text);font-weight:800}
      .vestra-data-health__age{margin-left:auto;font-weight:650}
      .vestra-data-health__chev{font-size:9px;transition:transform .15s ease}
      .vestra-data-health[open] .vestra-data-health__chev{transform:rotate(180deg)}
      .vestra-data-health__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding:0 12px 12px}
      .vestra-data-health__item{padding:9px 10px;border-radius:10px;background:var(--card2)}
      .vestra-data-health__item small{display:block;font-size:9px;letter-spacing:.04em;text-transform:uppercase;color:var(--text2);margin-bottom:3px}
      .vestra-data-health__item strong{display:block;font-size:12px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      @media (min-width:760px){.vestra-data-health__grid{grid-template-columns:repeat(5,minmax(0,1fr))}}
    `;
    document.head.appendChild(style);
  }

  function render(view, data) {
    let host = document.getElementById('vestraDataHealth');
    if (!host) {
      host = document.createElement('details');
      host.id = 'vestraDataHealth';
      host.className = 'vestra-data-health';
      host.dataset.vestraDataHealth = 'true';
      view.prepend(host);
    }
    host.dataset.state = data.state.key;
    host.innerHTML = `
      <summary aria-label="Estado operacional dos dados Vestra">
        <span class="vestra-data-health__dot" aria-hidden="true"></span>
        <span class="vestra-data-health__label">${data.state.label}</span>
        <span class="vestra-data-health__age">${data.age}</span>
        <span class="vestra-data-health__chev" aria-hidden="true">⌄</span>
      </summary>
      <div class="vestra-data-health__grid">
        <div class="vestra-data-health__item"><small>Último build</small><strong>${formatDate(data.generatedAt)}</strong></div>
        <div class="vestra-data-health__item"><small>Universo verificado</small><strong>${data.rows == null ? '—' : new Intl.NumberFormat('pt-PT').format(data.rows)}</strong></div>
        <div class="vestra-data-health__item"><small>Coverage guard</small><strong>${data.violations == null ? data.state.label : `${data.violations} violações`}</strong></div>
        <div class="vestra-data-health__item"><small>Tickers aprendidos</small><strong>${data.learnedCount == null ? '—' : data.learnedCount}</strong></div>
        <div class="vestra-data-health__item"><small>Origem aprendida</small><strong>${data.learnedSource}</strong></div>
      </div>`;
  }

  async function refresh() {
    const view = document.getElementById('viewMarket');
    if (!view) return null;
    ensureStyle();
    const [guard, learned] = await Promise.all([
      loadJson(DATA_URLS.guard),
      loadJson(DATA_URLS.learned),
    ]);
    const data = model(guard, learned);
    render(view, data);
    return data;
  }

  function start() {
    refresh();
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) refresh();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();

  window.VestraMarketDataHealth = Object.freeze({ version: '1.1', refresh, model, ageLabel, deriveState });
})();
