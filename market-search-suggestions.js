/* Vestra Market Search Suggestions v1.3 — local rerenders preserve global results; explicit hide clears all. */
(() => {
  'use strict';

  function create(options={}){
    const getStocks = typeof options.getStocks === 'function' ? options.getStocks : () => [];
    const getQuery = typeof options.getQuery === 'function' ? options.getQuery : () => '';
    const isLoaded = typeof options.isLoaded === 'function' ? options.isLoaded : () => false;
    const getBox = typeof options.getBox === 'function' ? options.getBox : () => null;
    const text = typeof options.text === 'function' ? options.text : v => String(v ?? '').trim();
    const number = typeof options.number === 'function' ? options.number : v => {
      if(v === null || v === undefined || v === '') return null;
      const x = Number(v); return Number.isFinite(x) ? x : null;
    };
    const escapeHtml = typeof options.escapeHtml === 'function' ? options.escapeHtml : text;
    const isFund = typeof options.isFund === 'function' ? options.isFund : () => false;

    // Search relevance is identification, not an investment-quality ranking.
    // Normalise diacritics and whitespace without altering displayed names.
    const fold = value => text(value).toLowerCase().normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ');
    function matches(query, limit=7){
      const q=fold(query);
      if(!q || !Number.isFinite(limit) || limit<=0) return [];
      const rank=x=>{
        const ticker=fold(x.ticker), name=fold(x.name);
        if(ticker===q) return 1000;
        if(ticker.startsWith(q)) return 900;
        if(name===q) return 850;
        if(name.startsWith(q)) return 750;
        if(name.split(/[^a-z0-9]+/).some(word=>word.startsWith(q))) return 650;
        if(ticker.includes(q)) return 500;
        if(name.includes(q)) return 350;
        return 0;
      };
      return getStocks().map(x=>({x,rank:rank(x)})).filter(item=>item.rank>0)
        .sort((a,b)=>b.rank-a.rank ||
          fold(a.x.name).localeCompare(fold(b.x.name),'en') ||
          fold(a.x.ticker).localeCompare(fold(b.x.ticker),'en'))
        .slice(0,Math.floor(limit)).map(item=>item.x);
    }

    function globalHost(box){
      return typeof box?.querySelector === 'function' ? box.querySelector(':scope > .vestra-global-search') : null;
    }

    function localHost(box, create=false){
      if(typeof box?.querySelector !== 'function') return box;
      let host=box.querySelector(':scope > .vestra-local-search');
      if(!host && create && typeof document?.createElement === 'function'){
        host=document.createElement('div');
        host.className='vestra-local-search';
        const global=globalHost(box);
        if(global && typeof box.insertBefore === 'function') box.insertBefore(host,global);
        else if(typeof box.prepend === 'function') box.prepend(host);
        else if(typeof box.appendChild === 'function') box.appendChild(host);
      }
      return host;
    }

    function hide(){
      const box=getBox(); if(!box) return;
      box.hidden=true;
      box.innerHTML='';
    }

    function render(){
      const box=getBox(); if(!box || !isLoaded()) return;
      const q=text(getQuery());
      if(!q){ hide(); return; }
      const rows=matches(q,7);
      const host=localHost(box,true);
      if(!host) return;
      if(!rows.length){
        host.innerHTML='<div class="market-suggestion-empty">Sem correspondências imediatas</div>';
        box.hidden=false; return;
      }
      host.innerHTML=rows.map(x=>`<button type="button" class="market-suggestion" role="option" data-market-ticker="${escapeHtml(x.ticker)}"><span class="market-suggestion__ticker">${escapeHtml(x.ticker)}</span><span class="market-suggestion__name">${escapeHtml(x.name||'')}</span><span class="market-suggestion__type">${escapeHtml(isFund(x)?'ETF/Fundo':x.sector||'Ação')}</span></button>`).join('');
      box.hidden=false;
    }

    return Object.freeze({ matches, hide, render });
  }

  window.VestraMarketSearchSuggestions = Object.freeze({ create, version:'1.3' });
})();
