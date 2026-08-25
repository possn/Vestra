/* Vestra Portfolio Overview v4.60 — global view first, detail second. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const num=v=>{const m=t(v).replace(',','.').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):null;};

  function root(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function textFrom(root,rx){
    const el=[...root.querySelectorAll('strong,b,span,div,p')].find(x=>rx.test(t(x.textContent)));
    return t(el?.textContent);
  }
  function kpiByLabel(c,label){
    const labels=[...c.querySelectorAll('small,span,div')].filter(x=>t(x.textContent).toLowerCase()===label.toLowerCase());
    for(const l of labels){
      const box=l.parentElement; if(!box) continue;
      const strong=box.querySelector('strong,b'); if(strong)return t(strong.textContent);
      const next=l.nextElementSibling;if(next)return t(next.textContent);
    }
    return '';
  }
  function decisionCenter(c){
    return [...c.querySelectorAll('.market-detail-card,section,div')].find(x=>/Portfolio Decision Center/i.test(t(x.textContent))&&/O que merece atenção agora/i.test(t(x.textContent)));
  }
  function counts(c){
    const pos=kpiByLabel(c,'Posições')||textFrom(c,/^Posições\s+\d+$/i).replace(/\D/g,'');
    const research=kpiByLabel(c,'Com research')||'';
    const coverage=kpiByLabel(c,'Cobertura')||'';
    const pulse=c.querySelector('.ux458-pulse');
    const val=(label)=>{const card=[...pulse?.querySelectorAll('.ux458-pulse-card')||[]].find(x=>t(x.textContent).toLowerCase().startsWith(label));return t(card?.querySelector('strong')?.textContent);};
    return {pos,research,coverage,reinforce:val('reforçar'),review:val('rever'),swaps:val('trocas'),risk:val('risco'),researchPending:val('research')};
  }
  function summary(c){
    const dc=decisionCenter(c);const txt=t(dc?.textContent);
    const conviction=(txt.match(/CONVICÇÃO\s*([0-9.,]+)/i)||[])[1]||'';
    const risk=(txt.match(/RISK BUDGET\s*([0-9.,]+)/i)||[])[1]||'';
    const stress=(txt.match(/PIOR STRESS\s*([0-9.,]+)/i)||[])[1]||'';
    const review=(txt.match(/REVER\/SUBSTITUIR\s*(\d+)/i)||[])[1]||'';
    return {conviction,risk,stress,review};
  }
  function status(s,cnt){
    const conv=num(s.conviction),risk=num(s.risk),cov=num(cnt.coverage),review=num(cnt.review||s.review);
    let title='Carteira equilibrada, com pontos a acompanhar';let tone='neutral';const bits=[];
    if(conv!=null){if(conv>=70)bits.push('convicção forte');else if(conv<45)bits.push('convicção frágil');else bits.push('convicção moderada');}
    if(risk!=null){if(risk>=70){bits.push('risco elevado');tone='warn';title='Boa base, mas o risco merece atenção';}else if(risk>=55){bits.push('concentração a vigiar');tone='warn';}else bits.push('risco controlado');}
    if(cov!=null&&cov<35)bits.push('research ainda incompleto');
    if(review!=null&&review>0)bits.push(`${review} itens para rever`);
    return {title,tone,sub:bits.slice(0,3).join(' · ')||'Visão consolidada da carteira.'};
  }
  function install(){
    const c=root();if(!c)return;
    const cnt=counts(c),s=summary(c),st=status(s,cnt);
    let hero=c.querySelector('.ux460-overview');
    if(!hero){hero=document.createElement('section');hero.className='ux460-overview';
      const dc=decisionCenter(c);const firstNav=c.querySelector('.ux454-nav-title,.market-collapse-toolbar');
      if(dc)dc.insertAdjacentElement('beforebegin',hero);else if(firstNav)firstNav.insertAdjacentElement('beforebegin',hero);else c.prepend(hero);
    }
    const metrics=[
      ['Posições',cnt.pos||'—','total'],['Com research',cnt.research||'—','analisáveis'],['Cobertura',cnt.coverage||'—','research'],['Convicção',s.conviction||'—','/100'],['Risco',cnt.risk||s.risk||'—','/100'],['Rever',cnt.review||'—','posições']
    ];
    hero.innerHTML=`<div class="ux460-kicker">VISÃO GLOBAL DA CARTEIRA</div><div class="ux460-status is-${st.tone}"><div><strong>${st.title}</strong><span>${st.sub}</span></div><button type="button" data-ux460-detail>Ver diagnóstico</button></div><div class="ux460-grid">${metrics.map(([a,b,d])=>`<div><small>${a}</small><strong>${b}</strong><span>${d}</span></div>`).join('')}</div><div class="ux460-actions"><button data-ux460-jump="reinforce">↗ Reforçar <b>${cnt.reinforce||'—'}</b></button><button data-ux460-jump="review">! Rever <b>${cnt.review||'—'}</b></button><button data-ux460-jump="swap">⇄ Trocas <b>${cnt.swaps||'—'}</b></button><button data-ux460-jump="risk">◇ Risco <b>${cnt.risk||s.risk||'—'}</b></button></div>`;

    const dc=decisionCenter(c);
    if(dc&&!dc.dataset.ux460Prepared){
      dc.dataset.ux460Prepared='1';dc.classList.add('ux460-decision-center');
      const score=[...dc.querySelectorAll('strong,b,span,div')].find(x=>/^0\/100$/.test(t(x.textContent)));
      if(score)score.closest('span,div')?.classList.add('ux460-hide-zero');
      dc.hidden=true;
    }
    const navTitle=c.querySelector('.ux454-nav-title');if(navTitle)navTitle.classList.add('ux460-nav-secondary');
  }
  function jump(kind){
    const c=root();const card=c?.querySelector(`[data-ux-kind="${kind}"]`);if(!card)return;
    if(card.classList.contains('is-collapsed'))card.querySelector('[data-collapse-toggle]')?.click();
    setTimeout(()=>card.scrollIntoView({behavior:'smooth',block:'start'}),30);
  }
  function style(){
    if(document.getElementById('vestra-v460-style'))return;const s=document.createElement('style');s.id='vestra-v460-style';s.textContent=`
    .ux460-overview{margin:8px 0 14px;padding:16px;border-radius:24px;background:linear-gradient(145deg,#123d48,#176b69);color:#fff;box-shadow:0 16px 34px rgba(18,61,72,.18)}.ux460-kicker{font-size:9px;font-weight:900;letter-spacing:.14em;opacity:.7;margin-bottom:8px}.ux460-status{display:flex;justify-content:space-between;gap:12px;align-items:start;padding-bottom:13px;border-bottom:1px solid rgba(255,255,255,.12)}.ux460-status>div{display:grid;gap:4px}.ux460-status strong{font-size:19px;line-height:1.15}.ux460-status span{font-size:10px;line-height:1.4;opacity:.78}.ux460-status button{border:0;border-radius:999px;padding:8px 10px;background:rgba(255,255,255,.14);color:#fff;font-size:9px;font-weight:850;white-space:nowrap}.ux460-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.ux460-grid>div{display:grid;gap:1px;padding:10px;border-radius:14px;background:rgba(255,255,255,.09)}.ux460-grid small{font-size:8px;opacity:.65}.ux460-grid strong{font-size:18px}.ux460-grid span{font-size:8px;opacity:.62}.ux460-actions{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}.ux460-actions button{display:flex;align-items:center;justify-content:center;gap:5px;border:0;border-radius:12px;padding:9px 6px;background:#f7fbfa;color:#183a42;font-size:9px;font-weight:850}.ux460-actions b{font-size:10px;color:#148777}.ux460-decision-center{margin-top:10px!important}.ux460-hide-zero{display:none!important}.ux460-nav-secondary{margin-top:12px!important;padding-top:4px!important}.ux460-nav-secondary>span{display:none!important}
    @media(max-width:620px){.ux460-overview{padding:14px;border-radius:21px}.ux460-status{display:grid}.ux460-status button{justify-self:start}.ux460-grid{grid-template-columns:repeat(3,1fr)}.ux460-actions{grid-template-columns:repeat(2,1fr)}.ux460-status strong{font-size:17px}}
    `;document.head.appendChild(s);
  }
  document.addEventListener('click',e=>{
    const d=e.target.closest?.('[data-ux460-detail]');if(d){const c=root(),dc=decisionCenter(c);if(dc){dc.hidden=!dc.hidden;d.textContent=dc.hidden?'Ver diagnóstico':'Ocultar diagnóstico';if(!dc.hidden)setTimeout(()=>dc.scrollIntoView({behavior:'smooth',block:'start'}),20);}return;}
    const j=e.target.closest?.('[data-ux460-jump]');if(j)jump(j.dataset.ux460Jump);
  });
  function start(){style();install();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;install();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
