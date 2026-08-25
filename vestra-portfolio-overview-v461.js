/* Vestra Portfolio Overview v4.61 — cleaner landing hierarchy, global snapshot first. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const num=v=>{const m=t(v).replace(',','.').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):null;};

  function root(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function card(kind,c){return c?.querySelector(`[data-ux-kind="${kind}"]`)||null;}
  function text(c,rx){const el=[...c.querySelectorAll('small,strong,b,span,div,p')].find(x=>rx.test(t(x.textContent)));return t(el?.textContent);}
  function scoreFrom(c,label){const raw=text(c,new RegExp(label+'\\s*[0-9.,]+','i'));return num(raw);}
  function countRows(el){return el?[...el.querySelectorAll('.market-row,.market-research-queue-row,.market-fresh-row')].length:0;}

  function metrics(c){
    const hero=c.querySelector('.ux460-overview');
    const dc=[...c.querySelectorAll('.market-detail-card,section,div')].find(x=>/Portfolio Decision Center/i.test(t(x.textContent))&&/O que merece atenção agora/i.test(t(x.textContent)));
    const dcTxt=t(dc?.textContent),heroTxt=t(hero?.textContent);
    const pick=(rx,src=dcTxt)=>(src.match(rx)||[])[1]||'';
    const conviction=pick(/CONVICÇÃO\s*([0-9.,]+)/i)||pick(/Convicção\s*([0-9.,]+)/i,heroTxt);
    const risk=pick(/RISK BUDGET\s*([0-9.,]+)/i)||pick(/Risco\s*([0-9.,]+)/i,heroTxt);
    const coverage=pick(/Cobertura\s*([0-9.,]+%?)/i,heroTxt)||text(c,/^\d+%\s*coberto$/i).match(/\d+%/)?.[0]||'';
    const research=pick(/Com research\s*(\d+)/i,heroTxt)||'';
    const positions=pick(/Posições\s*(\d+)/i,heroTxt)||'';
    const reinforce=countRows(card('reinforce',c));
    const review=countRows(card('review',c));
    const swaps=countRows(card('swap',c));
    const researchPending=num(text(card('research',c),/\d+\s*pendentes/i))||countRows(card('research',c));
    return {conviction,risk,coverage,research,positions,reinforce,review,swaps,researchPending};
  }
  function tone(v,reverse=false){
    const x=num(v);if(x==null)return 'neutral';
    if(reverse)return x>=75?'bad':x>=55?'warn':'good';
    return x>=70?'good':x>=50?'warn':'bad';
  }
  function bar(label,value,reverse=false){
    const x=Math.max(0,Math.min(100,num(value)??0));
    return `<div class="ux461-health-row"><div><span>${label}</span><b>${value||'—'}${value&&String(value).includes('%')?'':'/100'}</b></div><div class="ux461-track"><i class="is-${tone(value,reverse)}" style="width:${x}%"></i></div></div>`;
  }
  function installSnapshot(){
    const c=root();if(!c)return;const m=metrics(c);const hero=c.querySelector('.ux460-overview');if(!hero)return;
    let box=hero.querySelector('.ux461-snapshot');
    if(!box){box=document.createElement('div');box.className='ux461-snapshot';hero.appendChild(box);}
    const cov=num(m.coverage);const covText=m.coverage||'—';
    box.innerHTML=`<div class="ux461-snapshot-head"><div><small>SAÚDE DA CARTEIRA</small><strong>Leitura em 5 segundos</strong></div><span>${m.positions||'—'} posições · ${m.research||'—'} com research</span></div>
      <div class="ux461-health">${bar('Convicção',m.conviction)}${bar('Risco',m.risk,true)}<div class="ux461-health-row"><div><span>Cobertura</span><b>${covText}</b></div><div class="ux461-track"><i class="is-${cov!=null&&cov>=70?'good':cov!=null&&cov>=40?'warn':'bad'}" style="width:${Math.max(0,Math.min(100,cov??0))}%"></i></div></div></div>`;
  }
  function simplifyLanding(){
    const c=root();if(!c)return;
    c.classList.add('ux461-portfolio');
    const pulse=c.querySelector('.ux458-pulse');if(pulse)pulse.hidden=true;
    const nav=c.querySelector('.ux454-nav-title');if(nav)nav.hidden=true;
    const toolbar=c.querySelector('.market-collapse-toolbar');const focus=c.querySelector('.ux453-focusbar');const shortcuts=c.querySelector('.ux-portfolio-shortcuts');
    [toolbar,focus,shortcuts].filter(Boolean).forEach(x=>x.classList.add('ux461-secondary-nav'));
    let reveal=c.querySelector('.ux461-reveal');
    const hero=c.querySelector('.ux460-overview');
    if(hero&&!reveal){
      reveal=document.createElement('div');reveal.className='ux461-reveal';reveal.innerHTML='<div><small>ANÁLISE DETALHADA</small><strong>Explorar a carteira</strong><span>Trocas, overlap, research, objetivos e stress tests.</span></div><button type="button" data-ux461-toggle>Explorar</button>';
      hero.insertAdjacentElement('afterend',reveal);
    }
    const expanded=c.dataset.ux461Expanded==='1';
    [toolbar,focus,shortcuts].filter(Boolean).forEach(x=>x.hidden=!expanded);
    if(reveal){const b=reveal.querySelector('[data-ux461-toggle]');if(b)b.textContent=expanded?'Fechar navegação':'Explorar';}
    // Keep the landing decisional: priorities + reinforce + review visible first.
    const research=card('research',c);if(research)research.classList.add('ux461-secondary-card');
  }
  function jump(kind){
    const c=root();const target=card(kind,c);if(!target)return;
    c.dataset.ux461Expanded='1';simplifyLanding();
    if(target.classList.contains('is-collapsed'))target.querySelector('[data-collapse-toggle]')?.click();
    setTimeout(()=>target.scrollIntoView({behavior:'smooth',block:'start'}),35);
  }
  function style(){
    if(document.getElementById('vestra-v461-style'))return;const s=document.createElement('style');s.id='vestra-v461-style';s.textContent=`
      .ux461-snapshot{margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,.13)}.ux461-snapshot-head{display:flex;justify-content:space-between;gap:10px;align-items:end;margin-bottom:9px}.ux461-snapshot-head>div{display:grid;gap:2px}.ux461-snapshot-head small{font-size:8px;letter-spacing:.12em;font-weight:900;opacity:.65}.ux461-snapshot-head strong{font-size:13px}.ux461-snapshot-head>span{font-size:8px;opacity:.65;text-align:right}.ux461-health{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.ux461-health-row{display:grid;gap:5px;padding:9px;border-radius:13px;background:rgba(255,255,255,.08)}.ux461-health-row>div:first-child{display:flex;justify-content:space-between;gap:6px;align-items:center}.ux461-health-row span{font-size:8px;opacity:.7}.ux461-health-row b{font-size:9px}.ux461-track{height:5px;background:rgba(255,255,255,.12);border-radius:999px;overflow:hidden}.ux461-track i{display:block;height:100%;border-radius:999px}.ux461-track i.is-good{background:#68d5aa}.ux461-track i.is-warn{background:#f0c35a}.ux461-track i.is-bad{background:#ee8b76}.ux461-track i.is-neutral{background:#9ec4c7}
      .ux461-reveal{margin:0 0 12px;padding:12px 13px;border-radius:18px;border:1px solid var(--line);background:linear-gradient(135deg,color-mix(in srgb,var(--accent,#168e89) 7%,var(--card)),var(--card));display:flex;justify-content:space-between;align-items:center;gap:12px}.ux461-reveal>div{display:grid;gap:2px}.ux461-reveal small{font-size:8px;letter-spacing:.12em;font-weight:900;color:var(--accent,#168e89)}.ux461-reveal strong{font-size:14px}.ux461-reveal span{font-size:9px;color:var(--text2)}.ux461-reveal button{border:0;border-radius:999px;padding:8px 11px;background:var(--accent,#168e89);color:#fff;font-size:9px;font-weight:850;white-space:nowrap}
      .ux461-secondary-nav[hidden]{display:none!important}.ux461-portfolio .ux458-pulse[hidden]{display:none!important}.ux461-portfolio .ux460-nav-secondary[hidden]{display:none!important}
      .ux461-portfolio .ux455-group-label[data-ux455-group="decide"]{margin-top:10px}.ux461-portfolio .ux455-group-label[data-ux455-group="decide"] span{font-size:17px}.ux461-portfolio .ux455-group-label[data-ux455-group="decide"] small{font-size:10px}
      @media(max-width:620px){.ux461-health{grid-template-columns:1fr}.ux461-snapshot-head>span{display:none}.ux461-reveal{align-items:flex-start}.ux461-reveal span{max-width:210px}}
    `;document.head.appendChild(s);
  }
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-ux461-toggle]');if(b){const c=root();if(!c)return;c.dataset.ux461Expanded=c.dataset.ux461Expanded==='1'?'0':'1';simplifyLanding();return;}
    const j=e.target.closest?.('[data-ux460-jump]');if(j){jump(j.dataset.ux460Jump);}
  },true);
  function apply(){installSnapshot();simplifyLanding();}
  function start(){style();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
