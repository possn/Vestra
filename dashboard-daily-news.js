/* Vestra Dashboard Daily News v1.0 — compact market + portfolio-aware daily briefing. */
(() => {
  'use strict';

  const FETCH_TIMEOUT_MS = 5000;
  const MAX_VISIBLE = 5;
  let payload = null;
  let loadPromise = null;
  let renderQueued = false;

  const text = value => String(value ?? '').trim();
  const esc = value => text(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

  function portfolioTickers() {
    const rows = (() => { try { return Array.isArray(state?.assets) ? state.assets : []; } catch (_) { return []; } })();
    const tickers = new Set();
    for (const asset of rows) {
      for (const raw of [asset?.ticker, asset?.symbol, asset?.quoteSymbol, asset?.canonicalTicker, asset?.yahooSymbol]) {
        const ticker = text(raw).toUpperCase();
        if (!ticker) continue;
        tickers.add(ticker);
        tickers.add(ticker.split('.')[0]);
      }
    }
    return tickers;
  }

  function publishedTime(item) {
    const ts = Date.parse(text(item?.published));
    return Number.isFinite(ts) ? ts : 0;
  }

  function portfolioHits(item, held) {
    return (Array.isArray(item?.tickers) ? item.tickers : []).filter(raw => {
      const ticker = text(raw).toUpperCase();
      return ticker && (held.has(ticker) || held.has(ticker.split('.')[0]));
    });
  }

  function rankedItems() {
    const rows = Array.isArray(payload?.items) ? payload.items : [];
    const held = portfolioTickers();
    const now = Date.now();
    const ranked = rows.map((item, index) => {
      const hits = portfolioHits(item, held);
      const ageHours = publishedTime(item) ? Math.max(0, (now - publishedTime(item)) / 3600000) : 72;
      const impact = Number(item?.impact_score) || 0;
      const score = impact + (hits.length ? 120 + Math.min(30, hits.length * 10) : 0) - Math.min(40, ageHours * 0.8) - index * 0.01;
      return { item, hits, score, ageHours };
    }).sort((a, b) => b.score - a.score);

    const selected = [];
    const seenSources = new Map();
    let marketOnly = 0;
    for (const candidate of ranked) {
      const source = text(candidate.item?.source).toLowerCase();
      const sourceCount = seenSources.get(source) || 0;
      if (source && sourceCount >= 2) continue;
      if (!candidate.hits.length && candidate.item?.kind === 'market') {
        if (marketOnly >= 3) continue;
        marketOnly += 1;
      }
      selected.push(candidate);
      if (source) seenSources.set(source, sourceCount + 1);
      if (selected.length >= MAX_VISIBLE) break;
    }
    return selected;
  }

  function timeLabel(item) {
    const ts = publishedTime(item);
    if (!ts) return '';
    const hours = Math.max(0, Math.round((Date.now() - ts) / 3600000));
    if (hours < 1) return 'agora';
    if (hours === 1) return 'há 1 h';
    if (hours < 24) return `há ${hours} h`;
    const days = Math.round(hours / 24);
    return days === 1 ? 'há 1 dia' : `há ${days} dias`;
  }

  function cardHtml() {
    const rows = rankedItems();
    const generated = payload?.generated_at ? Date.parse(payload.generated_at) : 0;
    const freshness = Number.isFinite(generated) && generated > 0 ? new Date(generated).toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' }) : '';
    const body = rows.length ? rows.map(({ item, hits }) => {
      const badge = hits.length ? `CARTEIRA · ${esc(hits.slice(0, 2).map(x => text(x).split('.')[0]).join(', '))}` : 'MERCADO';
      const meta = [text(item?.source), timeLabel(item)].filter(Boolean).join(' · ');
      return `<a class="vestra-daily-news-item" href="${esc(item?.link)}" target="_blank" rel="noopener noreferrer"><span class="vestra-daily-news-badge${hits.length ? ' is-portfolio' : ''}">${badge}</span><strong>${esc(item?.title)}</strong><small>${esc(meta)}</small></a>`;
    }).join('') : '<div class="vestra-daily-news-empty">Sem notícias relevantes atualizadas neste momento.</div>';
    return `<section class="vestra-daily-news-card" id="vestraDailyNewsCard"><div class="vestra-daily-news-head"><div><span class="vestra-daily-news-kicker">HOJE</span><h3>Notícias do dia</h3><p>O que pode mexer com os mercados e com a tua carteira.</p></div>${freshness ? `<small>Dados ${esc(freshness)}</small>` : ''}</div><div class="vestra-daily-news-list">${body}</div></section>`;
  }

  function dashboardAnchor() {
    return document.getElementById('quickTools') || document.getElementById('passiveIncomeSection') || document.getElementById('portfolioEvolutionCard');
  }

  function render() {
    const anchor = dashboardAnchor();
    if (!anchor || !payload) return false;
    const existing = document.getElementById('vestraDailyNewsCard');
    const shell = document.createElement('div');
    shell.innerHTML = cardHtml();
    const next = shell.firstElementChild;
    if (!next) return false;
    if (existing) existing.replaceWith(next);
    else anchor.parentNode?.insertBefore(next, anchor);
    return true;
  }

  function queueRender() {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => { renderQueued = false; render(); });
  }

  async function fetchWithTimeout(url) {
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    let timer = null;
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => {
        try { controller?.abort(); } catch (_) {}
        reject(new Error('dashboard news timeout'));
      }, FETCH_TIMEOUT_MS);
    });
    try {
      const request = fetch(url, { cache: 'no-store', ...(controller ? { signal: controller.signal } : {}) });
      return await Promise.race([request, timeout]);
    } finally {
      if (timer !== null) clearTimeout(timer);
    }
  }

  async function load(force = false) {
    if (payload && !force) { queueRender(); return payload; }
    if (loadPromise) return loadPromise;
    loadPromise = (async () => {
      const response = await fetchWithTimeout('data/dashboard-news.json');
      if (!response?.ok) throw new Error(`dashboard news ${response?.status || 'unavailable'}`);
      const next = await response.json();
      if (!next || !Array.isArray(next.items)) throw new Error('dashboard news invalid payload');
      payload = next;
      queueRender();
      return payload;
    })().catch(() => null).finally(() => { loadPromise = null; });
    return loadPromise;
  }

  function style() {
    if (document.getElementById('vestra-dashboard-daily-news-style')) return;
    const link = document.createElement('link');
    link.id = 'vestra-dashboard-daily-news-style';
    link.rel = 'stylesheet';
    link.href = 'dashboard-daily-news.css?v=1.0';
    document.head.appendChild(link);
  }

  function start() {
    style();
    load();
    const observer = typeof MutationObserver === 'function' ? new MutationObserver(queueRender) : null;
    if (observer && document.body) observer.observe(document.body, { childList: true, subtree: true });
    document.addEventListener('click', event => {
      if (event.target.closest?.('.sidenavbtn[data-view="dashboard"], .navbtn[data-view="dashboard"]')) queueRender();
    });
    window.addEventListener?.('vestra:market-ready', queueRender);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();

  window.VestraDashboardDailyNews = Object.freeze({ load, refresh: () => load(true), render, rankedItems, version: '1.0' });
})();
