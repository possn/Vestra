/* Vestra Portfolio → Dossier navigation repair v1.0 */
(() => {
  'use strict';
  const VERSION='1.0';
  let openingFromPortfolio=false;

  const sheet=()=>document.getElementById('marketSheet');
  const content=()=>document.getElementById('marketSheetContent');

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
      sh.dataset.tool='ticker-from-portfolio';
      sh.dataset.returnView='portfolio';
      openingFromPortfolio=false;
      cleanupPortfolioChrome();
    }
  }

  function reopenPortfolioAnalysis(){
    const trigger=document.querySelector('[data-market-tool="portfolio"], .market-portfolio-access');
    if(trigger){
      trigger.click();
      requestAnimationFrame(()=>{
        const sh=sheet();
        if(sh){ sh.dataset.tool='portfolio'; sh.dataset.returnView='assets'; }
      });
      return true;
    }
    return false;
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
    if(close && !sh.hidden && sh.dataset.ticker && sh.dataset.returnView==='portfolio'){
      e.preventDefault();
      e.stopImmediatePropagation();
      reopenPortfolioAnalysis();
    }
  },true);

  function repair(){
    const sh=sheet();
    if(!sh||sh.hidden) return;
    if(sh.dataset.ticker){
      markTickerFromPortfolio();
      cleanupPortfolioChrome();
    }
  }

  function start(){
    repair();
    let pending=false;
    const mo=new MutationObserver(()=>{
      if(pending)return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;repair();});
    });
    mo.observe(document.body,{childList:true,subtree:true});
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
