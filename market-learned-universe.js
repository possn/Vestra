/* Vestra Learned Universe v2.0 — persistent local catalogue of globally discovered instruments. */
(() => {
  'use strict';

  // v2 intentionally starts from a clean local catalogue. v1 could persist
  // symbols that passed a permissive upstream fallback without exact identity.
  const DB_KEY = 'market_learned_universe_v2';
  const SCHEMA_VERSION = 2;
  const MAX_ROWS = 500;
  const txt = v => String(v ?? '').trim();

  let loaded = false;
  let loading = null;
  let rows = [];

  function normalizeRow(input, source='live') {
    const ticker = txt(input?.ticker || input?.symbol).toUpperCase();
    if (!ticker) return null;
    const now = new Date().toISOString();
    return {
      ticker,
      name: txt(input?.name || input?.longname || input?.shortname || ticker),
      exchange: txt(input?.exchange),
      currency: txt(input?.currency).toUpperCase(),
      quote_type: txt(input?.quote_type || input?.quoteType || 'EQUITY').toUpperCase(),
      sector: txt(input?.sector),
      industry: txt(input?.industry),
      country: txt(input?.country),
      source: txt(source) || 'live',
      first_seen: txt(input?.first_seen) || now,
      last_seen: now,
      validation_count: Math.max(1, Number(input?.validation_count || 1) || 1),
      promotion_status: txt(input?.promotion_status) || 'pending',
    };
  }

  async function load() {
    if (loaded) return rows;
    if (loading) return loading;
    loading = (async () => {
      try {
        const raw = await window.VestraStorage?.idbGet?.(DB_KEY);
        const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
        const list = Array.isArray(parsed?.rows) ? parsed.rows : [];
        rows = list.map(r => normalizeRow(r, r?.source || 'persisted')).filter(Boolean).slice(0, MAX_ROWS);
      } catch (_) {
        rows = [];
      }
      loaded = true;
      return rows;
    })();
    return loading;
  }

  async function persist() {
    const payload = { schema_version: SCHEMA_VERSION, updated_at: new Date().toISOString(), rows };
    try {
      if (window.VestraStorage?.idbSet) {
        await window.VestraStorage.idbSet(DB_KEY, payload);
        return true;
      }
    } catch (_) {}
    return false;
  }

  async function upsert(input, source='live') {
    await load();
    const next = normalizeRow(input, source);
    if (!next) return null;
    const i = rows.findIndex(r => r.ticker === next.ticker);
    if (i >= 0) {
      const prev = rows[i];
      rows[i] = {
        ...prev,
        ...next,
        first_seen: prev.first_seen || next.first_seen,
        validation_count: (Number(prev.validation_count) || 0) + 1,
        promotion_status: prev.promotion_status || 'pending',
      };
    } else {
      rows.unshift(next);
    }
    rows.sort((a,b) => txt(b.last_seen).localeCompare(txt(a.last_seen)));
    if (rows.length > MAX_ROWS) rows.length = MAX_ROWS;
    await persist();
    try { window.dispatchEvent(new CustomEvent('vestra:learned-universe-updated',{detail:{ticker:next.ticker}})); } catch (_) {}
    return rows.find(r => r.ticker === next.ticker) || next;
  }

  async function search(query, limit=8) {
    await load();
    const q = txt(query).toLowerCase();
    if (!q) return [];
    return rows.filter(r =>
      r.ticker.toLowerCase().includes(q) ||
      txt(r.name).toLowerCase().includes(q) ||
      txt(r.exchange).toLowerCase().includes(q)
    ).slice(0, Math.max(1, limit));
  }

  async function list() { await load(); return rows.map(r => ({...r})); }
  async function pendingPromotion() { await load(); return rows.filter(r => r.promotion_status === 'pending').map(r => ({...r})); }

  window.VestraLearnedUniverse = Object.freeze({
    version: '2.0', DB_KEY, load, upsert, search, list, pendingPromotion,
  });
})();
