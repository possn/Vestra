/* Vestra Market Live Overlay v1.1 — bounded live dossier enrichment without rerendering the open sheet. */
(() => {
  'use strict';

  const LIVE_TIMEOUT_MS = 4500;

  function create(options = {}) {
    const getWorkerBase = typeof options.getWorkerBase === 'function' ? options.getWorkerBase : () => '';
    const getSheet = typeof options.getSheet === 'function' ? options.getSheet : () => null;
    const loadingSet = options.loadingSet instanceof Set ? options.loadingSet : new Set();
    const text = typeof options.text === 'function' ? options.text : v => String(v ?? '').trim();
    const escapeHtml = typeof options.escapeHtml === 'function' ? options.escapeHtml : v => text(v);
    const formatMoney = typeof options.formatMoney === 'function' ? options.formatMoney : () => '—';
    const formatNum = typeof options.formatNum === 'function' ? options.formatNum : () => '—';
    const formatPct = typeof options.formatPct === 'function' ? options.formatPct : () => '—';
    const fetchImpl = typeof options.fetchImpl === 'function' ? options.fetchImpl : (...args) => fetch(...args);
    const timeoutMs = Number.isFinite(Number(options.timeoutMs)) && Number(options.timeoutMs) > 0
      ? Number(options.timeoutMs)
      : LIVE_TIMEOUT_MS;

    function compactLiveBadge(stock) {
      if (!stock?._liveUpdated) return '';
      const date = new Date(stock._liveUpdated);
      if (Number.isNaN(date.valueOf())) return '';
      const time = new Intl.DateTimeFormat('pt-PT', { hour: '2-digit', minute: '2-digit' }).format(date);
      return `<span class="market-live-badge">● Live · ${escapeHtml(time)}</span>`;
    }

    function refreshOpenDossierLiveFields(stock) {
      const sheet = getSheet();
      const ticker = text(stock?.ticker).toUpperCase();
      if (!sheet || sheet.hidden || !ticker || text(sheet.dataset?.ticker).toUpperCase() !== ticker) return false;
      const values = {
        current_price: formatMoney(stock.current_price, stock.currency),
        forward_pe: formatNum(stock.forward_pe),
        roe: formatPct(stock.roe),
        revenue_growth: formatPct(stock.revenue_growth),
        fcf_yield: formatPct(stock.fcf_yield),
      };
      for (const [field, value] of Object.entries(values)) {
        const el = sheet.querySelector(`[data-live-field="${field}"]`);
        if (el && value !== '—') el.textContent = value;
      }
      return true;
    }

    function refreshOpenDossierBadge(stock) {
      const sheet = getSheet();
      const ticker = text(stock?.ticker).toUpperCase();
      if (!sheet || sheet.hidden || !ticker || text(sheet.dataset?.ticker).toUpperCase() !== ticker) return false;
      const head = sheet.querySelector('.market-detail-head');
      let badge = head?.querySelector('.market-live-badge');
      const holder = document.createElement('span');
      holder.innerHTML = compactLiveBadge(stock);
      const nextBadge = holder.firstElementChild;
      if (!nextBadge) return false;
      if (!badge && head) {
        const info = head.querySelector('.market-detail-head > div:first-child');
        if (info) info.appendChild(nextBadge);
      } else if (badge) {
        badge.replaceWith(nextBadge);
      }
      refreshOpenDossierLiveFields(stock);
      sheet.dataset.liveReady = '1';
      return true;
    }

    async function fetchWithDeadline(url) {
      const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      let timer = null;
      const timeout = new Promise((_, reject) => {
        timer = setTimeout(() => {
          try { controller?.abort(); } catch (_) {}
          reject(new Error('live quote timeout'));
        }, timeoutMs);
      });
      try {
        return await Promise.race([
          fetchImpl(url, { cache: 'no-store', ...(controller ? { signal: controller.signal } : {}) }),
          timeout,
        ]);
      } finally {
        if (timer) clearTimeout(timer);
      }
    }

    async function enrichTickerLive(stock) {
      const base = text(getWorkerBase()).replace(/\/$/, '');
      const ticker = text(stock?.ticker).toUpperCase();
      if (!base || !ticker || loadingSet.has(ticker)) return null;
      loadingSet.add(ticker);
      try {
        const response = await fetchWithDeadline(`${base}/market?ticker=${encodeURIComponent(ticker)}`);
        if (!response.ok) throw new Error(`market ${response.status}`);
        const live = await response.json();
        if (!live || live.error) return null;
        const merge = {};
        for (const [key, value] of Object.entries(live)) {
          if (value !== null && value !== undefined && value !== '') merge[key] = value;
        }
        Object.assign(stock, merge, {
          _liveUpdated: live.quote_updated || live.updated || new Date().toISOString(),
        });
        // Safari/iPhone contract: never rebuild the open dossier after async data arrives.
        // Only mutate the small live badge and the explicitly marked live fields.
        refreshOpenDossierBadge(stock);
        return live;
      } catch (_) {
        // The local snapshot remains the canonical fallback when live enrichment fails.
        return null;
      } finally {
        loadingSet.delete(ticker);
      }
    }

    return Object.freeze({ compactLiveBadge, refreshOpenDossierLiveFields, enrichTickerLive });
  }

  window.VestraMarketLiveOverlay = Object.freeze({
    create,
    version: '1.1',
    timeoutMs: LIVE_TIMEOUT_MS,
  });
})();
