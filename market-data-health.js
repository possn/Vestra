/* Vestra Market Data Health v1.2 — distinguish published dataset health from live quote freshness. */
(() => {
  'use strict';

  const DATA_URLS = Object.freeze({
    guard: './data/coverage_guard.json',
    learned: './data/learned_tickers.json',
  });
  const QUOTE_STALE_MS = 60 * 1000;

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
    if (value instanceof Date && Number.isFinite(value.getTime())) return value;
    const time = typeof value === 'number' ? value : Date.parse(text(value));
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
    if (minutes != null && minutes > 240) return { key: 'stale', label: 'Dados de referência antigos' };
    return { key: 'ok', label: 'Dados de referência atualizados' };
  }

  function deriveQuoteState(report, quoteDate, now = new Date()) {
    if (!quoteDate) return { key: 'unknown', label: 'Cotações ainda não atualizadas' };
    const updated = number(report?.updated) ?? 0;
    const failed = number(report?.failed) ?? 0;
    if (failed > 0 && updated <= 0) return { key: 'bad', label: 'Falha nas cotações' };
    if (failed > 0) return { key: 'partial', label: 'Cotações parciais' };
    if (Math.max(0, now.getTime() - quoteDate.getTime()) > QUOTE_STALE_MS) return { key: 'stale', label: 'Cotações a atualizar' };
    return { key: 'ok', label: 'Cotações atualizadas' };
  }

  function deriveOverallState(referenceState, quoteState) {
    if (referenceState.key === 'bad' || quoteState.key === 'bad') return { key: 'bad', label: 'Atenção ao mercado' };
    if (quoteState.key === 'partial') return { key: 'stale', label: 'Cotações parcialmente atualizadas' };
    if (referenceState.key === 'stale' || quoteState.key === 'stale') return { key: 'stale', label: 'Atualização pendente' };
    if (referenceState.key === 'ok' && quoteState.key === 'ok') return { key: 'ok', label: 'Mercado atualizado' };
    if (referenceState.key === 'ok') return { key: 'ok', label: 'Dados de referência atualizados' };
    return { key: 'unknown', label: 'Estado do mercado indisponível' };
  }

  function model(guard, learned, now = new Date(), quoteReport = null, quoteTs = null) {
    const generatedAt = parseDate(guard?.generated_at);
    const minutes = ageMinutes(generatedAt, now);
    const rows = number(guard?.rows_checked);
    const violations = number(guard?.violation_count);
    const learnedCount = number(learned?.count) ?? (Array.isArray(learned?.rows) ? learned.rows.length : null);
    const quoteDate = parseDate(quoteTs) || parseDate(quoteReport?.ts);
    const quoteMinutes = ageMinutes(quoteDate, now);
    const quoteState = deriveQuoteState(quoteReport, quoteDate, now);
    const referenceState = deriveState(guard, minutes);
    return {
      generatedAt,
      ageMinutes: minutes,
      age: ageLabel(minutes),
      state: referenceState,
      overallState: deriveOverallState(referenceState, quoteState),
      rows,
      violations,
      learnedCount,
      learnedSource: text(learned?.source) || '—',
      quoteDate,
      quoteAgeMinutes: quoteMinutes,
      quoteAge: ageLabel(quoteMinutes),
      quoteState,
      quoteUpdated: number(quoteReport?.updated),
      quoteFailed: number(quoteReport?.failed),
      quoteSkipped: number(quoteReport?.skipped),
      quoteDurationMs: number(quoteReport?.durationMs),
    };
  }

  function runtimeQuoteSnapshot() {
    try {
      const settings = window.state?.settings;
      if (!settings) return null;
      return {
        report: settings.lastQuoteRefresh || null,
        ts: settings.lastQuoteRefreshTs || settings.lastQuoteRefresh?.ts || null,
      };
    } catch (_) {
      return null;
    }
  }

  async function persistedQuoteSnapshot() {
    const direct = runtimeQuoteSnapshot();
    if (direct?.report || direct?.ts) return direct;
    const storage = window.VestraStorage;
    if (typeof storage?.storageGet !== 'function') return { report: null, ts: null };
    try {
      const raw = await storage.storageGet();
      if (!raw) return { report: null, ts: null };
      const parsed = JSON.parse(raw);
      const settings = parsed?.settings || {};
      return {
        report: settings.lastQuoteRefresh || null,
        ts: settings.lastQuoteRefreshTs || settings.lastQuoteRefresh?.ts || null,
      };
    } catch (_) {
      return { report: null, ts: null };
    }
  }

  function ensureStyle() {
    if (document.getElementById('vestra-data-health-style')) return;
    const link = document.createElement('link');
    link.id = 'vestra-data-health-style';
    link.rel = 'stylesheet';
    link.href = 'market-data-health.css?v=1.0';
    document.head.appendChild(link);
  }

  function quoteResultLabel(data) {
    if (data.quoteUpdated == null && data.quoteFailed == null) return '—';
    const updated = data.quoteUpdated ?? 0;
    const failed = data.quoteFailed ?? 0;
    return failed > 0 ? `${updated} ok · ${failed} falhas` : `${updated} atualizadas`;
  }

  function durationLabel(ms) {
    if (ms == null) return '—';
    if (ms < 1000) return `${Math.round(ms)} ms`;
    return `${(ms / 1000).toFixed(1)} s`;
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
    host.dataset.state = data.overallState.key;
    const headlineAge = data.quoteDate ? `Cotações ${data.quoteAge}` : `Build ${data.age}`;
    host.innerHTML = `
      <summary aria-label="Estado operacional dos dados Vestra">
        <span class="vestra-data-health__dot" aria-hidden="true"></span>
        <span class="vestra-data-health__label">${data.overallState.label}</span>
        <span class="vestra-data-health__age">${headlineAge}</span>
        <span class="vestra-data-health__chev" aria-hidden="true">⌄</span>
      </summary>
      <div class="vestra-data-health__grid">
        <div class="vestra-data-health__item"><small>Cotações</small><strong>${data.quoteState.label}</strong></div>
        <div class="vestra-data-health__item"><small>Última atualização</small><strong>${formatDate(data.quoteDate)}</strong></div>
        <div class="vestra-data-health__item"><small>Resultado</small><strong>${quoteResultLabel(data)}</strong></div>
        <div class="vestra-data-health__item"><small>Duração</small><strong>${durationLabel(data.quoteDurationMs)}</strong></div>
        <div class="vestra-data-health__item"><small>Build de referência</small><strong>${formatDate(data.generatedAt)}</strong></div>
        <div class="vestra-data-health__item"><small>Universo verificado</small><strong>${data.rows == null ? '—' : new Intl.NumberFormat('pt-PT').format(data.rows)}</strong></div>
        <div class="vestra-data-health__item"><small>Coverage guard</small><strong>${data.violations == null ? data.state.label : `${data.violations} violações`}</strong></div>
        <div class="vestra-data-health__item"><small>Tickers aprendidos</small><strong>${data.learnedCount == null ? '—' : data.learnedCount}</strong></div>
      </div>`;
  }

  async function refresh() {
    const view = document.getElementById('viewMarket');
    if (!view) return null;
    ensureStyle();
    const [guard, learned, quote] = await Promise.all([
      loadJson(DATA_URLS.guard),
      loadJson(DATA_URLS.learned),
      persistedQuoteSnapshot(),
    ]);
    const data = model(guard, learned, new Date(), quote.report, quote.ts);
    render(view, data);
    return data;
  }

  function start() {
    refresh();
    document.addEventListener('quotesUpdated', refresh);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) refresh();
    });
    window.addEventListener?.('vestra:app-ready', refresh);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();

  window.VestraMarketDataHealth = Object.freeze({
    version: '1.2',
    quoteStaleMs: QUOTE_STALE_MS,
    refresh,
    model,
    ageLabel,
    deriveState,
    deriveQuoteState,
    deriveOverallState,
  });
})();
