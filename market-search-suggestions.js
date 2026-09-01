/* Vestra Market Search Suggestions v1.0 */
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

    function matches(query, limit=7){
      const q=text(query).toLowerCase();
      if(!q) return [];
      const scoreMatch=(x)=>{
        const t=text(x.ticker).toLowerCase(), name=text(x.name).toLowerCase();
        if(t===q) return 1000;
        if(t.startsWith(q)) return 800 - t.length;
        if(name.startsWith(q)) return 650 - name.length/100;
        if(t.includes(q)) return 500;
        if(name.includes(q)) return 350;
        return 0;
      };
      return getStocks().map(x=>({x,rank:scoreMatch(x)})).filter(r=>r.rank>0)
        .sort((a,b)=>b.rank-a.rank || (number(b.x.score)||0)-(number(a.x.score)||0))
        .slice(0,limit).map(r=>r.x);
    }

    function hide(){
      const box=getBox(); if(!box) return;
      box.hidden=true; box.innerHTML='';
    }

    function render(){
      const box=getBox(); if(!box || !isLoaded()) return;
      const q=text(getQuery());
      if(!q){ hide(); return; }
      const rows=matches(q,7);
      if(!rows.length){
        box.innerHTML='<div class="market-suggestion-empty">Sem correspondências imediatas</div>';
        box.hidden=false; return;
      }
      box.innerHTML=rows.map(x=>`<button type="button" class="market-suggestion" role="option" data-market-ticker="${escapeHtml(x.ticker)}"><span class="market-suggestion__ticker">${escapeHtml(x.ticker)}</span><span class="market-suggestion__name">${escapeHtml(x.name||'')}</span><span class="market-suggestion__type">${escapeHtml(isFund(x)?'ETF/Fundo':x.sector||'Ação')}</span></button>`).join('');
      box.hidden=false;
    }

    return Object.freeze({ matches, hide, render });
  }

  window.VestraMarketSearchSuggestions = Object.freeze({ create, version:'1.0' });
})();
