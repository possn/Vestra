/* Vestra Market Company Brief v2.1 — canonical dossier/company description repair + dossier normalization pipeline. */
(() => {
'use strict';
const SCRIPT_LOAD_TIMEOUT_MS=8000;
const t=v=>String(v??'').trim();
function marketStock(ticker){const api=window.VestraMarket;if(!api?.resolvePortfolioStock)return null;const tk=t(ticker).toUpperCase();if(!tk)return null;return api.resolvePortfolioStock({ticker:tk,yahooTicker:tk,symbol:tk,class:'Ações'})||null}
function brief(s){const d=t(s?.business_summary||s?.longBusinessSummary||s?.long_business_summary||s?.description||s?.company_description);if(d)return d;const i=t(s?.industry),sec=t(s?.sector),c=t(s?.country);if(i&&sec&&i.toLowerCase()!==sec.toLowerCase())return`Empresa do setor ${sec}, com atividade principal em ${i}.`;if(i)return`Empresa com atividade principal em ${i}.`;if(sec)return`Empresa integrada no setor ${sec}.`;if(c)return`Empresa cotada com sede/atividade principal em ${c}.`;return'Empresa cotada acompanhada pelo universo Vestra.'}
function repair(){const sh=document.getElementById('marketSheet');if(!sh||sh.hidden)return;const tk=t(sh.dataset.ticker).toUpperCase();if(!tk)return;const s=marketStock(tk);if(!s)return;const info=sh.querySelector('.market-detail-head > div:first-child');if(!info)return;let node=info.querySelector('.market-company-brief');if(!node){node=document.createElement('div');node.className='market-company-brief';const name=info.querySelector('.market-title-line + p')||info.querySelector('p');name?name.insertAdjacentElement('afterend',node):info.appendChild(node)}const d=brief(s);if(node.textContent!==d)node.textContent=d}
function refreshDossier(){repair();window.VestraMarketMetricCleanup?.refresh?.();window.VestraMarketDossierControls?.normalizeButtons?.()}
function style(){if(document.getElementById('vestra-market-company-brief-style'))return;const link=document.createElement('link');link.id='vestra-market-company-brief-style';link.rel='stylesheet';link.href='market-company-brief.css?v=1.0';document.head.appendChild(link)}
function loadScript(id,src,ready,onload,attempt=0){
  const isReady=()=>typeof ready==='function'?!!ready():!!ready;
  if(isReady()){if(onload)onload();return;}
  const existing=document.getElementById(id);
  const s=existing||document.createElement('script');
  let settled=false;
  let timeoutId=null;
  const cleanup=()=>{
    if(timeoutId!==null&&typeof clearTimeout==='function')clearTimeout(timeoutId);
    s.removeEventListener('load',onLoad);
    s.removeEventListener('error',onError);
  };
  const retry=()=>{
    if(attempt<1&&typeof setTimeout==='function')setTimeout(()=>loadScript(id,src,ready,onload,attempt+1),1000);
  };
  const fail=()=>{
    if(settled)return;
    settled=true;
    cleanup();
    if(s.isConnected)s.remove();
    retry();
  };
  const onLoad=()=>{
    if(settled)return;
    if(!isReady()){fail();return;}
    settled=true;
    cleanup();
    if(onload)onload();
  };
  const onError=()=>fail();
  s.addEventListener('load',onLoad,{once:true});
  s.addEventListener('error',onError,{once:true});
  if(typeof setTimeout==='function')timeoutId=setTimeout(fail,SCRIPT_LOAD_TIMEOUT_MS);
  if(!existing){s.id=id;s.src=src;s.defer=true;document.head.appendChild(s)}
}
function loadResearchDiagnostics(){loadScript('vestra-model-validation-script','market-model-validation.js?v=1.0',()=>window.VestraModelValidation)}
function loadCanonicalQuoteRepair(){loadScript('vestra-canonical-quote-repair-script','quote-canonical-repair.js?v=2.3',()=>window.VestraAssetIdentityGuard||window.VestraCanonicalQuoteRepair)}
function loadDossierControls(){loadScript('vestra-market-dossier-controls-script','market-dossier-controls.js?v=1.6',()=>window.VestraMarketDossierControls,()=>window.VestraMarketDossierControls?.normalizeButtons?.())}
function loadGlobalMarketSearch(){loadScript('vestra-global-market-search-script','market-global-search.js?v=1.7',()=>window.VestraGlobalMarketSearch)}
function loadLearnedUniverse(){loadScript('vestra-learned-universe-script','market-learned-universe.js?v=2.1',()=>window.VestraLearnedUniverse,loadGlobalMarketSearch)}
function loadAppUpdateManager(){loadScript('vestra-app-update-manager-script','app-update-manager.js?v=1.5',()=>window.VestraAppUpdateManager)}
function loadDataHealth(){loadScript('vestra-market-data-health-script','market-data-health.js?v=1.3',()=>window.VestraMarketDataHealth)}
function loadRuntimeBridge(){loadScript('vestra-runtime-bridge-script','app-runtime-bridge.js?v=1.1',()=>window.VestraRuntimeBridge,()=>{loadAppUpdateManager();loadLearnedUniverse();})}
function start(){style();loadResearchDiagnostics();loadDataHealth();refreshDossier();const sh=document.getElementById('marketSheet');if(!sh)return;let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;refreshDossier()})});mo.observe(sh,{childList:true,subtree:true})}
loadCanonicalQuoteRepair();
loadDossierControls();
loadRuntimeBridge();
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
window.VestraMarketCompanyBrief=Object.freeze({brief,refresh:refreshDossier,scriptLoadTimeoutMs:SCRIPT_LOAD_TIMEOUT_MS,version:'2.1'});
})();