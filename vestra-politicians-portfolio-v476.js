/* Vestra v4.76 — followed politicians hub + clearer swap scenario scores. */
(() => {
  'use strict';
  const FOLLOW_KEY='vestra-politician-follows-v4';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let stocks=[], byTicker=new Map(), loading=null, pending=false;
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};

  function loadStocks(){
    if(loading)return loading;
    loading=fetch('./data/stocks.json?v=4.76',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{
      stocks=Array.isArray(d)?d:(d?.stocks||[]); byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s])); return stocks;
    }).catch(()=>[]); return loading;
  }
  function stock(tk){const x=t(tk).toUpperCase();return byTicker.get(x)||stocks.find(s=>t(s?.ticker).toUpperCase().split('.')[0]===x.split('.')[0])||null;}
  function readFollows(){try{return JSON.parse(localStorage.getItem(FOLLOW_KEY)||'[]').filter(x=>x?.value&&x?.label)}catch{return[]}}
  function writeFollows(x){try{localStorage.setItem(FOLLOW_KEY,JSON.stringify(x))}catch{}}

  function cleanPoliticalLegacy(s){
    if(!s)return;
    // Old base filters and summary cards are redundant with the canonical v4.75 activity view.
    [...s.querySelectorAll('div,nav,section')].forEach(x=>{
      if(x.classList.contains('ux475-shell')||x.classList.contains('ux476-followhub'))return;
      const buttons=[...x.querySelectorAll(':scope > button')];
      const labels=buttons.map(b=>t(b.textContent)).join('|');
      if(buttons.length>=3&&/Tudo/i.test(labels)&&/Compras/i.test(labels)&&/Vendas/i.test(labels)&&( /Favorito/i.test(labels)||/Seguir/i.test(labels))) x.hidden=true;
    });
    [...s.querySelectorAll('.market-detail-card')].forEach(card=>{
      const tx=t(card.textContent);
      if(/^RADAR RÁPIDO/i.test(tx)||/^Compras em destaque/i.test(tx)||/^Vendas em destaque/i.test(tx)) card.hidden=true;
    });
  }

  function followedHub(s){
    const picker=s?.querySelector('.politician-picker'); if(!s||!picker)return;
    let hub=s.querySelector('.ux476-followhub');
    if(!hub){hub=document.createElement('section');hub.className='ux476-followhub';picker.insertAdjacentElement('beforebegin',hub);}
    const follows=readFollows();
    hub.innerHTML=`<div class="ux476-followhead"><div><small>A SEGUIR</small><strong>Políticos acompanhados</strong></div><span>${follows.length}</span></div>${follows.length?`<div class="ux476-followchips">${follows.map(x=>`<button type="button" data-ux476-pick="${esc(x.value)}">★ ${esc(x.label)}</button>`).join('')}</div>`:'<p>Ainda não segues nenhum político.</p>'}`;
  }

  function simplifyPoliticianShell(s){
    const shell=s?.querySelector('.ux475-shell'); if(!shell)return;
    // The follow list belongs outside the selected-politician card.
    shell.querySelector('[data-ux475-view="follow"]')?.remove();
    shell.querySelector('.ux475-followview')?.remove();
    // Keep one explicit follow action in each selected profile.
    const person=shell.querySelector('.ux475-person');
    const follow=person?.querySelector('[data-ux475-follow]');
    if(follow) follow.textContent=follow.classList.contains('is-on')?'★ A seguir':'☆ Seguir político';
    // Two clear tabs only.
    const tabs=shell.querySelector('.ux475-tabs'); if(tabs)tabs.style.gridTemplateColumns='1fr 1fr';
  }

  function scenarioPolish(){
    const sh=document.getElementById('marketSheet'), root=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!root||!stocks.length)return;
    root.querySelectorAll('.market-scenario-row').forEach(row=>{
      const strong=row.querySelector('strong'), small=row.querySelector('small'); if(!strong||!small)return;
      const m=t(strong.textContent).match(/^\s*([^\s]+)\s*→\s*([^\s]+)\s*$/); if(!m)return;
      const a=stock(m[1]),b=stock(m[2]); const sa=n(a?.score),sb=n(b?.score);
      const old=t(small.textContent);
      const cm=old.match(/Convicção carteira\s*([\d.,]+)\s*→\s*([\d.,]+)/i);
      const om=old.match(/overlap\s*([\d.,]+)%\s*→\s*([\d.,]+)%/i);
      const global=cm?`${cm[1]} → ${cm[2]}`:'—';
      const overlap=om?`${om[1]}% → ${om[2]}%`:'—';
      const scoreTxt=sa!=null&&sb!=null?`${Math.round(sa)} → ${Math.round(sb)}`:'—';
      small.innerHTML=`<span class="ux476-position-score"><b>Score da posição</b> ${scoreTxt}</span><span><b>Impacto global</b> ${esc(global)}</span><span><b>Overlap</b> ${esc(overlap)}</span>`;
      if(cm&&cm[1]===cm[2]){
        const em=row.querySelector('em'); if(em&&t(em.textContent)==='Neutro') em.title='A posição é pequena face à carteira total; o impacto global arredondado pode parecer igual mesmo quando os scores das empresas são diferentes.';
      }
    });
    const card=root.querySelector('.market-scenario-preview');
    const note=card?.querySelector('.market-case-note');
    if(note)note.textContent='Compara o Score Vestra da posição atual com a alternativa e, separadamente, o impacto ponderado na carteira. Numa carteira grande, o impacto global pode arredondar para o mesmo valor.';
  }

  function style(){if(document.getElementById('vestra-v476-style'))return;const s=document.createElement('style');s.id='vestra-v476-style';s.textContent=`
    .ux476-followhub{margin:10px 0 12px;padding:11px 12px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent,#168e89) 7%,var(--card)),var(--card))}.ux476-followhead{display:flex;justify-content:space-between;align-items:center;gap:8px}.ux476-followhead>div{display:grid;gap:1px}.ux476-followhead small{font-size:8px;letter-spacing:.12em;font-weight:900;color:var(--accent,#168e89)}.ux476-followhead strong{font-size:12px}.ux476-followhead span{font-size:8px;color:var(--text2)}.ux476-followchips{display:flex;gap:6px;overflow-x:auto;margin-top:8px;scrollbar-width:none}.ux476-followchips button{flex:0 0 auto;border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:7px 9px;color:var(--text);font-size:9px;font-weight:800}.ux476-followhub p{margin:6px 0 0;font-size:9px;color:var(--text2)}
    .ux475-tabs{grid-template-columns:1fr 1fr!important}.ux475-tabs [data-ux475-view="follow"]{display:none!important}.politicians-section .market-detail-card[hidden]{display:none!important}
    .market-scenario-row small{display:grid!important;gap:2px!important;margin-top:3px}.market-scenario-row small>span{font-size:9px;color:var(--text2)}.market-scenario-row small b{color:var(--text);font-weight:800}.market-scenario-row .ux476-position-score{font-size:10px;color:var(--text)}
  `;document.head.appendChild(s);}

  function apply(){const s=document.querySelector('.politicians-section');cleanPoliticalLegacy(s);followedHub(s);simplifyPoliticianShell(s);scenarioPolish();}
  document.addEventListener('click',e=>{
    const pick=e.target.closest?.('[data-ux476-pick]'); if(pick){const s=document.querySelector('.politicians-section'),sel=s?.querySelector('[data-politician-select]');if(sel){sel.value=pick.dataset.ux476Pick;sel.dispatchEvent(new Event('change',{bubbles:true}));}return;}
    if(e.target.closest?.('[data-ux475-follow]')) setTimeout(()=>{const s=document.querySelector('.politicians-section');followedHub(s);simplifyPoliticianShell(s);},30);
  },true);
  function start(){style();loadStocks().then(()=>{apply();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();