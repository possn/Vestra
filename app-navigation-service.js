/* Vestra Navigation Service v1.0 — single entry point for company dossier opening. */
(() => {
  'use strict';

  const VERSION='1.0';
  const txt=v=>String(v??'').trim();
  let sequence=0;

  function normalizeTicker(value){
    return txt(value).toUpperCase();
  }

  function inferOrigin(node){
    const sh=document.getElementById('marketSheet');
    const content=document.getElementById('marketSheetContent');
    if(node && sh && !sh.hidden && sh.dataset.tool==='portfolio' && content?.contains(node)) return 'portfolio';
    return 'market';
  }

  function applyOrigin(origin){
    const sh=document.getElementById('marketSheet');
    if(!sh || sh.hidden || !sh.dataset.ticker) return;
    if(origin==='portfolio'){
      sh.dataset.tool='ticker-from-portfolio';
      sh.dataset.returnView='portfolio';
      return;
    }
    if(sh.dataset.tool==='ticker-from-portfolio') sh.dataset.tool='';
    if(sh.dataset.returnView==='portfolio') sh.dataset.returnView='';
  }

  async function openCompany(ticker, options={}){
    const tk=normalizeTicker(ticker);
    if(!tk) return false;
    const origin=txt(options.origin)||inferOrigin(options.sourceNode);
    const api=window.VestraMarket;
    if(!api?.openTicker) return false;

    const request=++sequence;
    try{
      await Promise.resolve(api.openTicker(tk));
    }catch(err){
      console.error('Vestra navigation openCompany',err);
      return false;
    }
    if(request!==sequence) return false;
    applyOrigin(origin);
    return true;
  }

  window.VestraNavigation=Object.freeze({
    version:VERSION,
    normalizeTicker,
    inferOrigin,
    applyOrigin,
    openCompany
  });
})();
