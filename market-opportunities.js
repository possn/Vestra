/* Vestra Market Opportunities v1.2 — canonical opportunity ranking/rendering + strategy-specific universe lenses. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const clamp=v=>Math.max(0,Math.min(100,v));
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const LENSES=new Set(['all','low52','emerging','recovery','value']);
  let activeLens='all';

  function stocks(){
    const rows=window.VestraMarketStaticUniverse?.getStocks?.();
    return Array.isArray(rows)?rows:[];
  }

  function stats(s){
    const c=(Array.isArray(s?.price_history_1y)?s.price_history_1y:[]).map(x=>n(x?.close)).filter(x=>x>0);
    const ret=d=>c.length>d?(c.at(-1)/c[c.length-d-1]-1)*100:null;
    const hi=c.length?Math.max(...c):null,cur=c.at(-1)||null;
    const r5=ret(5),r20=ret(20),r60=ret(60),room=hi&&cur?(1-cur/hi)*100:null;
    const accel=(r5!=null&&r20!=null)?r5-(r20/4):null;
    return {r5,r20,r60,room,accel};
  }
  function confirmed(s){
    const p=stats(s),est=t(s?.estimate_signal),rec=t(s?.recovery_status),dir=t(s?.thesis_direction);
    let signals=0;
    if(est==='improving')signals++;
    if(['confirmed','recovering'].includes(rec))signals++;
    if(p.r20!=null&&p.r20>=0&&p.r20<=12)signals++;
    if(p.accel!=null&&p.accel>0)signals++;
    if(dir==='up')signals++;
    return signals;
  }
  function overextended(s){
    if(typeof s?.opportunity_overextended==='boolean')return s.opportunity_overextended;
    const p=stats(s);return (p.r20!=null&&p.r20>22)||(p.r60!=null&&p.r60>44)||((p.room!=null&&p.room<2)&&(p.r60!=null&&p.r60>18));
  }
  function timing(s){
    const o=n(s?.opportunity_timing_score); if(o!=null)return o;
    const p=stats(s);let x=50;
    if(p.r20!=null)x+=p.r20>=1&&p.r20<=9?21:p.r20>-4&&p.r20<1?7:p.r20>18?-16:p.r20<=-12?-15:0;
    if(p.r60!=null)x+=p.r60>=3&&p.r60<=22?13:p.r60>38?-13:p.r60<=-18?-11:0;
    if(p.accel!=null)x+=p.accel>2?7:p.accel>0?3:p.accel<-4?-7:0;
    if(p.room!=null)x+=p.room>=5&&p.room<=28?10:p.room<2?-8:p.room>45?-4:0;
    if(t(s?.estimate_signal)==='improving')x+=8;if(t(s?.estimate_signal)==='deteriorating')x-=10;
    if(['confirmed','recovering'].includes(t(s?.recovery_status)))x+=7;if(['failed','bounce_only'].includes(t(s?.recovery_status)))x-=10;
    return clamp(x);
  }
  function eligible(s){
    const qt=t(s?.quote_type||s?.quoteType).toUpperCase();if(['ETF','CRYPTOCURRENCY','MUTUALFUND'].includes(qt))return false;
    const sc=n(s?.score),cov=n(s?.data_coverage_pct),conf=n(s?.confidence_score),crit=n(s?.critical_metric_coverage_pct),rel=t(s?.score_reliability).toLowerCase(),risk=t(s?.risk_gate).toLowerCase();
    if(sc==null||sc<58||cov==null||cov<55||conf==null||conf<50)return false;
    if(crit!=null&&crit<35)return false;
    if(['insufficient','suppressed'].includes(rel)||['high','severe'].includes(risk)||t(s?.zombie).toLowerCase()==='yes'||overextended(s))return false;
    return timing(s)>=48 && confirmed(s)>=2;
  }
  function score(s){
    const vals=[[n(s?.score),.23],[timing(s),.27],[n(s?.recovery_score),.10],[n(s?.qarp_score),.10],[n(s?.moat_score),.07],[n(s?.capital_allocation_intelligence_score),.05],[n(s?.confidence_score),.06],[n(s?.value_pct),.06],[n(s?.growth_pct),.03],[n(s?.sector_native_score),.03]].filter(([v])=>v!=null);
    if(!vals.length)return null;let x=vals.reduce((a,[v,w])=>a+clamp(v)*w,0)/vals.reduce((a,[,w])=>a+w,0);
    const p=stats(s),fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);
    if(fv!=null)x+=Math.max(-7,Math.min(8,fv/4.5));else if(pt!=null)x+=Math.max(-5,Math.min(6,pt/7));
    x+=Math.min(5,confirmed(s)*1.25);
    if(p.accel!=null&&p.accel>2)x+=2;
    if(t(s?.estimate_signal)==='deteriorating')x-=7;if(['failed','bounce_only'].includes(t(s?.recovery_status)))x-=7;if(t(s?.valuation_signal)==='overvalued')x-=7;
    return clamp(x);
  }
  function low52Above(s){
    const direct=n(s?.low52_above_low_pct);
    if(direct!=null)return direct;
    const current=n(s?.current_price),low=n(s?.low52_price_low)??n(s?.fifty_two_week_low);
    return current!=null&&current>0&&low!=null&&low>0?(current/low-1)*100:null;
  }
  function coreCandidate(s,{scoreMin=54,coverageMin=50,confidenceMin=45,criticalMin=30}={}){
    const qt=t(s?.quote_type||s?.quoteType).toUpperCase();if(['ETF','CRYPTOCURRENCY','MUTUALFUND'].includes(qt))return false;
    const sc=n(s?.score),cov=n(s?.data_coverage_pct),conf=n(s?.confidence_score),crit=n(s?.critical_metric_coverage_pct),rel=t(s?.score_reliability).toLowerCase(),risk=t(s?.risk_gate).toLowerCase();
    if(sc==null||sc<scoreMin||cov==null||cov<coverageMin||conf==null||conf<confidenceMin)return false;
    if(crit!=null&&crit<criticalMin)return false;
    if(['insufficient','suppressed'].includes(rel)||['high','severe'].includes(risk)||t(s?.zombie).toLowerCase()==='yes')return false;
    return true;
  }
  function lensEligible(s,lens){
    if(lens==='all')return eligible(s);
    const p=stats(s),rec=t(s?.recovery_status),est=t(s?.estimate_signal),dir=t(s?.thesis_direction),val=t(s?.valuation_signal);
    if(lens==='low52'){
      const above=low52Above(s);
      return coreCandidate(s,{scoreMin:50,coverageMin:45,confidenceMin:45,criticalMin:25})&&above!=null&&above>=-0.5&&above<=5&&timing(s)>=35;
    }
    if(lens==='emerging')return coreCandidate(s)&&!overextended(s)&&timing(s)>=55&&timing(s)<=82&&confirmed(s)>=1&&!['confirmed','recovering'].includes(rec)&&(est==='improving'||dir==='up'||(p.accel!=null&&p.accel>0));
    if(lens==='recovery')return coreCandidate(s)&&!overextended(s)&&timing(s)>=45&&(['confirmed','recovering'].includes(rec)||(est==='improving'&&confirmed(s)>=2));
    if(lens==='value'){
      const fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);
      return coreCandidate(s)&&!overextended(s)&&timing(s)>=45&&((fv!=null&&fv>=10)||(pt!=null&&pt>=12)||val==='undervalued');
    }
    return false;
  }
  function lensScore(s,lens){
    const base=n(s?.score)||0,tm=timing(s),conf=n(s?.confidence_score)||0,p=stats(s);
    if(lens==='all')return score(s)||0;
    if(lens==='low52'){
      const above=Math.max(0,low52Above(s)??5),proximity=clamp(100-above*20);
      return clamp(base*.38+tm*.22+proximity*.30+conf*.10);
    }
    if(lens==='emerging'){
      const accel=p.accel==null?50:clamp(50+p.accel*7);
      return clamp(tm*.38+base*.27+accel*.20+conf*.15);
    }
    if(lens==='recovery'){
      const rec=n(s?.recovery_score)??(confirmed(s)*18);
      return clamp(base*.28+tm*.27+clamp(rec)*.27+clamp(confirmed(s)*20)*.18);
    }
    if(lens==='value'){
      const fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct),up=Math.max(fv??-100,pt??-100);
      const upside=clamp(50+Math.max(-40,Math.min(50,up))*1.15);
      return clamp(base*.30+tm*.25+upside*.30+conf*.15);
    }
    return score(s)||0;
  }
  function brief(s){return t(s?.business_summary||s?.longBusinessSummary||s?.description)||[t(s?.industry),t(s?.sector)].filter(Boolean).join(' · ')||'Empresa acompanhada pelo Vestra.';}
  function reason(s){const p=stats(s),b=[];if(t(s?.estimate_signal)==='improving')b.push('estimativas ↑');if(['confirmed','recovering'].includes(t(s?.recovery_status)))b.push('recuperação confirmada');if(p.accel!=null&&p.accel>2)b.push('aceleração recente');if(p.room!=null&&p.room>=5&&p.room<=30)b.push(`${p.room.toFixed(0)}% abaixo do máximo`);const fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);if(fv!=null&&fv>8)b.push(`upside +${fv.toFixed(0)}%`);else if(pt!=null&&pt>10)b.push(`target +${pt.toFixed(0)}%`);return b.slice(0,3).join(' · ')||'qualidade e timing alinhados';}
  function lensReason(s,lens){
    if(lens==='low52'){const x=low52Above(s);return x!=null?`${x.toFixed(1)}% acima do mínimo 52s · qualidade ${Math.round(n(s?.score)||0)} · timing ${Math.round(timing(s))}`:reason(s);}
    if(lens==='emerging')return ['setup inicial',t(s?.estimate_signal)==='improving'?'estimativas ↑':'',stats(s).accel>0?'aceleração positiva':''].filter(Boolean).join(' · ');
    if(lens==='recovery')return ['recuperação',t(s?.recovery_status)||'',confirmed(s)>=2?`${confirmed(s)} confirmações`:''].filter(Boolean).join(' · ');
    if(lens==='value'){const fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);return ['value + timing',fv!=null?`fair value +${fv.toFixed(0)}%`:pt!=null?`target +${pt.toFixed(0)}%`:'',`timing ${Math.round(timing(s))}`].filter(Boolean).join(' · ');}
    return reason(s);
  }
  function row(s,lens){const p=stats(s),sc=lensScore(s,lens),tm=timing(s);return `<div class="market-row ux453-opp" data-market-ticker="${esc(s.ticker)}"><div class="ux453-opp-body"><div class="market-row__title"><span class="market-row__ticker">${esc(s.ticker)}</span><span class="market-row__name">${esc(s.name||'')}</span></div><div class="market-row__description">${esc(brief(s))}</div><div class="ux453-thesis">✦ ${esc(lensReason(s,lens))}</div><div class="ux453-pills"><span>Qualidade ${Math.round(n(s?.score)||0)}</span><span>Timing ${Math.round(tm)}</span>${p.r20!=null?`<span>20d ${p.r20>=0?'+':''}${p.r20.toFixed(1)}%</span>`:''}${p.accel!=null?`<span>Acel. ${p.accel>=0?'+':''}${p.accel.toFixed(1)}</span>`:''}</div></div><div class="ux453-entry"><small>ENTRY</small><strong>${Math.round(sc)}</strong><em>${confirmed(s)} sinais</em></div></div>`;}

  function decorate(section){
    const list=section?.querySelector('.market-list');if(!list)return;
    const rows=[...list.querySelectorAll('.market-row')];
    rows.forEach((r,i)=>{
      r.classList.toggle('ux454-podium',i<3);
      r.classList.toggle('ux454-podium-1',i===0);
      r.classList.toggle('ux454-podium-2',i===1);
      r.classList.toggle('ux454-podium-3',i===2);
      const old=r.querySelector('.ux454-rank');
      if(i<3){if(!old){const b=document.createElement('span');b.className='ux454-rank';b.textContent=`#${i+1}`;r.prepend(b);}else old.textContent=`#${i+1}`;}else old?.remove();
    });
    if(!section.querySelector('.ux454-opportunity-guide')){
      const g=document.createElement('div');g.className='ux454-opportunity-guide';
      g.innerHTML='<span><b>ENTRY</b> combinação de qualidade + timing</span><span><b>Timing</b> evita perseguir preço esticado</span><span><b>Sinais</b> confirmações independentes</span>';
      section.querySelector('.market-section__head')?.insertAdjacentElement('afterend',g);
    }
  }
  function lensMeta(lens){
    if(lens==='low52')return ['Mínimos 52 semanas','Empresas robustas negociadas até 5% acima do mínimo de 52 semanas.'];
    if(lens==='emerging')return ['A começar','Setups ainda numa fase inicial: timing a melhorar, sem recuperação já madura.'];
    if(lens==='recovery')return ['Recuperação','Empresas com recuperação operacional ou de estimativas já confirmada.'];
    if(lens==='value')return ['Value + timing','Desconto ou upside relevante, mas apenas com timing mínimo aceitável.'];
    return ['Oportunidades agora','Empresas robustas com pelo menos 2 confirmações independentes de timing — sem perseguir preços esticados.'];
  }

  function opportunities(lens=activeLens){
    activeLens=LENSES.has(t(lens))?t(lens):'all';
    const universe=stocks();
    const section=[...document.querySelectorAll('.market-section')].find(x=>/Oportunidades (agora|emergentes)|Melhores oportunidades|Mínimos 52 semanas|A começar|Recuperação|Value \+ timing/.test(t(x.querySelector('h3')?.textContent)));if(!section||!universe.length)return [];
    const list=section.querySelector('.market-list');if(!list)return[];const active=section.querySelector('[data-market-sector].is-active');const sec=t(active?.dataset.marketSector)||'all';
    let rows=universe.filter(s=>lensEligible(s,activeLens));if(sec!=='all')rows=rows.filter(s=>t(s?.sector)===sec);rows.sort((a,b)=>lensScore(b,activeLens)-lensScore(a,activeLens)||(score(b)||0)-(score(a)||0));rows=rows.slice(0,12);
    const sig=(rows.map(s=>`${t(s.ticker)}:${Math.round(lensScore(s,activeLens))}`).join('|')||'empty')+`:${sec}:${activeLens}`;
    if(list.dataset.ux453!==sig){
      list.innerHTML=rows.map(s=>row(s,activeLens)).join('');
      rows.forEach(s=>{const el=list.querySelector(`[data-market-ticker="${CSS.escape(t(s.ticker))}"]`);if(el)el.__vestraStock=s;});
      list.dataset.ux453=sig;
    }
    const [title,subtitle]=lensMeta(activeLens);const h=section.querySelector('.market-section__head h3');if(h)h.textContent=title;const p=section.querySelector('.market-section__head p');if(p)p.textContent=subtitle;
    decorate(section);
    return rows;
  }
  function selectLens(lens){activeLens=LENSES.has(t(lens))?t(lens):'all';return opportunities(activeLens);}

  function style(){if(document.getElementById('vestra-market-opportunities-style'))return;const s=document.createElement('style');s.id='vestra-market-opportunities-style';s.textContent=`
  .ux453-opp{align-items:stretch!important;background:linear-gradient(145deg,var(--card),color-mix(in srgb,var(--accent,#168e89) 5%,var(--card)));border-radius:18px!important}.ux453-opp-body{min-width:0;flex:1}.ux453-thesis{font-size:11px;font-weight:750;color:var(--text);margin:7px 0 6px}.ux453-pills{display:flex;gap:6px;flex-wrap:wrap}.ux453-pills span{font-size:9.5px;font-weight:800;padding:4px 7px;border-radius:999px;background:var(--soft);color:var(--text2)}.ux453-entry{min-width:58px;display:grid;align-content:center;justify-items:center;border-left:1px solid var(--line);padding-left:10px}.ux453-entry small{font-size:8px;letter-spacing:.12em;color:var(--text2);font-weight:900}.ux453-entry strong{font-size:23px;color:var(--accent,#168e89)}.ux453-entry em{font-size:8px;font-style:normal;color:var(--text2)}
  .ux454-opportunity-guide{display:flex;gap:6px;overflow-x:auto;padding:0 1px 9px;margin-top:-2px;scrollbar-width:none}.ux454-opportunity-guide span{flex:0 0 auto;padding:6px 8px;border-radius:999px;background:var(--soft);font-size:8.5px;color:var(--text2)}.ux454-opportunity-guide b{color:var(--text);margin-right:3px}.ux454-podium{position:relative!important;border-width:1.5px!important}.ux454-podium-1{background:linear-gradient(145deg,color-mix(in srgb,var(--accent,#168e89) 12%,var(--card)),var(--card))!important;box-shadow:0 10px 26px rgba(18,118,111,.10)!important}.ux454-podium-2{background:linear-gradient(145deg,#f3f6fb,var(--card))!important}.ux454-podium-3{background:linear-gradient(145deg,#fff7ec,var(--card))!important}.ux454-rank{position:absolute;right:8px;top:7px;font-size:8px;font-weight:900;letter-spacing:.08em;color:var(--text2);opacity:.8}
  `;document.head.appendChild(s);}

  function start(){style();opportunities();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;opportunities();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  window.VestraMarketOpportunities=Object.freeze({stats,confirmed,timing,eligible,score,low52Above,lensEligible,lensScore,selectLens,refresh:opportunities,decorate,get activeLens(){return activeLens;},version:'1.2'});
})();
