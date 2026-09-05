/* Vestra Quote Refresh Performance v1.0 — batch the common path, preserve existing per-asset fallback. */
(() => {
  'use strict';

  const BATCH_SIZE = 20;
  const BATCH_CONCURRENCY = 10;
  const BATCH_TIMEOUT_MS = 8500;

  const now = () => (typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now());
  const clean = v => String(v == null ? '' : v).trim().toUpperCase();

  function workerUrl() {
    const input = document.getElementById('settingsWorkerUrl');
    return String(input && input.value || '').trim().replace(/\/$/, '');
  }

  function looksLikeQuoteRefresh(items, limit) {
    if (Number(limit) !== 8 || !Array.isArray(items) || items.length < 12) return false;
    return items.every(item => item && Array.isArray(item.candidates) && item.asset);
  }

  async function mapLimited(items, limit, worker) {
    const out = new Array(items.length);
    let cursor = 0;
    const runners = Array.from({length: Math.min(limit, items.length)}, async () => {
      while (true) {
        const idx = cursor++;
        if (idx >= items.length) return;
        try { out[idx] = {status:'fulfilled', value:await worker(items[idx], idx)}; }
        catch (reason) { out[idx] = {status:'rejected', reason}; }
      }
    });
    await Promise.all(runners);
    return out;
  }

  async function fetchBatch(base, tickers) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), BATCH_TIMEOUT_MS);
    try {
      const url = `${base}/quotes?tickers=${encodeURIComponent(tickers.join(','))}`;
      const response = await fetch(url, {signal:controller.signal, cache:'no-store'});
      if (!response.ok) throw new Error(`Worker batch HTTP ${response.status}`);
      const payload = await response.json();
      return payload && typeof payload === 'object' ? payload : {};
    } catch (error) {
      const e = new Error(error && error.name === 'AbortError' ? 'Tempo limite do batch de cotações' : (error?.message || 'Falha no batch de cotações'));
      e.cause = error;
      throw e;
    } finally {
      clearTimeout(timer);
    }
  }

  async function fastQuoteMap(items, fallbackWorker) {
    const base = workerUrl();
    if (!base) return null;

    const started = now();
    const primaryByIndex = items.map(item => clean(item.candidates && item.candidates[0]));
    const unique = [...new Set(primaryByIndex.filter(Boolean))];
    if (!unique.length) return null;

    const chunks = [];
    for (let i = 0; i < unique.length; i += BATCH_SIZE) chunks.push(unique.slice(i, i + BATCH_SIZE));

    const quoteByTicker = new Map();
    const batchResults = await mapLimited(chunks, BATCH_CONCURRENCY, async chunk => fetchBatch(base, chunk));
    batchResults.forEach((result, chunkIndex) => {
      if (!result || result.status !== 'fulfilled') return;
      const payload = result.value || {};
      for (const ticker of chunks[chunkIndex]) {
        const row = payload[ticker];
        if (row && !row.error && Number.isFinite(Number(row.price)) && Number(row.price) > 0) quoteByTicker.set(ticker, row);
      }
    });

    const settled = new Array(items.length);
    const fallbackIndexes = [];
    items.forEach((item, idx) => {
      const ticker = primaryByIndex[idx];
      const quote = quoteByTicker.get(ticker);
      if (quote) {
        settled[idx] = {
          status:'fulfilled',
          value:{yahoo:ticker, quote, attempts:1, durationMs:Math.round(now() - started), fastBatch:true}
        };
      } else {
        fallbackIndexes.push(idx);
      }
    });

    if (fallbackIndexes.length) {
      const fallbackItems = fallbackIndexes.map(idx => items[idx]);
      const fallback = await mapLimited(fallbackItems, 8, fallbackWorker);
      fallbackIndexes.forEach((idx, j) => { settled[idx] = fallback[j]; });
    }

    return settled;
  }

  function install() {
    const original = window.mapWithConcurrency;
    if (typeof original !== 'function' || original.__vestraQuoteFastLane) return false;

    async function accelerated(items, limit, worker) {
      if (!looksLikeQuoteRefresh(items, limit)) return original(items, limit, worker);
      try {
        const result = await fastQuoteMap(items, worker);
        if (result) return result;
      } catch (error) {
        console.warn('[Quotes] fast batch unavailable; using existing individual path', error);
      }
      return original(items, limit, worker);
    }

    Object.defineProperty(accelerated, '__vestraQuoteFastLane', {value:true});
    Object.defineProperty(accelerated, '__vestraOriginal', {value:original});
    window.mapWithConcurrency = accelerated;
    return true;
  }

  if (!install()) document.addEventListener('DOMContentLoaded', install, {once:true});

  window.VestraQuoteRefreshPerformance = Object.freeze({
    version:'1.0',
    batchSize:BATCH_SIZE,
    batchConcurrency:BATCH_CONCURRENCY,
    batchTimeoutMs:BATCH_TIMEOUT_MS,
    install,
  });
})();
