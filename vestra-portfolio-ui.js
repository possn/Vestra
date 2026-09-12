/* Vestra Portfolio UI v1.1 — canonical portfolio landing + analysis tabs. */
(() => {
  'use strict';

  const GROUPS = {
    decide: {label:'Prioridades', title:'Prioridades', sub:'Research, reforços e posições que merecem atenção.', kinds:['research','priority','reinforce','review']},
    monitor:{label:'Monitorizar', title:'Monitorizar', sub:'Saúde, objetivos, concentração e resistência da carteira.', kinds:['target','history','risk','stress']},
    optimize:{label:'Otimizar', title:'Otimizar', sub:'Trocas, alternativas, overlap e impacto antes de mexer.', kinds:['swap','scenario','overlap','map']}
  };
  const t=v=>String(v??'').trim();
  const num=v=>{const m=t(v).replace(',','.').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):null;};
  let active='decide', pending=false;

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
    const dc=decisionCenter(c), dcTxt=t(dc?.textContent);
    const positions=kpiByLabel(c,'Posições')||'';
    const research=kpiByLabel(c,'Com research')||'';
    const coverage=kpiByLabel(c,'Cobertura')||'';
    const conviction=(dcTxt.match(/CONVICÇÃO\s*([0-9.,]+)/i)||[])[1]||'';
    const risk=(dcTxt.match(/RISK BUDGET\s*([0-9.,]+)/i)||[])[1]||'';
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
    let hero=c.querySelector('.vpu-overview'); const m=metrics(c), st=status(m);
    if(!hero){ hero=document.createElement('section'); hero.className='vpu-overview'; const dc=decisionCenter(c); const anchor=dc||c.querySelector('.ux454-nav-title,.market-collapse-toolbar'); if(anchor)anchor.insertAdjacentElement('beforebegin',hero); else c.prepend(hero); }
    const cov=num(m.coverage), covText=m.coverage||'—';
    hero.innerHTML=`<div class="vpu-kicker">VISÃO GLOBAL DA CARTEIRA</div><div class="vpu-status is-${st.tone}"><div><strong>${st.title}</strong><span>${st.sub}</span></div><button type="button" data-vpu-detail>Ver diagnóstico</button></div><div class="vpu-grid"><div><small>Posições</small><strong>${m.positions||'—'}</strong><span>total</span></div><div><small>Com research</small><strong>${m.research||'—'}</strong><span>analisáveis</span></div><div><small>Cobertura</small><strong>${m.coverage||'—'}</strong><span>research</span></div><div><small>Convicção</small><strong>${m.conviction||'—'}</strong><span>/100</span></div><div><small>Risco</small><strong>${m.risk||'—'}</strong><span>/100</span></div><div><small>Rever</small><strong>${m.review||0}</strong><span>posições</span></div></div><div class="vpu-actions"><button data-vpu-jump="reinforce">↗ Reforçar <b>${m.reinforce||0}</b></button><button data-vpu-jump="review">! Rever <b>${m.review||0}</b></button><button data-vpu-jump="swap">⇄ Trocas <b>${m.swaps||0}</b></button><button data-vpu-jump="risk">◇ Risco <b>${m.risk||'—'}</b></button></div><div class="vpu-snapshot"><div class="vpu-snapshot-head"><div><small>SAÚDE DA CARTEIRA</small><strong>Leitura em 5 segundos</strong></div><span>${m.positions||'—'} posições · ${m.research||'—'} com research</span></div><div class="vpu-health">${healthBar('Convicção',m.conviction)}${healthBar('Risco',m.risk,true)}<div class="vpu-health-row"><div><span>Cobertura</span><b>${covText}</b></div><div class="vpu-track"><i class="is-${cov!=null&&cov>=70?'good':cov!=null&&cov>=40?'warn':'bad'}" style="width:${Math.max(0,Math.min(100,cov??0))}%"></i></div></div></div></div>`;
    const dc=decisionCenter(c); if(dc) dc.hidden=true;
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
    let reveal=c.querySelector('.vpu-reveal'); if(!reveal){ reveal=document.createElement('div'); reveal.className='vpu-reveal'; reveal.innerHTML='<div><small>ANÁLISE DETALHADA</small><strong>Explorar a carteira</strong><span>Trocas, overlap, research, objetivos e stress tests.</span></div><button type="button" data-vpu-toggle>Explorar</button>'; hero.insertAdjacentElement('afterend',reveal); } return reveal;
  }
  function ensureTabs(c,reveal){
    let shell=c.querySelector('.vpu-tabs-shell'); if(!shell){ shell=document.createElement('section'); shell.className='vpu-tabs-shell'; shell.innerHTML=`<div class="vpu-tabs" role="tablist" aria-label="Análise da carteira">${Object.entries(GROUPS).map(([id,g])=>`<button type="button" role="tab" data-vpu-tab="${id}">${g.label}</button>`).join('')}</div><div class="vpu-tab-intro"><strong></strong><span></span></div>`; reveal.insertAdjacentElement('afterend',shell); } return shell;
  }
  function apply(){
    const c=root(); if(!c)return; c.classList.add('vpu-portfolio');
    const hero=ensureHero(c), reveal=ensureExplore(c,hero), tabs=ensureTabs(c,reveal);
    c.querySelectorAll('.ux455-group-label,.ux454-group-label,.ux454-nav-title,.market-collapse-toolbar,.ux-portfolio-shortcuts,.ux453-focusbar,.ux460-overview,.ux461-reveal,.v479-portfolio-tabs').forEach(x=>{if(!x.closest('.vpu-overview,.vpu-reveal,.vpu-tabs-shell'))x.style.display='none';});
    let expanded=c.dataset.vpuExpanded==='1';
    tabs.hidden=!expanded;
    const meta=GROUPS[active]||GROUPS.decide;
    tabs.querySelectorAll('[data-vpu-tab]').forEach(b=>{const on=b.dataset.vpuTab===active;b.classList.toggle('is-active',on);b.setAttribute('aria-selected',on?'true':'false');});
    tabs.querySelector('.vpu-tab-intro strong').textContent=meta.title; tabs.querySelector('.vpu-tab-intro span').textContent=meta.sub;
    c.querySelectorAll('.market-detail-card[data-collapsible="1"],[data-ux-kind]').forEach(el=>{const g=classify(el);if(!g)return;el.classList.toggle('vpu-hidden',!expanded||g!==active);});
    const btn=reveal.querySelector('[data-vpu-toggle]'); if(btn)btn.textContent=expanded?'Fechar navegação':'Explorar';
  }
  function jump(kind){ const c=root(), target=card(kind,c); if(!target)return; c.dataset.vpuExpanded='1'; active=classify(target)||active; try{localStorage.setItem('vestra.portfolio.analysisTab',active);}catch{} apply(); if(target.classList.contains('is-collapsed'))target.querySelector('[data-collapse-toggle],.market-collapse-toggle')?.click(); setTimeout(()=>target.scrollIntoView({behavior:'smooth',block:'start'}),30); }
  function style(){ if(document.getElementById('vestra-portfolio-ui-style'))return; const link=document.createElement('link'); link.id='vestra-portfolio-ui-style'; link.rel='stylesheet'; link.href='vestra-portfolio-ui.css?v=1.0'; document.head.appendChild(link); }
  document.addEventListener('click',e=>{
    const d=e.target.closest?.('[data-vpu-detail]'); if(d){const c=root(),dc=decisionCenter(c);if(dc){dc.hidden=!dc.hidden;d.textContent=dc.hidden?'Ver diagnóstico':'Ocultar diagnóstico';if(!dc.hidden)setTimeout(()=>dc.scrollIntoView({behavior:'smooth',block:'start'}),20);}return;}
    const j=e.target.closest?.('[data-vpu-jump]'); if(j){e.preventDefault();jump(j.dataset.vpuJump);return;}
    const q=e.target.closest?.('[data-vpu-toggle]'); if(q){const c=root();if(!c)return;c.dataset.vpuExpanded=c.dataset.vpuExpanded==='1'?'0':'1';apply();return;}
    const tab=e.target.closest?.('[data-vpu-tab]'); if(tab){active=tab.dataset.vpuTab||'decide';try{localStorage.setItem('vestra.portfolio.analysisTab',active);}catch{}apply();return;}
  },true);
  function start(){style();try{const saved=localStorage.getItem('vestra.portfolio.analysisTab');if(GROUPS[saved])active=saved;}catch{} apply(); const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});}); mo.observe(document.body,{childList:true,subtree:true}); }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();