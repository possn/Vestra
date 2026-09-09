/* Vestra ETF Intelligence v1.2 — fund-only scoring, compact startup evidence. */
(() => {
  'use strict';

  const FUND_TYPES = new Set(['ETF', 'MUTUALFUND', 'FUND']);
  const CATALOG_BATCH = 30;
  let catalogLimit = CATALOG_BATCH;

  function text(v){ return String(v ?? '').trim(); }
  function number(v){
    if(v === null || v === undefined || v === '') return null;
    const x = Number(v);
    return Number.isFinite(x) ? x : null;
  }
  function isFund(row){ return FUND_TYPES.has(text(row?.quote_type).toUpperCase()); }
  function escapeHtml(v){ return text(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

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
    let top10 = number(row?.fund_top10_weight_pct);
    if(top10 == null){
      const holdings = Array.isArray(row?.top_holdings) ? row.top_holdings : [];
      if(!holdings.length) return null;
      const weights = holdings.map(h => ratioToPct(h?.holdingPercent ?? h?.weight ?? h?.pct ?? h?.percentage)).filter(v => v != null && v >= 0);
      if(!weights.length) return null;
      top10 = weights.slice(0, 10).reduce((a,b) => a+b, 0);
    }
    if(top10 < 0) return null;
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
      number(row?.fund_top10_weight_pct) != null || (Array.isArray(row?.top_holdings) && row.top_holdings.length > 0),
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
      const sorted = [...rows].sort((a,b) => {
        const sa = number(byTicker.get(text(a.dataset.marketTicker).toUpperCase())?.etf_score);
        const sb = number(byTicker.get(text(b.dataset.marketTicker).toUpperCase())?.etf_score);
        if(sa == null && sb == null) return 0;
        if(sa == null) return 1;
        if(sb == null) return -1;
        return sb-sa;
      });
      if(sorted.every((row,index) => row === rows[index])) return;
      sorted.forEach(row => list.appendChild(row));
    });
  }

  function scoreClass(value){
    const x = number(value);
    return x == null ? 'market-score--soft' : x >= 70 ? '' : x >= 55 ? 'market-score--soft' : 'market-score--risk';
  }

  function catalogRow(row){
    const ticker = text(row?.ticker);
    const score = number(row?.etf_score);
    const ter = ratioToPct(row?.expense_ratio);
    const coverage = number(row?.etf_score_coverage_pct);
    const meta = [
      ter != null ? `TER ${ter.toFixed(2)}%` : '',
      text(row?.fund_region ?? row?.region),
      score == null ? `Por avaliar${coverage != null ? ` · dados ${Math.round(coverage)}%` : ''}` : '',
    ].filter(Boolean).join(' · ');
    return `<div class="market-row" data-market-ticker="${escapeHtml(ticker)}">
      <div><div class="market-row__title"><span class="market-row__ticker">${escapeHtml(ticker)}</span><span class="market-row__name">${escapeHtml(row?.name || '')}</span></div><div class="market-row__meta">${escapeHtml(meta)}</div></div>
      <div class="market-row__end"><div class="market-score ${scoreClass(score)}" title="ETF Score">${score == null ? '—' : Math.round(score)}</div></div>
    </div>`;
  }

  function renderFullCatalog(){
    if(typeof document === 'undefined') return;
    const root = document.getElementById('marketPrimary');
    const stocks = window.VestraMarketStaticUniverse?.getStocks?.() || [];
    if(!root || !stocks.length) return;
    const funds = stocks.filter(isFund).sort((a,b) => {
      const sa = number(a?.etf_score), sb = number(b?.etf_score);
      if(sa == null && sb == null) return text(a?.ticker).localeCompare(text(b?.ticker));
      if(sa == null) return 1;
      if(sb == null) return -1;
      return sb-sa;
    });
    const visible = funds.slice(0, catalogLimit);
    const more = visible.length < funds.length
      ? `<button type="button" class="market-etf-change-theme" data-vestra-etf-all-more>Mostrar mais · ${visible.length} de ${funds.length}</button>`
      : '';
    root.innerHTML = `<section class="market-section market-etf-discovery" data-vestra-etf-all-catalog>
      <div class="market-section__head"><div><h3>Todos os ETFs</h3><p>Catálogo completo, ordenado pelo ETF Score quando existe. Carregamento progressivo otimizado para iPhone.</p></div><button type="button" class="market-etf-change-theme" data-vestra-etf-all-back>Mudar tema</button></div>
      <div class="market-list">${visible.length ? visible.map(catalogRow).join('') : '<div class="market-empty">Sem ETFs encontrados.</div>'}</div>${more}
    </section>`;
  }

  function closestElement(target, selector){
    return target && typeof target.closest === 'function' ? target.closest(selector) : null;
  }

  function installCatalogInteraction(){
    if(typeof document === 'undefined') return;
    document.addEventListener('click', event => {
      const target = event.target;
      const all = closestElement(target, '[data-market-fund-theme="all"]');
      if(all){
        event.preventDefault();
        event.stopImmediatePropagation();
        catalogLimit = CATALOG_BATCH;
        renderFullCatalog();
        return;
      }
      const more = closestElement(target, '[data-vestra-etf-all-more]');
      if(more){
        event.preventDefault();
        event.stopImmediatePropagation();
        catalogLimit += CATALOG_BATCH;
        renderFullCatalog();
        return;
      }
      const back = closestElement(target, '[data-vestra-etf-all-back]');
      if(back){
        event.preventDefault();
        event.stopImmediatePropagation();
        const fundsMode = document.querySelector('[data-market-mode="funds"]');
        if(fundsMode && typeof fundsMode.click === 'function') fundsMode.click();
      }
    }, true);
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
  installCatalogInteraction();
  if(typeof window !== 'undefined') window.addEventListener('vestra:market-ready', annotateDiscovery);

  window.VestraEtfIntelligence = Object.freeze({
    assess,
    enrichStocks,
    isFund,
    rankVisibleFundLists,
    renderFullCatalog,
    version: '1.2',
  });
})();
