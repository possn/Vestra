/* Vestra Portfolio Sector Explorer v1.0 — sector drilldown for owned equities. */
(() => {
  'use strict';

  const t = v => String(v ?? '').trim();
  const n = v => {
    if (v === null || v === undefined || v === '') return null;
    const x = Number(v);
    return Number.isFinite(x) ? x : null;
  };
  const esc = v => t(v).replace(/[&<>"']/g, ch => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[ch]));

  let activeSector = '';
  let scheduled = false;

  function root() {
    const sh = document.getElementById('marketSheet');
    const c = document.getElementById('marketSheetContent');
    return (!sh || sh.hidden || t(sh.dataset.tool) !== 'portfolio' || !c) ? null : c;
  }

  function state() {
    try { return window.VestraRuntimeBridge?.getState?.() || window.state || null; }
    catch (_) { return null; }
  }

  function normalizeTicker(v) { return t(v).toUpperCase(); }
  function normalizeIsin(v) { return t(v).toUpperCase().replace(/\s+/g, ''); }

  function assetTicker(asset) {
    return normalizeTicker(asset?.yahooTicker || asset?.ticker || asset?.symbol);
  }

  function resolveStock(asset) {
    try {
      return window.VestraMarket?.resolvePortfolioStock?.(asset) || null;
    } catch (_) {
      return null;
    }
  }

  function isOwnedEquity(asset, stock) {
    const cls = t(asset?.class).toLowerCase();
    const qt = t(stock?.quote_type || stock?.quoteType).toUpperCase();
    if (!asset || !(n(asset.value) > 0)) return false;
    if (/cripto|crypto/.test(cls)) return false;
    if (/\betf\b|\bfund\b|fundo/.test(cls)) return false;
    if (['ETF','FUND','MUTUALFUND','CRYPTO'].includes(qt)) return false;
    if (qt === 'EQUITY') return true;
    return /a[cç][oõ]es|equity|stock/.test(cls);
  }

  function eventMatchesAsset(event, asset, stock) {
    if (!event || !asset) return false;
    const assetIsin = normalizeIsin(asset.isin || asset.ISIN);
    const eventIsin = normalizeIsin(event.isin || event.ISIN);
    if (assetIsin && eventIsin) return assetIsin === eventIsin;

    const ids = new Set([
      normalizeTicker(stock?.ticker),
      normalizeTicker(asset?.yahooTicker),
      normalizeTicker(asset?.ticker),
      normalizeTicker(asset?.symbol),
    ].filter(Boolean));
    const eventIds = [
      normalizeTicker(event?.yahooTicker),
      normalizeTicker(event?.ticker),
      normalizeTicker(event?.symbol),
    ].filter(Boolean);
    return eventIds.some(id => ids.has(id));
  }

  function firstBuyDate(asset, stock, events) {
    const dates = (events || [])
      .filter(e => e?.type === 'BUY' && eventMatchesAsset(e, asset, stock))
      .map(e => t(e.date || e.dateTime).slice(0, 10))
      .filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d))
      .sort();
    if (dates.length) return dates[0];
    const fallback = t(asset?.purchaseDate || asset?.acquisitionDate || asset?.buyDate).slice(0,10);
    return /^\d{4}-\d{2}-\d{2}$/.test(fallback) ? fallback : '';
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso + 'T12:00:00');
    if (!Number.isFinite(d.getTime())) return '—';
    return new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short',year:'numeric'}).format(d);
  }
  function eur(v, digits=0) {
    const x=n(v); if (x == null) return '—';
    return new Intl.NumberFormat('pt-PT',{style:'currency',currency:'EUR',minimumFractionDigits:digits,maximumFractionDigits:digits}).format(x);
  }
  function pct(v) {
    const x=n(v); if (x == null) return '—';
    const sign=x>0?'+':'';
    return sign + new Intl.NumberFormat('pt-PT',{minimumFractionDigits:1,maximumFractionDigits:1}).format(x) + '%';
  }
  function qty(v) {
    const x=n(v); if (x == null) return '—';
    return new Intl.NumberFormat('pt-PT',{maximumFractionDigits:6}).format(x);
  }

  function position(asset, stock, events) {
    const value = n(asset.value) ?? n(asset.marketValueEUR) ?? 0;
    const cost = n(asset.costBasis);
    const q = n(asset.qty);
    const gain = cost != null && cost > 0 ? value - cost : null;
    const gainPct = gain != null && cost > 0 ? gain / cost * 100 : null;
    const avgCost = cost != null && cost > 0 && q != null && q > 0 ? cost / q : null;
    return {
      asset, stock,
      ticker: normalizeTicker(stock?.ticker || assetTicker(asset)),
      name: t(stock?.name || stock?.short_name || asset?.name || assetTicker(asset)),
      sector: t(stock?.sector) || 'Sem sector',
      value, cost, q, gain, gainPct, avgCost,
      firstBuy: firstBuyDate(asset, stock, events),
    };
  }

  function buildModel() {
    const s = state();
    const assets = Array.isArray(s?.assets) ? s.assets : [];
    const events = Array.isArray(s?.brokerData?.events) ? s.brokerData.events : [];
    const rows = [];
    for (const asset of assets) {
      const stock = resolveStock(asset);
      if (!isOwnedEquity(asset, stock)) continue;
      rows.push(position(asset, stock, events));
    }
    const total = rows.reduce((sum,r)=>sum+r.value,0);
    const groups = new Map();
    for (const row of rows) {
      const key = row.sector;
      if (!groups.has(key)) groups.set(key,[]);
      groups.get(key).push(row);
    }
    return [...groups.entries()].map(([sector,positions]) => {
      positions.sort((a,b)=>b.value-a.value);
      const value=positions.reduce((s,r)=>s+r.value,0);
      const cost=positions.reduce((s,r)=>s+(r.cost ?? 0),0);
      const knownCost=positions.some(r=>r.cost!=null && r.cost>0);
      const gain=knownCost?value-cost:null;
      const gainPct=knownCost&&cost>0?gain/cost*100:null;
      return {sector,positions,value,cost,gain,gainPct,weight:total>0?value/total*100:0};
    }).sort((a,b)=>b.value-a.value);
  }

  function tone(v) {
    const x=n(v); if (x == null || Math.abs(x) < 0.005) return 'neutral';
    return x > 0 ? 'positive' : 'negative';
  }

  function sectorCard(g) {
    const selected = activeSector === g.sector;
    return `<button type="button" class="vpse-sector${selected?' is-active':''}" data-vpse-sector="${esc(g.sector)}" aria-expanded="${selected?'true':'false'}">
      <span><strong>${esc(g.sector)}</strong><small>${g.positions.length} ${g.positions.length===1?'posição':'posições'} · ${pct(g.weight)} da carteira em ações</small></span>
      <span class="vpse-sector-value"><b>${eur(g.value)}</b><em class="is-${tone(g.gain)}">${g.gain==null?'P/L —':`${g.gain>=0?'+':''}${eur(g.gain)} · ${pct(g.gainPct)}`}</em></span>
    </button>`;
  }

  function positionRow(r) {
    return `<button type="button" class="vpse-position portfolio-dossier-link" data-market-ticker="${esc(r.ticker)}">
      <span class="vpse-position-main"><strong>${esc(r.ticker || r.name)}</strong><small>${esc(r.name)}</small></span>
      <span class="vpse-position-meta">
        <span><small>Primeira compra</small><b>${esc(fmtDate(r.firstBuy))}</b></span>
        <span><small>Qtd.</small><b>${qty(r.q)}</b></span>
        <span><small>Custo médio</small><b>${eur(r.avgCost,2)}</b></span>
        <span><small>Investido</small><b>${eur(r.cost)}</b></span>
        <span><small>Valor atual</small><b>${eur(r.value)}</b></span>
        <span><small>Ganho / perda</small><b class="is-${tone(r.gain)}">${r.gain==null?'—':`${r.gain>=0?'+':''}${eur(r.gain)} · ${pct(r.gainPct)}`}</b></span>
      </span>
      <span class="vpse-open" aria-hidden="true">›</span>
    </button>`;
  }

  function render() {
    const c = root();
    if (!c) return;
    const groups = buildModel();
    let section = c.querySelector('.vpse');
    if (!section) {
      section = document.createElement('section');
      section.className = 'vpse';
      const hero = c.querySelector('.vpu-overview');
      const anchor = c.querySelector('.vpu-reveal');
      if (hero) hero.insertAdjacentElement('afterend', section);
      else if (anchor) anchor.insertAdjacentElement('beforebegin', section);
      else c.prepend(section);
    }
    if (!groups.length) {
      section.innerHTML = '<div class="vpse-head"><div><small>SECTORES</small><strong>As tuas ações por sector</strong></div></div><p class="vpse-empty">Ainda não há ações com sector identificado.</p>';
      return;
    }
    if (activeSector && !groups.some(g=>g.sector===activeSector)) activeSector='';
    const selected = groups.find(g=>g.sector===activeSector);
    const signature = JSON.stringify(groups.map(g=>[
      g.sector,g.value,g.cost,g.gain,g.weight,
      ...g.positions.map(r=>[r.ticker,r.value,r.cost,r.q,r.firstBuy])
    ]).concat([activeSector]));
    if (section.dataset.signature === signature) return;
    section.dataset.signature = signature;
    section.innerHTML = `
      <div class="vpse-head">
        <div><small>SECTORES</small><strong>As tuas ações por sector</strong><span>Vê exposição, custo e resultado; toca numa ação para abrir o dossier Vestra.</span></div>
        <b>${groups.reduce((s,g)=>s+g.positions.length,0)} ações · ${groups.length} sectores</b>
      </div>
      <div class="vpse-grid">${groups.map(sectorCard).join('')}</div>
      ${selected ? `<div class="vpse-detail"><div class="vpse-detail-head"><strong>${esc(selected.sector)}</strong><span>${selected.positions.length} ${selected.positions.length===1?'posição':'posições'} · ${eur(selected.value)}</span></div><div class="vpse-list">${selected.positions.map(positionRow).join('')}</div></div>` : ''}
    `;
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled=false; render(); });
  }

  async function openTicker(ticker, sourceNode) {
    const tk=normalizeTicker(ticker); if(!tk)return false;
    let nav=window.VestraNavigation;
    if (nav?.openCompany) return nav.openCompany(tk,{origin:'portfolio',sourceNode});
    try { await window.VestraMarketLoader?.ensure?.(); } catch (_) {}
    nav=window.VestraNavigation;
    if (nav?.openCompany) return nav.openCompany(tk,{origin:'portfolio',sourceNode});
    return false;
  }

  document.addEventListener('click', e => {
    const sectorBtn=e.target.closest?.('[data-vpse-sector]');
    if (sectorBtn && root()?.contains(sectorBtn)) {
      e.preventDefault(); e.stopPropagation();
      const sector=t(sectorBtn.dataset.vpseSector);
      activeSector = activeSector===sector ? '' : sector;
      render();
      return;
    }
    const row=e.target.closest?.('.vpse-position[data-market-ticker]');
    if (row && root()?.contains(row)) {
      e.preventDefault(); e.stopImmediatePropagation();
      void openTicker(row.dataset.marketTicker,row);
    }
  }, true);

  function style() {
    if (document.getElementById('vestra-portfolio-sector-explorer-style')) return;
    const link=document.createElement('link');
    link.id='vestra-portfolio-sector-explorer-style';
    link.rel='stylesheet';
    link.href='portfolio-sector-explorer.css?v=1.0';
    document.head.appendChild(link);
  }

  function start() {
    style(); render();
    const sh=document.getElementById('marketSheet');
    if (sh) {
      const mo=new MutationObserver(schedule);
      mo.observe(sh,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','data-tool']});
    }
    window.addEventListener?.('vestra:market-ready',schedule);
    window.addEventListener?.('vestra:app-ready',schedule);
  }

  window.VestraPortfolioSectorExplorer=Object.freeze({
    refresh:render,
    buildModel,
    eventMatchesAsset,
    version:'1.0'
  });

  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();