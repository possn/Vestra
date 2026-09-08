/* Vestra ETF Intelligence v1.1 — fund-only scoring, separate from equity Score. */
(() => {
  'use strict';

  const FUND_TYPES = new Set(['ETF', 'MUTUALFUND', 'FUND']);

  function text(v){ return String(v ?? '').trim(); }
  function number(v){
    if(v === null || v === undefined || v === '') return null;
    const x = Number(v);
    return Number.isFinite(x) ? x : null;
  }
  function isFund(row){ return FUND_TYPES.has(text(row?.quote_type).toUpperCase()); }

  function ratioToPct(v){
    const x = number(v);
    if(x == null) return null;
    return Math.abs(x) <= 1 ? x * 100 : x;
  }

  function clamp(v, lo=0, hi=100){ return Math.max(lo, Math.min(hi, v)); }

  function expenseScore(row){
    const ter = ratioToPct(row?.expense_ratio);
    if(ter == null || ter < 0) return null;
    if(ter <= 0.07) return 100;
    if(ter <= 0.15) return 92;
    if(ter <= 0.25) return 82;
    if(ter <= 0.40) return 70;
    if(ter <= 0.65) return 55;
    if(ter <= 1.00) return 35;
    return 15;
  }

  function scaleScore(row){
    const aum = number(row?.fund_total_assets) ?? number(row?.market_cap);
    if(aum == null || aum <= 0) return null;
    if(aum >= 20e9) return 100;
    if(aum >= 5e9) return 92;
    if(aum >= 1e9) return 82;
    if(aum >= 250e6) return 68;
    if(aum >= 75e6) return 52;
    return 30;
  }

  function diversificationScore(row){
    const holdings = Array.isArray(row?.top_holdings) ? row.top_holdings : [];
    if(!holdings.length) return null;
    const weights = holdings.map(h => ratioToPct(h?.holdingPercent ?? h?.weight ?? h?.pct ?? h?.percentage)).filter(v => v != null && v >= 0);
    if(!weights.length) return null;
    const top10 = weights.slice(0, 10).reduce((a,b) => a+b, 0);
    if(top10 <= 20) return 100;
    if(top10 <= 30) return 90;
    if(top10 <= 40) return 78;
    if(top10 <= 50) return 64;
    if(top10 <= 65) return 48;
    return 30;
  }

  function riskScore(row){
    const low = number(row?.low52_price_low) ?? number(row?.fifty_two_week_low);
    const high = number(row?.low52_price_high) ?? number(row?.fifty_two_week_high);
    const current = number(row?.current_price);
    let drawdown = null;
    if(high != null && high > 0 && current != null && current > 0) drawdown = (current / high - 1) * 100;
    const r1y = number(row?.fund_return_1y_pct) ?? number(row?.return_1y_pct);
    if(drawdown == null && r1y == null && low == null) return null;
    let score = 72;
    if(drawdown != null){
      const dd = Math.abs(Math.min(0, drawdown));
      score += dd <= 8 ? 18 : dd <= 15 ? 10 : dd <= 25 ? 0 : dd <= 35 ? -12 : -25;
    }
    if(r1y != null){
      score += r1y >= -5 ? 5 : r1y >= -15 ? 0 : r1y >= -30 ? -7 : -14;
    }
    return clamp(score);
  }

  function structureScore(row){
    const ucits = text(row?.fund_ucits ?? row?.ucits).toLowerCase();
    const family = text(row?.fund_family);
    const category = text(row?.fund_category ?? row?.sector);
    const legal = text(row?.fund_legal_type);
    if(!ucits && !family && !category && !legal) return null;
    let score = 60;
    if(['confirmed','yes','true','ucits'].includes(ucits)) score += 25;
    if(family) score += 8;
    if(category) score += 5;
    if(legal) score += 2;
    return clamp(score);
  }

  function dataQualityScore(row){
    const checks = [
      number(row?.expense_ratio) != null,
      (number(row?.fund_total_assets) ?? number(row?.market_cap)) != null,
      Array.isArray(row?.top_holdings) && row.top_holdings.length > 0,
      number(row?.current_price) != null,
      (number(row?.low52_price_high) ?? number(row?.fifty_two_week_high)) != null,
      Boolean(text(row?.fund_region ?? row?.region)),
      Boolean(text(row?.fund_style)),
      Boolean(text(row?.fund_theme)),
    ];
    const observed = checks.filter(Boolean).length;
    return { score: Math.round(observed / checks.length * 100), observed, total: checks.length };
  }

  function assess(row){
    if(!isFund(row)) return null;
    const quality = dataQualityScore(row);
    const parts = [
      ['cost', expenseScore(row), 0.25],
      ['scale', scaleScore(row), 0.20],
      ['diversification', diversificationScore(row), 0.20],
      ['risk', riskScore(row), 0.15],
      ['structure', structureScore(row), 0.10],
      ['data', quality.score, 0.10],
    ];
    const available = parts.filter(([,v]) => v != null);
    const substantive = available.filter(([key]) => key !== 'data').length;
    const weight = available.reduce((sum,[,v,w]) => v == null ? sum : sum + w, 0);
    const score = substantive >= 2 && weight > 0
      ? Math.round(available.reduce((sum,[,v,w]) => sum + v*w, 0) / weight)
      : null;
    return {
      etf_score: score,
      etf_score_model: 'etf_v1',
      etf_score_coverage_pct: quality.score,
      etf_score_status: score == null ? 'pending' : 'published',
      etf_score_dimensions: Object.fromEntries(parts.map(([key,v]) => [key, v])),
    };
  }

  function enrichStocks(stocks){
    const rows = Array.isArray(stocks) ? stocks : [];
    let funds = 0, scored = 0;
    for(const row of rows){
      if(!isFund(row)) continue;
      funds += 1;
      const result = assess(row);
      if(result){ Object.assign(row, result); if(result.etf_score != null) scored += 1; }
    }
    const detail = { funds, scored, pending: Math.max(0, funds-scored) };
    try { window.dispatchEvent(new CustomEvent('vestra:etf-intelligence-ready', {detail})); } catch(_) {}
    return detail;
  }

  function rankVisibleFundLists(stocks){
    const byTicker = new Map(stocks.filter(isFund).map(row => [text(row?.ticker).toUpperCase(), row]));
    document.querySelectorAll('.market-list').forEach(list => {
      const rows = [...list.querySelectorAll(':scope > .market-row[data-market-ticker]')];
      if(rows.length < 2) return;
      if(!rows.every(el => byTicker.has(text(el.dataset.marketTicker).toUpperCase()))) return;
      rows.sort((a,b) => {
        const sa = number(byTicker.get(text(a.dataset.marketTicker).toUpperCase())?.etf_score);
        const sb = number(byTicker.get(text(b.dataset.marketTicker).toUpperCase())?.etf_score);
        if(sa == null && sb == null) return 0;
        if(sa == null) return 1;
        if(sb == null) return -1;
        return sb-sa;
      });
      rows.forEach(row => list.appendChild(row));
    });
  }

  function annotateDiscovery(){
    const stocks = window.VestraMarketStaticUniverse?.getStocks?.() || [];
    if(!stocks.length) return;
    const funds = stocks.filter(isFund);
    const scored = funds.filter(x => number(x?.etf_score) != null).length;
    rankVisibleFundLists(stocks);
    document.querySelectorAll('.market-etf-discovery').forEach(section => {
      if(section.querySelector('[data-etf-catalog-health]')) return;
      const head = section.querySelector('.market-section__head');
      if(!head) return;
      const badge = document.createElement('div');
      badge.dataset.etfCatalogHealth = '1';
      badge.className = 'market-data-age';
      badge.textContent = `${funds.length} no catálogo · ${scored} avaliados`;
      head.appendChild(badge);
    });
  }

  if(typeof MutationObserver !== 'undefined' && typeof document !== 'undefined'){
    let scheduled = false;
    const observer = new MutationObserver(() => {
      if(scheduled) return;
      scheduled = true;
      queueMicrotask(() => { scheduled = false; annotateDiscovery(); });
    });
    const start = () => observer.observe(document.body, {subtree:true, childList:true});
    if(document.body) start(); else document.addEventListener('DOMContentLoaded', start, {once:true});
  }
  if(typeof window !== 'undefined') window.addEventListener('vestra:market-ready', annotateDiscovery);

  window.VestraEtfIntelligence = Object.freeze({
    assess,
    enrichStocks,
    isFund,
    rankVisibleFundLists,
    version: '1.1',
  });
})();
