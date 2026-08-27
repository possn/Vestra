/* Vestra Portfolio Dossier Routing v1.1 — canonical row-to-dossier routing inside portfolio analysis. */
(()=>{'use strict';
const VERSION='1.1';
const t=v=>String(v??'').trim();
function root(){const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');return(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c}
const looksTicker=v=>/^[A-Z0-9][A-Z0-9.\-]{0,14}$/i.test(t(v))&&!/^(EUR|USD|GBP|JPY|CHF|CNY)$/i.test(t(v));
function tickerFrom(el){if(!el)return'';const direct=t(el.dataset?.marketTicker);if(direct)return direct.toUpperCase();const candidates=[...el.querySelectorAll('strong,b,.market-row__ticker')].map(x=>t(x.textContent).split(/\s|·/)[0]).filter(looksTicker);return(candidates[0]||'').toUpperCase()}
function decorate(){const c=root();if(!c)return;const selectors=['.market-row','.market-action-row','.market-fresh-row','.market-rebalance-row','.market-research-queue-main','.ux475-trade','.ux475-toprow','[data-ux-kind="reinforce"] .market-row','[data-ux-kind="review"] .market-row','[data-ux-kind="swap"] .market-row','[data-ux-kind="scenario"] button'];for(const el of c.querySelectorAll(selectors.join(','))){if(!el.dataset.marketTicker){const tk=tickerFrom(el);if(tk)el.dataset.marketTicker=tk}if(el.dataset.marketTicker){el.classList.add('portfolio-dossier-link');if(!el.getAttribute('title'))el.setAttribute('title',`Abrir dossier de ${el.dataset.marketTicker}`)}}}
function isControl(target,row){const ctl=target.closest?.('a,input,select,textarea,[data-market-watch],[data-collapse-toggle],.market-collapse-toggle,[data-queue-status],[data-vpu-toggle],[data-vpu-tab],[data-vpu-detail]');return !!(ctl&&ctl!==row)}
function openTicker(ticker){const tk=t(ticker).toUpperCase();if(!tk)return false;const hydrate=window.VestraMarketData?.hydrateTicker;const open=()=>window.VestraMarket?.openTicker?.(tk);if(hydrate){Promise.resolve(hydrate(tk)).finally(open)}else open();return true}
document.addEventListener('click',e=>{const c=root();if(!c||!c.contains(e.target))return;let row=e.target.closest?.('[data-market-ticker],.market-row,.market-action-row,.market-fresh-row,.market-rebalance-row,.market-research-queue-main');if(!row||!c.contains(row)||isControl(e.target,row))return;let tk=t(row.dataset.marketTicker);if(!tk){tk=tickerFrom(row);if(tk)row.dataset.marketTicker=tk}if(!tk)return;
  // market-data-loader runs earlier in capture phase. Rows that already had a
  // ticker are handled there. This fallback is for dynamically generated
  // portfolio suggestions that only become routable on this click.
  e.preventDefault();e.stopImmediatePropagation();openTicker(tk)
},true);
document.addEventListener('keydown',e=>{if(e.key!=='Enter'&&e.key!==' ')return;const c=root();if(!c||!c.contains(e.target))return;const row=e.target.closest?.('.portfolio-dossier-link');if(!row||isControl(e.target,row))return;const tk=t(row.dataset.marketTicker)||tickerFrom(row);if(!tk)return;e.preventDefault();openTicker(tk)},true);
function start(){decorate();let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;decorate()})}).observe(document.body,{childList:true,subtree:true})}
window.VestraPortfolioDossierRouting={version:VERSION,tickerFrom,decorate,openTicker};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();})();