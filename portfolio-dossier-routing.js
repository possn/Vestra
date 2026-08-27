/* Vestra Portfolio Dossier Routing v1.0 — canonical row-to-dossier routing inside portfolio analysis. */
(()=>{'use strict';
const VERSION='1.0';
const t=v=>String(v??'').trim();
function root(){const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');return(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c}
const looksTicker=v=>/^[A-Z0-9][A-Z0-9.\-]{0,14}$/i.test(t(v))&&!/^(EUR|USD|GBP|JPY|CHF|CNY)$/i.test(t(v));
function tickerFrom(el){if(!el)return'';const direct=t(el.dataset?.marketTicker);if(direct)return direct.toUpperCase();const candidates=[...el.querySelectorAll('strong,b,.market-row__ticker')].map(x=>t(x.textContent).split(/\s|·/)[0]).filter(looksTicker);return(candidates[0]||'').toUpperCase()}
function decorate(){const c=root();if(!c)return;const selectors=['.market-row','.market-action-row','.market-fresh-row','.market-rebalance-row','.market-research-queue-main','.ux475-trade','.ux475-toprow','[data-ux-kind="reinforce"] .market-row','[data-ux-kind="review"] .market-row','[data-ux-kind="swap"] .market-row','[data-ux-kind="scenario"] button'];for(const el of c.querySelectorAll(selectors.join(','))){if(el.dataset.marketTicker)continue;const tk=tickerFrom(el);if(tk)el.dataset.marketTicker=tk}}
function isControl(target,row){const ctl=target.closest?.('a,input,select,textarea,[data-market-watch],[data-collapse-toggle],.market-collapse-toggle,[data-queue-status],[data-vpu-toggle],[data-vpu-tab],[data-vpu-detail]');return !!(ctl&&ctl!==row)}
document.addEventListener('click',e=>{const c=root();if(!c||!c.contains(e.target))return;let row=e.target.closest?.('[data-market-ticker],.market-row,.market-action-row,.market-fresh-row,.market-rebalance-row,.market-research-queue-main');if(!row||!c.contains(row)||isControl(e.target,row))return;if(!row.dataset.marketTicker){const tk=tickerFrom(row);if(tk)row.dataset.marketTicker=tk}},true);
function start(){decorate();let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;decorate()})}).observe(document.body,{childList:true,subtree:true})}
window.VestraPortfolioDossierRouting={version:VERSION,tickerFrom,decorate};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();})();