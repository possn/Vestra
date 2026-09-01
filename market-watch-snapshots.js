/* Vestra Market Watch Snapshots v1.0 — watchlist persistence and tracked-change snapshots. */
(() => {
  'use strict';

  function create(options = {}) {
    const state = options.state || {};
    const text = typeof options.text === 'function' ? options.text : v => String(v ?? '').trim();
    const number = typeof options.number === 'function' ? options.number : v => {
      if (v === null || v === undefined || v === '') return null;
      const x = Number(v);
      return Number.isFinite(x) ? x : null;
    };
    const escapeHtml = typeof options.escapeHtml === 'function' ? options.escapeHtml : v => text(v);
    const formatShortDate = typeof options.formatShortDate === 'function' ? options.formatShortDate : v => text(v) || '—';
    const getPortfolioTickers = typeof options.getPortfolioTickers === 'function' ? options.getPortfolioTickers : () => new Set();
    const getStocksByTicker = typeof options.getStocksByTicker === 'function' ? options.getStocksByTicker : () => new Map();
    const getStocks = typeof options.getStocks === 'function' ? options.getStocks : () => [];
    const getGeneratedAt = typeof options.getGeneratedAt === 'function' ? options.getGeneratedAt : () => '';
    const storage = options.storage || window.localStorage;
    const now = typeof options.now === 'function' ? options.now : () => Date.now();
    const watchKey = options.watchKey || 'vestra-market-watchlist-v1';
    const lastKey = options.lastKey || 'vestra-market-snapshot-last-v1';
    const previousKey = options.previousKey || 'vestra-market-snapshot-prev-v1';

    function loadWatchlist() {
      try {
        const rows = JSON.parse(storage.getItem(watchKey) || '[]');
        state.watchlist = new Set((Array.isArray(rows) ? rows : []).map(x => text(x).toUpperCase()).filter(Boolean));
      } catch (_) {
        state.watchlist = new Set();
      }
      return state.watchlist;
    }

    function saveWatchlist() {
      try { storage.setItem(watchKey, JSON.stringify([...(state.watchlist || new Set())])); } catch (_) {}
    }

    function isWatched(ticker) {
      return (state.watchlist || new Set()).has(text(ticker).toUpperCase());
    }

    function snapshotStock(stock) {
      return {
        score: number(stock?.score),
        thesis_direction: text(stock?.thesis_direction),
        thesis_type: text(stock?.thesis_type),
        forward_pe_vs_sector_pct: number(stock?.forward_pe_vs_sector_pct),
        trailing_pe_vs_sector_pct: number(stock?.trailing_pe_vs_sector_pct),
        analyst_eps_revisions_up_30d: number(stock?.analyst_eps_revisions_up_30d) || 0,
        analyst_eps_revisions_down_30d: number(stock?.analyst_eps_revisions_down_30d) || 0,
        analyst_price_target_upside_pct: number(stock?.analyst_price_target_upside_pct),
        insider_buy_count_30d: number(stock?.insider_buy_count_30d) || 0,
        insider_sell_count_30d: number(stock?.insider_sell_count_30d) || 0,
        analyst_next_earnings_date: text(stock?.analyst_next_earnings_date),
        current_price: number(stock?.current_price),
      };
    }

    function resolveStock(ticker) {
      const t = text(ticker).toUpperCase();
      const base = t.replace(/\.[A-Z]+$/, '');
      return getStocksByTicker().get(t) || getStocks().find(x => text(x?.ticker).toUpperCase().replace(/\.[A-Z]+$/, '') === base) || null;
    }

    function buildSnapshot() {
      const tracked = new Set([...(state.watchlist || new Set()), ...getPortfolioTickers()]);
      const stocks = {};
      for (const ticker of tracked) {
        const stock = resolveStock(ticker);
        if (stock) stocks[text(stock.ticker).toUpperCase()] = snapshotStock(stock);
      }
      return { generatedAt: text(getGeneratedAt()), savedAt: new Date(now()).toISOString(), stocks };
    }

    function syncSnapshots() {
      try {
        const last = JSON.parse(storage.getItem(lastKey) || 'null');
        const previous = JSON.parse(storage.getItem(previousKey) || 'null');
        const current = buildSnapshot();
        if (last && last.generatedAt && current.generatedAt && last.generatedAt !== current.generatedAt) {
          storage.setItem(previousKey, JSON.stringify(last));
          state.previousSnapshot = last;
          storage.setItem(lastKey, JSON.stringify(current));
        } else if (!last) {
          storage.setItem(lastKey, JSON.stringify(current));
          state.previousSnapshot = previous;
        } else {
          state.previousSnapshot = previous;
          last.stocks = { ...(last.stocks || {}), ...(current.stocks || {}) };
          storage.setItem(lastKey, JSON.stringify(last));
        }
        state.currentSnapshot = current;
      } catch (_) {
        state.previousSnapshot = null;
        state.currentSnapshot = null;
      }
      return state.currentSnapshot;
    }

    function previousFor(stock) {
      return state.previousSnapshot?.stocks?.[text(stock?.ticker).toUpperCase()] || null;
    }

    function daysUntil(value) {
      if (!value) return null;
      const d = new Date(value);
      if (Number.isNaN(d.valueOf())) return null;
      return Math.ceil((d.valueOf() - now()) / 86400000);
    }

    function changeSignals(stock) {
      const out = [];
      const prev = previousFor(stock);
      if (prev) {
        const ds = number(stock?.score) != null && number(prev.score) != null ? number(stock.score) - number(prev.score) : null;
        if (ds != null && Math.abs(ds) >= 1) out.push({ tone: ds > 0 ? 'up' : 'down', label: `Score ${ds > 0 ? '+' : ''}${ds.toFixed(1)}` });
        if (text(stock?.thesis_direction) && text(prev.thesis_direction) && text(stock.thesis_direction) !== text(prev.thesis_direction)) {
          out.push({ tone: text(stock.thesis_direction) === 'up' ? 'up' : text(stock.thesis_direction) === 'down' ? 'down' : 'neutral', label: `Tese ${text(stock.thesis_direction_label) || text(stock.thesis_direction)}` });
        }
        const revisions = (number(stock?.analyst_eps_revisions_up_30d) || 0) - (number(stock?.analyst_eps_revisions_down_30d) || 0);
        const prevRevisions = (number(prev.analyst_eps_revisions_up_30d) || 0) - (number(prev.analyst_eps_revisions_down_30d) || 0);
        if (Math.abs(revisions - prevRevisions) >= 2) out.push({ tone: revisions > prevRevisions ? 'up' : 'down', label: `Revisões EPS ${revisions > prevRevisions ? 'melhoraram' : 'pioraram'}` });
        const valuation = number(stock?.forward_pe_vs_sector_pct) ?? number(stock?.trailing_pe_vs_sector_pct);
        const prevValuation = number(prev.forward_pe_vs_sector_pct) ?? number(prev.trailing_pe_vs_sector_pct);
        if (valuation != null && prevValuation != null && Math.abs(valuation - prevValuation) >= 10) out.push({ tone: valuation < prevValuation ? 'up' : 'down', label: `Valuation ${valuation < prevValuation ? 'mais favorável' : 'mais exigente'}` });
        if ((number(stock?.insider_buy_count_30d) || 0) > (number(prev.insider_buy_count_30d) || 0)) out.push({ tone: 'up', label: 'Novas compras insider' });
        if ((number(stock?.insider_sell_count_30d) || 0) > (number(prev.insider_sell_count_30d) || 0)) out.push({ tone: 'down', label: 'Novas vendas insider' });
      } else {
        const delta7 = number(stock?.thesis_score_delta_7d);
        if (delta7 != null && Math.abs(delta7) >= 1) out.push({ tone: delta7 > 0 ? 'up' : 'down', label: `Score 7d ${delta7 > 0 ? '+' : ''}${delta7.toFixed(1)}` });
        if (text(stock?.thesis_direction) === 'up') out.push({ tone: 'up', label: 'Tese a melhorar' });
        if (text(stock?.thesis_direction) === 'down') out.push({ tone: 'down', label: 'Tese a piorar' });
        const up = number(stock?.analyst_eps_revisions_up_30d) || 0;
        const down = number(stock?.analyst_eps_revisions_down_30d) || 0;
        if (up - down >= 3) out.push({ tone: 'up', label: 'Revisões EPS positivas' });
        else if (down - up >= 3) out.push({ tone: 'down', label: 'Revisões EPS negativas' });
        if (number(stock?.insider_buy_count_30d) > 0) out.push({ tone: 'up', label: 'Insiders a comprar' });
      }
      const days = daysUntil(stock?.analyst_next_earnings_date);
      if (days != null && days >= 0 && days <= 14) out.push({ tone: 'event', label: `Resultados em ${days}d` });
      return out.slice(0, 4);
    }

    function changeBadge(stock) {
      const signal = changeSignals(stock)[0];
      if (!signal) return '';
      const icon = signal.tone === 'up' ? '↗' : signal.tone === 'down' ? '↘' : signal.tone === 'event' ? '◷' : '•';
      return `<span class="market-change market-change--${signal.tone}">${icon} ${escapeHtml(signal.label)}</span>`;
    }

    function changePanel(stock) {
      const changes = changeSignals(stock);
      const prev = previousFor(stock);
      const label = prev ? `Desde ${formatShortDate(state.previousSnapshot?.generatedAt || state.previousSnapshot?.savedAt)}` : 'Sinais recentes';
      return `<div class="market-change-panel"><div class="market-change-panel__head"><div><small>O QUE MUDOU</small><h4>${escapeHtml(label)}</h4></div><span>${changes.length ? `${changes.length} ${changes.length === 1 ? 'alteração' : 'alterações'}` : 'Estável'}</span></div>${changes.length ? `<div class="market-change-list">${changes.map(signal => { const icon = signal.tone === 'up' ? '↗' : signal.tone === 'down' ? '↘' : signal.tone === 'event' ? '◷' : '•'; return `<div class="market-change-item market-change-item--${signal.tone}"><b>${icon}</b><span>${escapeHtml(signal.label)}</span></div>`; }).join('')}</div>` : '<p>Sem mudança material identificada desde a referência disponível.</p>'}</div>`;
    }

    return Object.freeze({
      loadWatchlist,
      saveWatchlist,
      isWatched,
      snapshotStock,
      buildSnapshot,
      syncSnapshots,
      previousFor,
      daysUntil,
      changeSignals,
      changeBadge,
      changePanel,
    });
  }

  window.VestraMarketWatchSnapshots = Object.freeze({ create, version: '1.0' });
})();
