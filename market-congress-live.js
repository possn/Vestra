/* Vestra Market Congress Live v1.0 — canonical congressional trade loading and stock attachment. */
(() => {
  'use strict';

  function create(options = {}) {
    const state = options.state || {};
    const getStocksByTicker = typeof options.getStocksByTicker === 'function' ? options.getStocksByTicker : () => new Map();
    const getStocks = typeof options.getStocks === 'function' ? options.getStocks : () => [];
    const text = typeof options.text === 'function' ? options.text : v => String(v ?? '').trim();
    const fetchImpl = typeof options.fetchImpl === 'function' ? options.fetchImpl : (...args) => fetch(...args);
    const storage = options.storage || window.localStorage;
    const now = typeof options.now === 'function' ? options.now : () => Date.now();
    const cacheKey = options.cacheKey || 'vestra-congress-canonical-v4';
    const cacheMaxAge = Number(options.cacheMaxAge) > 0 ? Number(options.cacheMaxAge) : 6 * 60 * 60 * 1000;
    const maxSnapshotAge = Number(options.maxSnapshotAge) > 0 ? Number(options.maxSnapshotAge) : 60 * 86400000;

    function normalize(x) {
      return {
        ticker: text(x?.ticker).toUpperCase(),
        representative: text(x?.representative || x?.member || x?.name) || 'Membro do Congresso',
        chamber: text(x?.chamber),
        state: text(x?.state),
        party: text(x?.party),
        type: text(x?.type || x?.transaction) || 'trade',
        amount: text(x?.amount || x?.amount_range) || '—',
        transaction_date: text(x?.transaction_date || x?.date),
        disclosure_date: text(x?.disclosure_date || x?.filed_date),
        asset: text(x?.asset),
        filing_url: text(x?.filing_url || x?.filing_portal),
      };
    }

    function snapshotFresh(data) {
      if (!data || data.data_current === false || Number(data.schema_version || 0) < 2 || !Array.isArray(data.trades)) return false;
      const newest = text(data.newest_disclosure || data.source_last_updated).slice(0, 10);
      const ms = newest ? new Date(`${newest}T00:00:00Z`).valueOf() : NaN;
      if (!Number.isFinite(ms)) return false;
      const age = now() - ms;
      return age >= 0 && age <= maxSnapshotAge;
    }

    // Preserve share classes and exchange suffixes; BRK.A must never absorb BRK.B.
    const tickerIdentity = value => text(value).toUpperCase().replace(/-/g, '.');

    function validTradeDate(value, required = true) {
      if (!value) return !required;
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
      const time = Date.parse(value + 'T00:00:00Z');
      return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value
        && time <= now();
    }

    function deduplicateTrades(rows) {
      const seen = new Set();
      const result = [];
      for (const trade of rows.map(normalize).filter(item => item.ticker && validTradeDate(item.transaction_date) && validTradeDate(item.disclosure_date, false))) {
        const id = [tickerIdentity(trade.ticker), trade.transaction_date,
          trade.representative, trade.type, trade.amount, trade.asset].join('|');
        if (seen.has(id)) continue;
        seen.add(id);
        result.push(trade);
      }
      return result;
    }

    function attachToStocks(trades) {
      const grouped = new Map();
      for (const trade of trades) {
        const ticker = tickerIdentity(trade.ticker);
        if (!ticker) continue;
        if (!grouped.has(ticker)) grouped.set(ticker, []);
        grouped.get(ticker).push(trade);
      }
      const byTicker = getStocksByTicker();
      const stocks = getStocks();
      for (const [ticker, rows] of grouped) {
        const stock = byTicker.get(ticker) || stocks.find(item => tickerIdentity(item.ticker) === ticker);
        if (!stock) continue;
        const current = Array.isArray(stock.congress_trades) ? stock.congress_trades : [];
        const key = item => `${text(item.transaction_date || item.date)}|${text(item.representative || item.member || item.name)}|${text(item.type)}|${text(item.amount || item.amount_range)}|${text(item.asset)}`;
        const seen = new Set(current.map(key));
        const additions = [];
        for (const item of rows) {
          const identity = key(item);
          if (seen.has(identity)) continue;
          seen.add(identity);
          additions.push(item);
        }
        stock.congress_trades = [...current, ...additions];
      }
    }

    async function load(ticker = '') {
      const normalizedTicker = tickerIdentity(ticker);
      if (state.loaded) {
        return normalizedTicker ? state.trades.filter(item => tickerIdentity(item.ticker) === normalizedTicker) : state.trades;
      }
      if (state.loading) {
        const all = await state.loading;
        return normalizedTicker ? all.filter(item => tickerIdentity(item.ticker) === normalizedTicker) : all;
      }

      state.loading = (async () => {
        try {
          try {
            const cached = JSON.parse(storage.getItem(cacheKey) || 'null');
            const cachedAge = now() - Number(cached?.ts);
            if (cached && Array.isArray(cached.trades) && Number.isFinite(cachedAge)
                && cachedAge >= 0 && cachedAge < cacheMaxAge && snapshotFresh({ ...cached.snapshot, trades: cached.trades })) {
              state.trades = deduplicateTrades(cached.trades);
              state.loaded = true;
              state.error = '';
              attachToStocks(state.trades);
              return state.trades;
            }
          } catch (_) {}

          const response = await fetchImpl(`./data/politicians.json?ts=${now()}`, { cache: 'no-store' });
          if (!response.ok) throw new Error(`Congress snapshot HTTP ${response.status}`);
          const data = await response.json();
          if (!snapshotFresh(data)) throw new Error('Congress snapshot desactualizado');
          const trades = deduplicateTrades(data.trades);
          state.trades = trades;
          state.loaded = true;
          state.error = '';
          attachToStocks(trades);
          try { storage.setItem(cacheKey, JSON.stringify({ ts: now(), trades, snapshot: {
            schema_version: data.schema_version,
            newest_disclosure: data.newest_disclosure,
            source_last_updated: data.source_last_updated,
            data_current: data.data_current,
          } })); } catch (_) {}
          return trades;
        } catch (error) {
          state.trades = [];
          // A failed fetch must remain retryable in this session; otherwise
          // the next invocation returns an empty array without checking again.
          state.loaded = false;
          state.error = error?.message || 'Congress snapshot indisponível';
          return [];
        } finally {
          state.loading = null;
        }
      })();

      const all = await state.loading;
      return normalizedTicker ? all.filter(item => tickerIdentity(item.ticker) === normalizedTicker) : all;
    }

    return Object.freeze({ normalize, snapshotFresh, attachToStocks, load });
  }

  window.VestraMarketCongressLive = Object.freeze({ create, version: '1.2' });
})();
