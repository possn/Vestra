/* Vestra Portfolio Sheet Navigation v1.2 — canonical dossier open origin + portfolio close/return rules. */
(() => {
  'use strict';
  const VERSION='1.2';
  let pending=false;
  let openingFromPortfolio=false;
  let navigationSequence=0;

  const txt=v=>String(v??'').trim();
  const sheet=()=>document.getElementById('marketSheet');
  const content=()=>document.getElementById('marketSheetContent');
  const normalizeTicker=value=>txt(value).toUpperCase();

  function inferOrigin(node){
    const sh=sheet(), c=content();
    if(node && sh && !sh.hidden && sh.dataset.tool==='portfolio' && c?.contains(node)) return 'portfolio';
    return 'market';
  }

  function applyDossierOrigin(origin){
    const sh=sheet();
    if(!sh || sh.hidden || !sh.dataset.ticker) return;
    if(origin==='portfolio'){
      sh.dataset.tool='ticker-from-portfolio';
      sh.dataset.returnView='portfolio';
      openingFromPortfolio=false;
      cleanupPortfolioChrome();
      return;
    }
    if(sh.dataset.tool==='ticker-from-portfolio') sh.dataset.tool='';
    if(sh.dataset.returnView==='portfolio') sh.dataset.returnView='';
  }

  async function openCompany(ticker,options={}){
    const tk=normalizeTicker(ticker);
    if(!tk) return false;
    const origin=txt(options.origin)||inferOrigin(options.sourceNode);
    const request=++navigationSequence;

    try{
      const hydrate=window.VestraMarketData?.hydrateTicker;
      if(hydrate) await Promise.resolve(hydrate(tk));
      if(request!==navigationSequence) return false;

      const api=window.VestraMarket;
      if(!api?.openTicker) return false;
      await Promise.resolve(api.openTicker(tk));
      if(request!==navigationSequence) return false;
    }catch(err){
      console.error('Vestra navigation openCompany',err);
      return false;
    }

    applyDossierOrigin(origin);
    return true;
  }

  function cleanupPortfolioChrome(){
    const sh=sheet(), c=content();
    if(!sh||!c||!sh.dataset.ticker) return;
    c.querySelectorAll('.market-collapse-toolbar').forEach(x=>x.remove());
    c.querySelectorAll('.market-collapse-toggle').forEach(x=>x.remove());
    c.querySelectorAll('.market-detail-card[data-collapsible="1"]').forEach(card=>{
      card.classList.remove('is-collapsed');
      card.removeAttribute('data-collapsible');
      card.removeAttribute('data-collapse-key');
    });
  }

  function markTickerFromPortfolio(){
    const sh=sheet();
    if(!sh||sh.hidden||!sh.dataset.ticker) return;
    if(openingFromPortfolio || sh.dataset.tool==='portfolio' || sh.dataset.returnView==='assets'){
      applyDossierOrigin('portfolio');
    }
  }

  function reopenPortfolioAnalysis(){
    const trigger=document.querySelector('[data-market-tool="portfolio"], .market-portfolio-access');
    if(!trigger) return false;
    trigger.click();
    requestAnimationFrame(()=>{
      const sh=sheet();
      if(sh){ sh.dataset.tool='portfolio'; sh.dataset.returnView='assets'; }
    });
    return true;
  }

  function closePortfolioToMarket(){
    const sh=sheet();
    if(!sh || sh.hidden || sh.dataset.tool!=='portfolio' || sh.dataset.ticker) return false;
    sh.hidden=true;
    sh.setAttribute('aria-hidden','true');
    sh.dataset.liveReady='0';
    sh.dataset.tool='';
    sh.dataset.returnView='';
    document.documentElement.classList.remove('modal-open');
    document.body.classList.remove('modal-open');
    sh.scrollTop=0; sh.scrollLeft=0;
    document.querySelectorAll('[data-view]').forEach(el=>{
      if(el.dataset.view==='market') el.classList.add('is-active');
      else if(el.dataset.view==='assets') el.classList.remove('is-active');
    });
    return true;
  }

  function normalizeCloseChrome(){
    const sh=sheet(), c=content(); if(!sh||!c)return;
    const persistent=sh.querySelector(':scope > [data-market-close].market-close-persistent');
    if(persistent){ persistent.hidden=false; persistent.setAttribute('aria-label','Fechar'); }
    c.querySelectorAll('.market-detail-head [data-market-close]').forEach(btn=>{
      btn.setAttribute('aria-hidden','true');
      btn.tabIndex=-1;
    });
  }

  function repair(){
    const sh=sheet();
    normalizeCloseChrome();
    if(!sh||sh.hidden) return;
    if(sh.dataset.ticker){
      markTickerFromPortfolio();
      cleanupPortfolioChrome();
    }
  }

  function style(){
    if(document.getElementById('vestra-portfolio-sheet-navigation-style'))return;
    const s=document.createElement('style');
    s.id='vestra-portfolio-sheet-navigation-style';
    s.textContent='#marketSheet:not([hidden]) #marketSheetContent .market-detail-head [data-market-close]{display:none!important}';
    document.head.appendChild(s);
  }

  document.addEventListener('click',e=>{
    const sh=sheet();
    if(!sh) return;

    const ticker=e.target.closest?.('[data-market-ticker]');
    if(ticker && !sh.hidden && sh.dataset.tool==='portfolio' && content()?.contains(ticker)){
      openingFromPortfolio=true;
      setTimeout(markTickerFromPortfolio,0);
      setTimeout(markTickerFromPortfolio,40);
      return;
    }

    const close=e.target.closest?.('[data-market-close]');
    if(!close || sh.hidden) return;

    if(sh.dataset.ticker && sh.dataset.returnView==='portfolio'){
      e.preventDefault();
      e.stopImmediatePropagation();
      reopenPortfolioAnalysis();
      return;
    }

    if(sh.dataset.tool==='portfolio' && !sh.dataset.ticker){
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      closePortfolioToMarket();
    }
  },true);

  function start(){
    style(); repair();
    const mo=new MutationObserver(()=>{
      if(pending)return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;repair();});
    });
    mo.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','class']});
  }

  window.VestraNavigation=Object.freeze({version:VERSION,normalizeTicker,inferOrigin,applyDossierOrigin,openCompany});
  window.VestraPortfolioSheetNavigation={version:VERSION,repair,reopenPortfolioAnalysis,closePortfolioToMarket,openCompany};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();
