/* Vestra Portfolio UI v2.5 — scan-first exploration; cards open only on explicit intent. */
(() => {
  'use strict';

  const GROUPS = {
    decide: {label:'Prioridades', title:'O que merece atenção', sub:'Research, reforços e posições que merecem atenção.', kinds:['research','priority','reinforce','review']},
    monitor:{label:'Monitorizar', title:'Como está a carteira', sub:'Saúde, objetivos, concentração e resistência da carteira.', kinds:['target','history','risk','stress']},
    optimize:{label:'Otimizar', title:'Onde posso melhorar', sub:'Trocas, alternativas, overlap e impacto antes de mexer.', kinds:['swap','scenario','overlap','map']}
  };
  const t=v=>String(v??'').trim();
  const num=v=>{const m=t(v).replace(',','.').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):null;};
  let active='decide';

  function root(){
    const sh=document.getElementById('marketSheet'), c=document.getElementById('marketSheetContent');
    return (!sh || sh.hidden || t(sh.dataset.tool)!=='portfolio' || !c) ? null : c;
  }
  function card(kind,c){ return c?.querySelector(`[data-ux-kind="${kind}"]`) || null; }
  function text(c,rx){ if(!c)return ''; const el=[...c.querySelectorAll('small,strong,b,span,div,p')].find(x=>rx.test(t(x.textContent))); return t(el?.textContent); }
  function countRows(el){ return el ? el.querySelectorAll('.market-row,.market-research-queue-row,.market-fresh-row').length : 0; }
  function decisionCenter(c){ return [...c.querySelectorAll('.market-detail-card,section,div')].find(x=>/Portfolio Decision Center/i.test(t(x.textContent))&&/O que merece atenção agora/i.test(t(x.textContent))); }
  function kpiByLabel(c,label){
    const labels=[...c.querySelectorAll('small,span,div')].filter(x=>t(x.textContent).toLowerCase()===label.toLowerCase());
    for(const l of labels){ const box=l.parentElement; const strong=box?.querySelector('strong,b'); if(strong) return t(strong.textContent); const next=l.nextElementSibling; if(next) return t(next.textContent); }
    return '';
  }
  function metrics(c){
    const summary=c?.querySelector('.market-portfolio-summary');
    const dc=decisionCenter(c), dcTxt=t(dc?.textContent);
    const positions=t(summary?.dataset.vpuPositions)||kpiByLabel(c,'Posições')||'';
    const research=t(summary?.dataset.vpuResearch)||kpiByLabel(c,'Com research')||'';
    const coverageRaw=t(summary?.dataset.vpuCoverage);
    const coverage=coverageRaw?coverageRaw+'%':kpiByLabel(c,'Cobertura')||'';
    const conviction=t(dc?.dataset.vpuConviction)||(dcTxt.match(/CONVICÇÃO\s*([0-9.,]+)/i)||[])[1]||'';
    const risk=t(dc?.dataset.vpuRisk)||(dcTxt.match(/RISK BUDGET\s*([0-9.,]+)/i)||[])[1]||'';
    return {
      positions,research,coverage,conviction,risk,
      reinforce:countRows(card('reinforce',c)), review:countRows(card('review',c)), swaps:countRows(card('swap',c)),
      researchPending:num(text(card('research',c),/\d+\s*pendentes/i))||countRows(card('research',c))
    };
  }
  function status(m){
    const conv=num(m.conviction), risk=num(m.risk), cov=num(m.coverage), review=num(m.review);
    let title='Carteira equilibrada, com pontos a acompanhar', tone='neutral'; const bits=[];
    if(conv!=null) bits.push(conv>=70?'convicção forte':conv<45?'convicção frágil':'convicção moderada');
    if(risk!=null){ if(risk>=70){bits.push('risco elevado');tone='warn';title='Boa base, mas o risco merece atenção';} else if(risk>=55){bits.push('concentração a vigiar');tone='warn';} else bits.push('risco controlado'); }
    if(cov!=null&&cov<35) bits.push('research ainda incompleto');
    if(review>0) bits.push(`${review} itens para rever`);
    return {title,tone,sub:bits.slice(0,3).join(' · ')||'Visão consolidada da carteira.'};
  }
  function tone(v,reverse=false){ const x=num(v); if(x==null)return'neutral'; if(reverse)return x>=75?'bad':x>=55?'warn':'good'; return x>=70?'good':x>=50?'warn':'bad'; }
  function healthBar(label,value,reverse=false){
    const x=Math.max(0,Math.min(100,num(value)??0));
    return `<div class="vpu-health-row"><div><span>${label}</span><b>${value||'—'}${value&&String(value).includes('%')?'':'/100'}</b></div><div class="vpu-track"><i class="is-${tone(value,reverse)}" style="width:${x}%"></i></div></div>`;
  }
  function ensureHero(c){
    let hero=c.querySelector('.vpu-overview'), created=false; const m=metrics(c), st=status(m);
    if(!hero){ hero=document.createElement('section'); hero.className='vpu-overview'; created=true; const dc=decisionCenter(c); if(dc)dc.insertAdjacentElement('beforebegin',hero); else c.prepend(hero); }
    const cov=num(m.coverage), covText=m.coverage||'—';
    const signature=JSON.stringify([m.positions,m.research,m.coverage,m.conviction,m.risk,m.reinforce,m.review,m.swaps,st.title,st.tone,st.sub]);
    if(hero.dataset.signature!==signature){
      hero.dataset.signature=signature;
      hero.innerHTML=`<div class="vpu-kicker">VISÃO GLOBAL DA CARTEIRA</div><div class="vpu-status is-${st.tone}"><div><strong>${st.title}</strong><span>${st.sub}</span></div><button type="button" data-vpu-detail>Ver diagnóstico</button></div><div class="vpu-grid"><div><small>Posições</small><strong>${m.positions||'—'}</strong><span>total</span></div><div><small>Com research</small><strong>${m.research||'—'}</strong><span>analisáveis</span></div><div><small>Cobertura</small><strong>${m.coverage||'—'}</strong><span>research</span></div><div><small>Convicção</small><strong>${m.conviction||'—'}</strong><span>/100</span></div><div><small>Risco</small><strong>${m.risk||'—'}</strong><span>/100</span></div><div><small>Rever</small><strong>${m.review||0}</strong><span>posições</span></div></div><div class="vpu-actions"><button data-vpu-jump="reinforce">↗ Reforçar <b>${m.reinforce||0}</b></button><button data-vpu-jump="review">! Rever <b>${m.review||0}</b></button><button data-vpu-jump="swap">⇄ Trocas <b>${m.swaps||0}</b></button><button data-vpu-jump="risk">◇ Risco <b>${m.risk||'—'}</b></button></div><div class="vpu-snapshot"><div class="vpu-snapshot-head"><div><small>SAÚDE DA CARTEIRA</small><strong>Leitura em 5 segundos</strong></div><span>${m.positions||'—'} posições · ${m.research||'—'} com research</span></div><div class="vpu-health">${healthBar('Convicção',m.conviction)}${healthBar('Risco',m.risk,true)}<div class="vpu-health-row"><div><span>Cobertura</span><b>${covText}</b></div><div class="vpu-track"><i class="is-${cov!=null&&cov>=70?'good':cov!=null&&cov>=40?'warn':'bad'}" style="width:${Math.max(0,Math.min(100,cov??0))}%"></i></div></div></div></div>`;
    }
    if(created){const dc=decisionCenter(c); if(dc)dc.hidden=true;}
    return hero;
  }
  function classify(cardEl){
    const tagged=t(cardEl.dataset.ux455Group||cardEl.dataset.ux454GroupCard); if(tagged&&GROUPS[tagged]) return tagged;
    const kind=t(cardEl.dataset.uxKind); for(const [g,meta] of Object.entries(GROUPS)) if(meta.kinds.includes(kind)) return g;
    const x=t(cardEl.textContent).toLowerCase();
    if(/fila de revisão|prioridades da carteira|candidatos a reforço|posições a rever|capital novo.*reforçar/.test(x))return'decide';
    if(/aderência aos objetivos|carteira está a melhorar|diversificação da carteira|como reage a carteira|objetivos da carteira/.test(x))return'monitor';
    if(/alternativas no mesmo setor|substituíres pelo mesmo valor|concentração e overlap|mapa da carteira|onde melhora mais este capital|plano de rebalanceamento|trocas inteligentes/.test(x))return'optimize';
    return'';
  }
  function ensureExplore(c,hero){
    let reveal=c.querySelector('.vpu-reveal'); if(!reveal){ reveal=document.createElement('div'); reveal.className='vpu-reveal'; reveal.innerHTML='<div><small>EXPLORAR A CARTEIRA</small><strong>Transforma a carteira em decisões</strong><span>Começa pelo que exige atenção, acompanha a saúde ou testa uma melhoria.</span></div><button type="button" data-vpu-toggle>Começar</button>'; hero.insertAdjacentElement('afterend',reveal); } return reveal;
  }
  function ensureTabs(c,reveal){
    let shell=c.querySelector('.vpu-tabs-shell'); if(!shell){ shell=document.createElement('section'); shell.className='vpu-tabs-shell'; shell.innerHTML=`<div class="vpu-tabs-head"><div><strong>Escolhe o foco</strong></div><button type="button" data-vpu-toggle aria-label="Fechar análise">×</button></div><div class="vpu-tabs" role="tablist" aria-label="Análise da carteira">${Object.entries(GROUPS).map(([id,g])=>`<button type="button" role="tab" data-vpu-tab="${id}"><strong>${g.label}</strong><span>${g.sub}</span></button>`).join('')}</div><div class="vpu-tab-intro"><strong></strong><span></span></div><div class="vpu-optimize-guide" hidden><button type="button" data-vpu-guide="swap"><small>1</small><span><b>Encontrar alternativa</b><em>Comparar opções melhores</em></span><i class="vpu-step-state">Comparar</i></button><button type="button" data-vpu-guide="scenario"><small>2</small><span><b>Simular impacto</b><em>Ver antes de trocar</em></span><i class="vpu-step-state">Simular</i></button><button type="button" data-vpu-guide="rebalance"><small>3</small><span><b>Redistribuir capital</b><em>Escolher onde melhora mais</em></span><i class="vpu-step-state">Decidir</i></button></div>`; reveal.insertAdjacentElement('afterend',shell); } return shell;
  }
  function cardCount(el){return countRows(el)||null;}
  function syncGroupScan(c,tabs){
    const meta=GROUPS[active]||GROUPS.decide;
    tabs.querySelectorAll('[data-vpu-tab]').forEach(b=>{
      const group=b.dataset.vpuTab, cards=[...c.querySelectorAll('.vpu-section-card')].filter(el=>el.dataset.vpuGroup===group);
      const actionable=cards.reduce((sum,el)=>sum+(cardCount(el)||0),0);
      let badge=b.querySelector('.vpu-tab-count');
      if(!badge){badge=document.createElement('i');badge.className='vpu-tab-count';b.appendChild(badge);}
      badge.textContent=actionable?String(actionable):String(cards.length);
      badge.title=actionable?`${actionable} itens nesta área`:`${cards.length} análises nesta área`;
    });
    c.querySelectorAll('.vpu-section-card').forEach(el=>{
      let cue=el.querySelector(':scope > .vpu-card-cue');
      const rows=cardCount(el),kind=t(el.dataset.uxKind);
      const labels={research:'Research pendente',priority:'Prioridade',reinforce:'Possível reforço',review:'Rever',target:'Objetivos',history:'Evolução',risk:'Risco',stress:'Stress test'};
      if(!labels[kind]){cue?.remove();return;}
      if(!cue){cue=document.createElement('span');cue.className='vpu-card-cue';el.appendChild(cue);}
      cue.textContent=rows?`${labels[kind]} · ${rows}`:labels[kind];
    });
    const intro=tabs.querySelector('.vpu-tab-intro');if(intro)intro.dataset.vpuMode=active;
  }
  function apply(){
    const c=root(); if(!c)return; c.classList.add('vpu-portfolio');
    const hero=ensureHero(c), reveal=ensureExplore(c,hero), tabs=ensureTabs(c,reveal);
    const expanded=c.dataset.vpuExpanded==='1';
    tabs.hidden=!expanded;
    const meta=GROUPS[active]||GROUPS.decide;
    tabs.querySelectorAll('[data-vpu-tab]').forEach(b=>{const on=b.dataset.vpuTab===active;b.classList.toggle('is-active',on);b.setAttribute('aria-selected',on?'true':'false');});
    const introTitle=tabs.querySelector('.vpu-tab-intro strong'),introSub=tabs.querySelector('.vpu-tab-intro span');
    if(introTitle&&introTitle.textContent!==meta.title)introTitle.textContent=meta.title;
    if(introSub){const compact=active==='optimize'?'Segue os três passos abaixo.':'';if(introSub.textContent!==compact)introSub.textContent=compact;}
    const guide=tabs.querySelector('.vpu-optimize-guide'); if(guide)guide.hidden=!expanded||active!=='optimize';
    c.querySelectorAll('.market-detail-card[data-collapsible="1"],[data-ux-kind]').forEach(el=>{const g=classify(el);if(!g)return;el.classList.add('vpu-section-card');el.dataset.vpuGroup=g;el.classList.toggle('vpu-hidden',!expanded||g!==active);});
    syncGroupScan(c,tabs);
    const btn=reveal.querySelector('[data-vpu-toggle]'),label=expanded?'Fechar':'Começar'; if(btn&&btn.textContent!==label)btn.textContent=label;
  }
  function focusCard(c,target){
    if(!target)return null;
    c.querySelectorAll('.vpu-section-card').forEach(el=>{
      if(el.classList.contains('vpu-hidden')||el===target)return;
      if(!el.classList.contains('is-collapsed'))el.querySelector(':scope > [data-collapse-toggle],:scope > .market-collapse-toggle')?.click();
    });
    if(target.classList.contains('is-collapsed'))target.querySelector(':scope > [data-collapse-toggle],:scope > .market-collapse-toggle')?.click();
    return target;
  }
  function collapseActive(c){
    c.querySelectorAll('.vpu-section-card').forEach(el=>{
      if(el.classList.contains('vpu-hidden')||el.classList.contains('is-collapsed'))return;
      el.querySelector(':scope > [data-collapse-toggle],:scope > .market-collapse-toggle')?.click();
    });
    if(active==='optimize')syncOptimizeGuide(c,null);
  }
  function syncOptimizeGuide(c,target=null){
    const guide=c.querySelector('.vpu-optimize-guide');if(!guide)return;
    const steps=['swap','scenario','rebalance'];
    let current='';
    if(target)current=steps.find(step=>optimizeTarget(c,step)===target)||'';
    guide.querySelectorAll('[data-vpu-guide]').forEach((b,i)=>{
      const on=b.dataset.vpuGuide===current;b.classList.toggle('is-current',on);
      b.setAttribute('aria-current',on?'step':'false');
      const state=b.querySelector('.vpu-step-state');if(state)state.textContent=on?'Agora':i===0?'Comparar':i===1?'Simular':'Decidir';
    });
  }
  function optimizeTarget(c,step){
    const cards=[...c.querySelectorAll('.vpu-section-card')];
    if(step==='swap') return cards.find(el=>/alternativas no mesmo setor|trocar só quando melhora/i.test(t(el.textContent)))||null;
    if(step==='scenario') return cards.find(el=>/se substituíres pelo mesmo valor/i.test(t(el.textContent)))||null;
    if(step==='rebalance') return cards.find(el=>/onde melhora mais este capital/i.test(t(el.textContent)))||null;
    return null;
  }
  function jump(kind){ const c=root(), target=card(kind,c); if(!target)return; c.dataset.vpuExpanded='1'; active=classify(target)||active; try{localStorage.setItem('vestra.portfolio.analysisTab',active);}catch{} apply(); focusCard(c,target); setTimeout(()=>target.scrollIntoView({behavior:'smooth',block:'start'}),30); }
  function style(){ if(document.getElementById('vestra-portfolio-ui-style'))return; const link=document.createElement('link'); link.id='vestra-portfolio-ui-style'; link.rel='stylesheet'; link.href='vestra-portfolio-ui.css?v=1.2'; document.head.appendChild(link); }
  document.addEventListener('click',e=>{
    const j=e.target.closest?.('[data-vpu-jump]'); if(j){e.preventDefault();jump(j.dataset.vpuJump);return;}
    const q=e.target.closest?.('[data-vpu-toggle]'); if(q){const c=root();if(!c)return;const opening=c.dataset.vpuExpanded!=='1';c.dataset.vpuExpanded=opening?'1':'0';apply();if(opening){collapseActive(c);setTimeout(()=>c.querySelector('.vpu-tabs-shell')?.scrollIntoView({behavior:'smooth',block:'start'}),20);}return;}
    const tab=e.target.closest?.('[data-vpu-tab]'); if(tab){active=tab.dataset.vpuTab||'decide';try{localStorage.setItem('vestra.portfolio.analysisTab',active);}catch{}apply();const c=root();if(c){collapseActive(c);setTimeout(()=>c.querySelector('.vpu-tab-intro')?.scrollIntoView({behavior:'smooth',block:'nearest'}),30);}return;}
    const guide=e.target.closest?.('[data-vpu-guide]'); if(guide){const c=root();if(!c)return;const target=optimizeTarget(c,guide.dataset.vpuGuide);if(!target)return;focusCard(c,target);syncOptimizeGuide(c,target);setTimeout(()=>target.scrollIntoView({behavior:'smooth',block:'start'}),30);return;}
  },true);
  function start(){style();try{const saved=localStorage.getItem('vestra.portfolio.analysisTab');if(GROUPS[saved])active=saved;}catch{}}
  window.VestraPortfolioUI=Object.freeze({refresh:apply,version:'2.5'});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();