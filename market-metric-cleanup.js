/* Vestra Market Metric Cleanup v1.0 — canonical display normalization for invalid multiples. */
(() => {
'use strict';
const t=v=>String(v??'').trim();
function ptNum(x){const z=t(x).replace(/\s/g,'').replace(/\./g,'').replace(',','.').replace(/[^0-9+\-.]/g,'');const v=Number(z);return Number.isFinite(v)?v:null}
function repair(){const labels=new Set(['P/E','Forward P/E','EV/EBITDA','PEG']);document.querySelectorAll('.market-metric').forEach(card=>{const l=t(card.querySelector('small')?.textContent),v=card.querySelector('strong');if(!labels.has(l)||!v)return;const x=ptNum(v.textContent);if(x!=null&&x<=0)v.textContent='—'})}
function start(){repair();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;repair()})});mo.observe(document.body,{childList:true,subtree:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
window.VestraMarketMetricCleanup=Object.freeze({ptNum,refresh:repair,version:'1.0'});
})();
