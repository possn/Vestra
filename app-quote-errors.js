/* Vestra Quote Errors v1.2 — classify failures and render diagnostics without locking the app. */
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

  function releaseBodyLock(modal) {
    if(modal) modal.setAttribute('aria-hidden','true');
    const anyOpen=[...document.querySelectorAll('.modal')]
      .some(m=>m!==modal && m.getAttribute('aria-hidden')==='false');
    if(!anyOpen) document.body.classList.remove('modal-open');
  }

  function closeQuoteErrorSheet() {
    const sheet=document.getElementById('quoteErrorSafeSheet');
    if(sheet) sheet.remove();
    releaseBodyLock(document.getElementById('modalQuoteErrors'));
  }

  function showQuoteErrorSheetFromModal() {
    const modal=document.getElementById('modalQuoteErrors');
    if(!modal) return false;
    const summary=document.getElementById('quoteErrorsSummary');
    const list=document.getElementById('quoteErrorsList');
    if(!summary && !list) return false;

    closeQuoteErrorSheet();
    releaseBodyLock(modal);

    const sheet=document.createElement('section');
    sheet.id='quoteErrorSafeSheet';
    sheet.setAttribute('role','region');
    sheet.setAttribute('aria-label','Erros de cotação');
    sheet.style.cssText='position:fixed;left:12px;right:12px;bottom:calc(14px + env(safe-area-inset-bottom));z-index:1002;max-height:min(72vh,720px);overflow:hidden;background:var(--card,#fff);color:var(--text,#0f2533);border:1px solid var(--line,#d7dfdc);border-radius:22px;box-shadow:0 18px 55px rgba(15,23,42,.28);display:flex;flex-direction:column;pointer-events:auto';

    const head=document.createElement('div');
    head.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px 12px;border-bottom:1px solid var(--line,#d7dfdc);flex:0 0 auto';
    const title=document.createElement('strong');
    title.textContent='⚠️ Erros de cotação';
    title.style.cssText='font-size:17px;line-height:1.2';
    const close=document.createElement('button');
    close.type='button';
    close.textContent='Fechar';
    close.setAttribute('aria-label','Fechar erros de cotação');
    close.style.cssText='border:0;border-radius:999px;padding:8px 13px;background:var(--line,#d7dfdc);color:var(--text,#0f2533);font:inherit;font-weight:800;cursor:pointer;touch-action:manipulation';
    close.addEventListener('click',closeQuoteErrorSheet);
    head.append(title,close);

    const body=document.createElement('div');
    body.style.cssText='overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding:14px 16px 18px;min-height:0';
    const summaryCopy=document.createElement('div');
    summaryCopy.style.cssText='font-weight:800;color:var(--muted,#58717b);line-height:1.45;margin-bottom:12px';
    summaryCopy.textContent=summary?.textContent||'';
    const listCopy=document.createElement('div');
    listCopy.innerHTML=list?.innerHTML||'<div class="note">Sem detalhes disponíveis.</div>';
    body.append(summaryCopy,listCopy);
    sheet.append(head,body);
    document.body.appendChild(sheet);
    return true;
  }

  // Defensive iOS/Safari close path for an already-open legacy modal.
  function forceCloseQuoteErrorsModal(event) {
    const target=event?.target;
    if(!(target instanceof Element)) return false;
    const trigger=target.closest('[data-close="modalQuoteErrors"]');
    if(!trigger) return false;
    releaseBodyLock(document.getElementById('modalQuoteErrors'));
    closeQuoteErrorSheet();
    event.preventDefault();
    event.stopImmediatePropagation();
    return true;
  }

  function installNonBlockingBridge() {
    const modal=document.getElementById('modalQuoteErrors');
    if(!modal) return;
    // Any legacy/openModal call is immediately converted into a small sheet.
    // This covers the toolbar button and clickable refresh toasts without
    // changing the large legacy app.js during the stability hotfix.
    const observer=new MutationObserver(()=>{
      if(modal.getAttribute('aria-hidden')==='false') showQuoteErrorSheetFromModal();
    });
    observer.observe(modal,{attributes:true,attributeFilter:['aria-hidden']});
    if(modal.getAttribute('aria-hidden')==='false') showQuoteErrorSheetFromModal();
  }

  document.addEventListener('click',forceCloseQuoteErrorsModal,true);
  document.addEventListener('keydown',event=>{
    if(event.key!=='Escape') return;
    closeQuoteErrorSheet();
  },true);
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',installNonBlockingBridge,{once:true});
  else installNonBlockingBridge();

  window.VestraQuoteErrors=Object.freeze({
    version:'1.2',
    classifyQuoteError,
    summarizeQuoteErrors,
    decorateQuoteError,
    showQuoteErrorSheetFromModal,
    closeQuoteErrorSheet
  });
})();
