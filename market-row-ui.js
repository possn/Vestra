/* Vestra Market Row UI v1.0 */
(() => {
  'use strict';

  function create(options={}){
    const text = typeof options.text === 'function' ? options.text : v => String(v ?? '').trim();
    const number = typeof options.number === 'function' ? options.number : v => {
      if(v === null || v === undefined || v === '') return null;
      const x=Number(v); return Number.isFinite(x) ? x : null;
    };
    const escapeHtml = typeof options.escapeHtml === 'function' ? options.escapeHtml : text;
    const getGeneratedAt = typeof options.getGeneratedAt === 'function' ? options.getGeneratedAt : () => '';
    const inPortfolio = typeof options.inPortfolio === 'function' ? options.inPortfolio : () => false;
    const isWatched = typeof options.isWatched === 'function' ? options.isWatched : () => false;
    const changeBadge = typeof options.changeBadge === 'function' ? options.changeBadge : () => '';

    function isFund(s){
      const q = text(s?.quote_type).toUpperCase();
      const name = text(s?.name).toUpperCase();
      return q === 'ETF' || q === 'MUTUALFUND' || /\bETF\b|ISHARES|VANGUARD|XTRACKERS|SPDR|LYXOR|AMUNDI|WISDOMTREE|INVESCO/.test(name);
    }

    function scoreClass(value){
      const x=number(value);
      return x==null ? 'market-score--soft' : x>=70 ? '' : x>=55 ? 'market-score--soft' : 'market-score--risk';
    }

    function ageText(){
      const raw=getGeneratedAt();
      const d = raw ? new Date(raw) : null;
      if(!d || Number.isNaN(d.valueOf())) return '';
      return `Dados ${new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'short'}).format(d)}`;
    }

    function renderRow(s, meta='', displayScore=null){
      const thesis = text(s?.thesis_type) || text(s?.sector) || 'Sem classificação';
      const sub = meta || [text(s?.sector), thesis].filter(Boolean).join(' · ');
      const ticker=text(s?.ticker);
      const held=inPortfolio(ticker), watched=isWatched(ticker);
      const shownScore=displayScore ?? s?.score;
      return `<div class="market-row" data-market-ticker="${escapeHtml(ticker)}">
      <div><div class="market-row__title"><span class="market-row__ticker">${escapeHtml(ticker)}</span>${held?'<span class="market-held-badge">Carteira</span>':''}<span class="market-row__name">${escapeHtml(s?.name||'')}</span></div><div class="market-row__meta">${escapeHtml(sub)}</div>${(held||watched)?changeBadge(s):''}</div>
      <div class="market-row__end"><button class="market-watch ${watched?'is-active':''}" data-market-watch="${escapeHtml(ticker)}" aria-label="${watched?'Remover da lista':'Guardar para acompanhar'}" title="${watched?'A acompanhar':'Acompanhar'}">${watched?'★':'☆'}</button><div class="market-score ${scoreClass(shownScore)}">${number(shownScore)==null?'—':Math.round(number(shownScore))}</div></div>
    </div>`;
    }

    return Object.freeze({ isFund, scoreClass, ageText, renderRow });
  }

  window.VestraMarketRowUI = Object.freeze({ create, version:'1.0' });
})();
