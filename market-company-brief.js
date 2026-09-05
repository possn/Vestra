/* Vestra Market Company Brief v1.8 — canonical dossier/company description repair + runtime diagnostics bootstrap. */
(() => {
'use strict';
const t=v=>String(v??'').trim();
function marketStock(ticker){const api=window.VestraMarket;if(!api?.resolvePortfolioStock)return null;const tk=t(ticker).toUpperCase();if(!tk)return null;return api.resolvePortfolioStock({ticker:tk,yahooTicker:tk,symbol:tk,class:'Ações'})||null}
function brief(s){const d=t(s?.business_summary||s?.longBusinessSummary||s?.long_business_summary||s?.description||s?.company_description);if(d)return d;const i=t(s?.industry),sec=t(s?.sector),c=t(s?.country);if(i&&sec&&i.toLowerCase()!==sec.toLowerCase())return`Empresa do setor ${sec}, com atividade principal em ${i}.`;if(i)return`Empresa com atividade principal em ${i}.`;if(sec)return`Empresa integrada no setor ${sec}.`;if(c)return`Empresa cotada com sede/atividade principal em ${c}.`;return'Empresa cotada acompanhada pelo universo Vestra.'}
function repair(){const sh=document.getElementById('marketSheet');if(!sh||sh.hidden)return;const tk=t(sh.dataset.ticker).toUpperCase();if(!tk)return;const s=marketStock(tk);if(!s)return;const info=sh.querySelector('.market-detail-head > div:first-child');if(!info)return;let node=info.querySelector('.market-company-brief');if(!node){node=document.createElement('div');node.className='market-company-brief';const name=info.querySelector('.market-title-line + p')||info.querySelector('p');name?name.insertAdjacentElement('afterend',node):info.appendChild(node)}const d=brief(s);if(node.textContent!==d)node.textContent=d}
function style(){if(document.getElementById('vestra-market-company-brief-style'))return;const s=document.createElement('style');s.id='vestra-market-company-brief-style';s.textContent='.market-row__description{font-size:11px;line-height:1.4;color:var(--text2,#62757c);margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.market-company-brief{font-size:12px;line-height:1.45;color:var(--text2,#62757c);margin-top:5px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}';document.head.appendChild(s)}
function loadScript(id,src,ready,onload){if(ready||document.getElementById(id)){if(onload)onload();return;}const s=document.createElement('script');s.id=id;s.src=src;s.defer=true;if(onload)s.addEventListener('load',onload,{once:true});document.head.appendChild(s)}
function loadResearchDiagnostics(){loadScript('vestra-model-validation-script','market-model-validation.js?v=1.0',window.VestraModelValidation)}
function loadCanonicalQuoteRepair(){loadScript('vestra-canonical-quote-repair-script','quote-canonical-repair.js?v=2.3',window.VestraAssetIdentityGuard||window.VestraCanonicalQuoteRepair)}
function loadQuoteRefreshPerformance(){loadScript('vestra-quote-refresh-performance-script','quote-refresh-performance.js?v=1.0',window.VestraQuoteRefreshPerformance)}
function loadDossierControls(){loadScript('vestra-market-dossier-controls-script','market-dossier-controls.js?v=1.0',window.VestraMarketDossierControls)}
function loadGlobalMarketSearch(){loadScript('vestra-global-market-search-script','market-global-search.js?v=1.2',window.VestraGlobalMarketSearch)}
function loadLearnedUniverse(){loadScript('vestra-learned-universe-script','market-learned-universe.js?v=2.0',window.VestraLearnedUniverse,loadGlobalMarketSearch)}
function loadAppUpdateManager(){loadScript('vestra-app-update-manager-script','app-update-manager.js?v=1.1',window.VestraAppUpdateManager)}
function loadDataHealth(){loadScript('vestra-market-data-health-script','market-data-health.js?v=1.0',window.VestraMarketDataHealth)}
function loadRuntimeBridge(){loadScript('vestra-runtime-bridge-script','app-runtime-bridge.js?v=1.1',window.VestraRuntimeBridge,()=>{loadLearnedUniverse();loadAppUpdateManager();})}
function start(){style();loadResearchDiagnostics();loadDataHealth();repair();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;repair()})});mo.observe(document.body,{childList:true,subtree:true})}
loadCanonicalQuoteRepair();
loadQuoteRefreshPerformance();
loadDossierControls();
loadRuntimeBridge();
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
window.VestraMarketCompanyBrief=Object.freeze({brief,refresh:repair,version:'1.8'});
})();