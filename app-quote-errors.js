/* Vestra Quote Errors v1.1 — classify quote refresh failures and keep diagnostics dismissible. */
(() => {
  'use strict';

  const RULES = [
    { key:'no_data', label:'Sem dados Yahoo', re:/sem dados|não foi possível obter uma cotação válida|no data|not found|404/i },
    { key:'identity', label:'Ticker / identidade', re:/ticker|isin|identidade|correspondência errada|sem ticker/i },
    { key:'delisted', label:'Delisted / ignorado', re:/delist|privat|acquired|merger|ignorado|skip/i },
    { key:'network', label:'Rede / Worker', re:/worker|tempo limite|timeout|http\s*5\d\d|inacessível|network|fetch/i },
    { key:'sanity', label:'Sanity de preço', re:/cotação suspeita|moeda .* não coincide|último preço fiável|cotação inválida/i },
  ];

  function classifyQuoteError(err) {
    const reason=String((err&&err.reason)||err||'').trim();
    for(const r of RULES) if(r.re.test(reason)) return { key:r.key, label:r.label };
    return { key:'other', label:'Outro' };
  }

  function summarizeQuoteErrors(errors) {
    const counts=new Map();
    for(const err of (Array.isArray(errors)?errors:[])) {
      const c=classifyQuoteError(err);
      const cur=counts.get(c.key)||{key:c.key,label:c.label,count:0};
      cur.count++;
      counts.set(c.key,cur);
    }
    return [...counts.values()].sort((a,b)=>b.count-a.count || a.label.localeCompare(b.label));
  }

  function decorateQuoteError(err) {
    const base=(err&&typeof err==='object')?{...err}:{reason:String(err||'')};
    const c=classifyQuoteError(base);
    return {...base, category:c.key, categoryLabel:c.label};
  }

  // Defensive iOS/Safari close path. The app has a generic delegated modal
  // closer, but quote diagnostics must never be able to trap the whole UI if
  // that listener is missed or an older cached runtime leaves the modal open.
  function forceCloseQuoteErrorsModal(event) {
    const target=event?.target;
    if(!(target instanceof Element)) return false;
    const trigger=target.closest('[data-close="modalQuoteErrors"]');
    if(!trigger) return false;
    const modal=document.getElementById('modalQuoteErrors');
    if(modal) modal.setAttribute('aria-hidden','true');
    const anyOpen=[...document.querySelectorAll('.modal')]
      .some(m=>m!==modal && m.getAttribute('aria-hidden')==='false');
    if(!anyOpen) document.body.classList.remove('modal-open');
    event.preventDefault();
    event.stopImmediatePropagation();
    return true;
  }

  document.addEventListener('click',forceCloseQuoteErrorsModal,true);
  document.addEventListener('keydown',event=>{
    if(event.key!=='Escape') return;
    const modal=document.getElementById('modalQuoteErrors');
    if(!modal || modal.getAttribute('aria-hidden')!=='false') return;
    modal.setAttribute('aria-hidden','true');
    const anyOpen=[...document.querySelectorAll('.modal')]
      .some(m=>m!==modal && m.getAttribute('aria-hidden')==='false');
    if(!anyOpen) document.body.classList.remove('modal-open');
  },true);

  window.VestraQuoteErrors=Object.freeze({ version:'1.1', classifyQuoteError, summarizeQuoteErrors, decorateQuoteError });
})();
