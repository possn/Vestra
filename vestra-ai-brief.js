/* Vestra AI Brief v1.1 — deterministic evidence brief + safe Worker AI handoff. */
(() => {
'use strict';
const VERSION='1.1';
const CANONICAL_WORKER_URL='https://delicate-bar-cc80.pedrossnunes.workers.dev';
const SESSION_KEY='vestra.ai.brief.session.v1';
const t=v=>String(v??'').trim();
const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let stocks=[],byTicker=new Map(),loading=null;
function load(){if(loading)return loading;loading=fetch('./data/stocks-index.json',{cache:'no-store'}).then(async r=>{if(r.ok)return r.json();const legacy=await fetch('./data/stocks.json',{cache:'no-store'});if(!legacy.ok)throw 0;return legacy.json()}).then(d=>{stocks=Array.isArray(d)?d:(d?.stocks||[]);byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));return stocks}).catch(()=>[]);return loading}
function workerBase(){
 try{
  const bridge=t(window.VestraRuntimeBridge?.getState?.()?.settings?.workerUrl||window.VestraRuntimeBridge?.canonicalWorkerUrl);
  const configured=t(window.state?.settings?.workerUrl);
  return (bridge||configured||CANONICAL_WORKER_URL).replace(/\/$/,'');
 }catch{return CANONICAL_WORKER_URL}
}
function aiSession(){
 try{
  let id=t(localStorage.getItem(SESSION_KEY));
  if(/^[A-Za-z0-9._-]{8,128}$/.test(id))return id;
  id=(globalThis.crypto?.randomUUID?.()||`vestra-${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/[^A-Za-z0-9._-]/g,'-').slice(0,128);
  localStorage.setItem(SESSION_KEY,id); return id;
 }catch{return `vestra-session-${Date.now()}`}
}
function stock(tk){const x=t(tk).toUpperCase();return byTicker.get(x)||stocks.find(s=>t(s?.ticker).toUpperCase().split('.')[0]===x.split('.')[0])||null}
function pct(v){const x=n(v);return x==null?'—':`${(Math.abs(x)<=1?x*100:x).toFixed(1)}%`}
function evidence(s){
 const positives=[],risks=[],catalysts=[];
 const sc=n(s?.score),conf=n(s?.confidence_score),cov=n(s?.data_coverage_pct),roe=n(s?.roe),rg=n(s?.revenue_growth),eg=n(s?.earnings_growth),fcf=n(s?.free_cash_flow_yield_pct),pe=n(s?.forward_pe),up=n(s?.fair_value_upside_pct)??n(s?.analyst_price_target_upside_pct);
 if(sc!=null&&sc>=70)positives.push(`qualidade Vestra ${Math.round(sc)}/100`);
 if(roe!=null&&roe>0.15)positives.push(`ROE ${pct(roe)}`);
 if(rg!=null&&rg>0.08)positives.push(`receita a crescer ${pct(rg)}`);
 if(fcf!=null&&fcf>4)positives.push(`FCF yield ${pct(fcf)}`);
 if(t(s?.estimate_signal)==='improving'){positives.push('estimativas a melhorar');catalysts.push('revisões de estimativas positivas')}
 if(['confirmed','recovering'].includes(t(s?.recovery_status))){positives.push('recuperação em confirmação');catalysts.push('continuação da recuperação')}
 if(t(s?.thesis_direction)==='up')catalysts.push('tese fundamental em melhoria');
 if(up!=null&&up>10)catalysts.push(`upside indicado ${up.toFixed(0)}%`);
 if(pe!=null&&pe>35)risks.push(`Forward P/E exigente (${pe.toFixed(1)}x)`);
 if(roe!=null&&roe<0)risks.push(`ROE negativo (${pct(roe)})`);
 if(eg!=null&&eg<0)risks.push(`lucros em queda (${pct(eg)})`);
 if(fcf!=null&&fcf<0)risks.push(`FCF yield negativo (${pct(fcf)})`);
 if(t(s?.estimate_signal)==='deteriorating')risks.push('estimativas a deteriorar');
 if(['failed','bounce_only'].includes(t(s?.recovery_status)))risks.push('recuperação não confirmada');
 if(t(s?.risk_gate).toLowerCase()==='high'||t(s?.risk_gate).toLowerCase()==='severe')risks.push(`Risk Gate ${t(s?.risk_gate)}`);
 if(cov!=null&&cov<65)risks.push(`cobertura limitada (${Math.round(cov)}%)`);
 if(conf!=null&&conf<60)risks.push(`confiança limitada (${Math.round(conf)}/100)`);
 const thesis=positives.length?positives.slice(0,3).join(' · '):'Não há evidência suficiente para uma tese forte apenas com os dados disponíveis.';
 const whyNow=catalysts.length?catalysts.slice(0,3).join(' · '):'Sem catalisador claro identificado; exige acompanhamento.';
 const riskText=risks.length?risks.slice(0,3).join(' · '):'Sem fragilidade dominante identificada nos sinais disponíveis.';
 const change=risks.some(x=>/estimativas|recuperação/.test(x))?'Uma melhoria sustentada de resultados/estimativas mudaria a leitura.':'Uma deterioração de crescimento, cash flow ou estimativas mudaria a leitura.';
 return {thesis,whyNow,riskText,change};
}
function payload(s){return {ticker:t(s.ticker),name:t(s.name),sector:t(s.sector),industry:t(s.industry),score:n(s.score),confidence:n(s.confidence_score),coverage:n(s.data_coverage_pct),critical_coverage:n(s.critical_metric_coverage_pct),roe:n(s.roe),revenue_growth:n(s.revenue_growth),earnings_growth:n(s.earnings_growth),fcf_yield:n(s.free_cash_flow_yield_pct),forward_pe:n(s.forward_pe),price_to_book:n(s.price_to_book),debt_to_equity:n(s.debt_to_equity),timing:n(s.opportunity_timing_score),recovery_score:n(s.recovery_score),recovery_status:t(s.recovery_status),estimate_signal:t(s.estimate_signal),thesis_direction:t(s.thesis_direction),fair_value_upside_pct:n(s.fair_value_upside_pct),analyst_price_target_upside_pct:n(s.analyst_price_target_upside_pct),business_summary:t(s.business_summary||s.longBusinessSummary)} }
function localHTML(s){const e=evidence(s);return `<div class="ai459-grid"><section><small>TESE</small><p>${esc(e.thesis)}</p></section><section><small>PORQUÊ AGORA</small><p>${esc(e.whyNow)}</p></section><section><small>RISCOS</small><p>${esc(e.riskText)}</p></section><section><small>O QUE MUDA A TESE</small><p>${esc(e.change)}</p></section></div>`}
function normalizeAI(d){const x=d?.brief||d?.analysis||d;if(!x||typeof x!=='object')return null;return {thesis:t(x.thesis),whyNow:t(x.why_now||x.whyNow),risks:Array.isArray(x.risks)?x.risks.join(' · '):t(x.risks),change:t(x.what_changes_the_thesis||x.change),catalysts:Array.isArray(x.catalysts)?x.catalysts.join(' · '):t(x.catalysts)}}
async function runAI(card,s){
 const base=workerBase(),out=card.querySelector('.ai459-content'),btn=card.querySelector('[data-ai459-run]');
 btn.disabled=true;btn.textContent='A analisar…';card.querySelector('.ai459-status').textContent='A cruzar apenas evidência Vestra';
 try{
  const r=await fetch(`${base}/ai-brief`,{method:'POST',headers:{'content-type':'application/json','x-vestra-session':aiSession()},body:JSON.stringify({type:'company_brief',version:'1',data:payload(s)})});
  if(!r.ok)throw new Error(`HTTP ${r.status}`);
  const d=normalizeAI(await r.json());if(!d||!d.thesis)throw new Error('Resposta inválida');
  out.innerHTML=`<div class="ai459-grid"><section><small>TESE</small><p>${esc(d.thesis)}</p></section><section><small>PORQUÊ AGORA</small><p>${esc(d.whyNow||d.catalysts||'—')}</p></section><section><small>RISCOS</small><p>${esc(d.risks||'—')}</p></section><section><small>O QUE MUDA A TESE</small><p>${esc(d.change||'—')}</p></section></div>`;
  card.dataset.ai459='live';card.querySelector('.ai459-status').textContent='Vestra AI · evidência atual';btn.textContent='Atualizar IA';
 }catch(e){card.querySelector('.ai459-status').textContent='Vestra AI indisponível agora · mantém-se o brief local';btn.textContent='Analisar com IA'}finally{btn.disabled=false}
}
function install(){const sh=document.getElementById('marketSheet'),host=document.getElementById('marketSheetContent');if(!sh||sh.hidden||!t(sh.dataset.ticker)||!host)return;const s=stock(sh.dataset.ticker);if(!s)return;if(host.querySelector('.ai459-card'))return;const card=document.createElement('div');card.className='market-detail-card ai459-card';card.innerHTML=`<div class="ai459-head"><div><small>VESTRA BRIEF</small><h4>Leitura executiva</h4></div><button type="button" data-ai459-run>✦ Analisar com IA</button></div><div class="ai459-content">${localHTML(s)}</div><div class="ai459-foot"><span class="ai459-status">Brief local · sem inventar métricas</span><small>A IA interpreta o evidence layer; não altera Score Vestra nem cria recomendação automática.</small></div>`;const tabs=host.querySelector('.market-tabs,.market-detail-tabs,[data-market-tabs]');if(tabs)tabs.insertAdjacentElement('beforebegin',card);else{const metrics=host.querySelector('.market-metrics');metrics?metrics.insertAdjacentElement('afterend',card):host.appendChild(card)}}
function style(){if(document.getElementById('vestra-ai-v459-style'))return;const x=document.createElement('style');x.id='vestra-ai-v459-style';x.textContent=`.ai459-card{background:linear-gradient(145deg,#eef8f7,var(--card));border-color:color-mix(in srgb,var(--accent,#168e89) 22%,var(--line));box-shadow:0 10px 28px rgba(24,93,91,.07)}.ai459-head{display:flex;align-items:start;justify-content:space-between;gap:10px;margin-bottom:11px}.ai459-head small{font-size:8px;font-weight:900;letter-spacing:.13em;color:var(--accent,#168e89)}.ai459-head h4{font-size:17px;margin:2px 0 0}.ai459-head button{border:0;border-radius:999px;background:var(--accent,#168e89);color:#fff;padding:8px 10px;font-size:9px;font-weight:850;white-space:nowrap}.ai459-head button:disabled{opacity:.55}.ai459-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.ai459-grid section{padding:10px;border-radius:13px;background:rgba(255,255,255,.58);border:1px solid var(--line)}.ai459-grid small{font-size:7.5px;letter-spacing:.1em;font-weight:900;color:var(--text2)}.ai459-grid p{font-size:10.5px;line-height:1.4;margin:4px 0 0;color:var(--text)}.ai459-foot{display:grid;gap:2px;margin-top:8px}.ai459-foot span{font-size:8.5px;font-weight:800;color:var(--accent,#168e89)}.ai459-foot small{font-size:8px;color:var(--text2)}@media(max-width:620px){.ai459-grid{grid-template-columns:1fr}.ai459-head{align-items:center}.ai459-head h4{font-size:15px}}`;document.head.appendChild(x)}
function start(){style();load().then(()=>{install();let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;install()})}).observe(document.body,{childList:true,subtree:true})})}
document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ai459-run]');if(!b)return;e.preventDefault();e.stopPropagation();const sh=document.getElementById('marketSheet'),s=stock(sh?.dataset.ticker);const card=b.closest('.ai459-card');if(s&&card)runAI(card,s)});
window.VestraAiBrief={version:VERSION,evidence,payload,install,workerBase};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
