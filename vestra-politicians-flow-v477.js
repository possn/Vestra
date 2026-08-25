/* Vestra v4.77 — global political flow summary + stricter politician control cleanup + clearer swap deltas. */
(() => {
  'use strict';
  const FOLLOW_KEY='vestra-politician-follows-v4';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  let flowData=null, flowLoading=null, pending=false;

  const section=()=>document.querySelector('.politicians-section');
  const readFollows=()=>{try{return JSON.parse(localStorage.getItem(FOLLOW_KEY)||'[]').filter(x=>x?.value&&x?.label)}catch{return[]}};

  function hideLegacyControls(s){
    if(!s)return;
    // Hide the old strip Tudo / Compras / Vendas / Favorito wherever an older renderer recreates it.
    [...s.querySelectorAll('div,nav,section')].forEach(x=>{
      if(x.closest('.ux475-shell')||x.closest('.ux477-flow')||x.closest('.ux477-followhub'))return;
      const bs=[...x.querySelectorAll('button')];
      if(bs.length<3||bs.length>8)return;
      const labels=bs.map(b=>t(b.textContent)).join(' | ');
      if(/\bTudo\b/i.test(labels)&&/Compras/i.test(labels)&&/Vendas/i.test(labels)&&( /Favorito/i.test(labels)||/Seguir/i.test(labels))){
        x.classList.add('ux477-hide-legacy');
        x.hidden=true;
      }
    });
    // Legacy summary blocks are replaced by the single global flow card below.
    s.querySelectorAll('.ux454-flow,.ux458-politician-leaders').forEach(x=>{x.hidden=true;x.classList.add('ux477-hide-legacy');});
    [...s.querySelectorAll('.market-detail-card')].forEach(card=>{
      const tx=t(card.textContent);
      if(/^RADAR RÁPIDO/i.test(tx)||/^Compras em destaque/i.test(tx)||/^Vendas em destaque/i.test(tx)){
        card.hidden=true;card.classList.add('ux477-hide-legacy');
      }
    });
  }

  async function loadFlow(){
    if(flowData)return flowData;
    if(flowLoading)return flowLoading;
    flowLoading=(async()=>{
      try{
        const from=new Date(Date.now()-120*86400000).toISOString().slice(0,10);
        const r=await fetch(`https://www.bargo.ai/free-apis/congress/v1/trades?from=${from}&limit=100`,{cache:'no-store',mode:'cors'});
        if(!r.ok)throw new Error(String(r.status));
        const d=await r.json();
        flowData=Array.isArray(d)?d:(d?.trades||d?.data||[]);
      }catch(_){flowData=[];}
      return flowData;
    })();
    return flowLoading;
  }

  function topTickers(rows,typeRe){
    const m=new Map();
    rows.filter(x=>typeRe.test(t(x?.type||x?.transaction))).forEach(x=>{
      const tk=t(x?.ticker).toUpperCase(); if(!tk)return;
      m.set(tk,(m.get(tk)||0)+1);
    });
    return [...m.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,5);
  }

  function renderFlow(s){
    if(!s)return;
    let card=s.querySelector('.ux477-flow');
    if(!card){
      card=document.createElement('section'); card.className='ux477-flow';
      const search=s.querySelector('input[placeholder*="Trump"]');
      const anchor=search?.parentElement||s.querySelector('.politician-picker');
      if(anchor) anchor.insertAdjacentElement('beforebegin',card); else s.prepend(card);
    }
    if(!flowData){card.innerHTML='<div class="ux477-flowhead"><div><small>FLUXO POLÍTICO</small><strong>O que os políticos estão a negociar</strong></div><span>últimas 100</span></div><p class="ux477-loading">A atualizar…</p>';return;}
    const buys=topTickers(flowData,BUY), sells=topTickers(flowData,SELL);
    const list=(arr,tone)=>`<div class="ux477-flowcol ${tone}"><b>${tone==='buy'?'↗ Mais compradas':'↘ Mais vendidas'}</b>${arr.length?arr.map(([tk,c])=>`<button type="button" data-market-ticker="${esc(tk)}"><strong>${esc(tk)}</strong><span>${c} ${c===1?'operação':'operações'}</span></button>`).join(''):'<small>Sem dados recentes.</small>'}</div>`;
    card.innerHTML=`<div class="ux477-flowhead"><div><small>FLUXO POLÍTICO</small><strong>Top 5 das últimas divulgações</strong></div><span>100 operações</span></div><div class="ux477-flowgrid">${list(buys,'buy')}${list(sells,'sell')}</div><p>Resumo global. Para ver operações individuais, escolhe um político abaixo.</p>`;
  }

  function renderFollowHub(s){
    if(!s)return;
    // Disable the older hub so there is only one canonical followed-politicians area.
    s.querySelectorAll('.ux476-followhub').forEach(x=>{x.hidden=true;});
    const follows=readFollows();
    let hub=s.querySelector('.ux477-followhub');
    if(!hub){
      hub=document.createElement('section');hub.className='ux477-followhub';
      const picker=s.querySelector('.politician-picker');
      if(picker)picker.insertAdjacentElement('beforebegin',hub);else s.appendChild(hub);
    }
    hub.innerHTML=`<div class="ux477-followhead"><div><small>A SEGUIR</small><strong>Políticos acompanhados</strong></div><span>${follows.length}</span></div>${follows.length?`<div class="ux477-followchips">${follows.map(x=>`<button type="button" data-ux477-pick="${esc(x.value)}">★ ${esc(x.label)}</button>`).join('')}</div>`:'<p>Ainda não segues nenhum político.</p>'}`;
  }

  function simplifySelectedPolitician(s){
    const shell=s?.querySelector('.ux475-shell'); if(!shell)return;
    const tabs=shell.querySelector('.ux475-tabs');
    if(tabs){
      tabs.querySelector('[data-ux475-view="follow"]')?.remove();
      tabs.style.gridTemplateColumns='1fr 1fr';
    }
    shell.querySelector('.ux475-followview')?.remove();
    const follow=shell.querySelector('[data-ux475-follow]');
    if(follow)follow.textContent=follow.classList.contains('is-on')?'★ A seguir':'☆ Seguir político';
  }

  function polishScenario(){
    const sh=document.getElementById('marketSheet'),root=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!root)return;
    root.querySelectorAll('.market-scenario-row').forEach(row=>{
      const scoreLine=row.querySelector('.ux476-position-score'); if(!scoreLine)return;
      const nums=t(scoreLine.textContent).match(/(\d+)\s*→\s*(\d+)/); if(!nums)return;
      const a=Number(nums[1]),b=Number(nums[2]),d=b-a;
      scoreLine.innerHTML=`<b>Score Vestra</b> ${a} → ${b} <em class="${d>0?'is-up':d<0?'is-down':''}">${d>0?'+':''}${d}</em>`;
      const spans=[...row.querySelectorAll('small>span')];
      const global=spans.find(x=>/Impacto global/i.test(t(x.textContent)));
      if(global){
        const m=t(global.textContent).match(/([\d.,]+)\s*→\s*([\d.,]+)/);
        if(m&&m[1]===m[2])global.innerHTML=`<b>Impacto na carteira</b> ${m[1]} → ${m[2]} <em>&lt;0,1 pt</em>`;
      }
    });
  }

  function style(){
    if(document.getElementById('vestra-v477-style'))return;
    const st=document.createElement('style');st.id='vestra-v477-style';st.textContent=`
      .politicians-section .ux477-hide-legacy,.politicians-section .ux476-followhub[hidden]{display:none!important}
      .ux477-flow{margin:10px 0 12px;padding:13px;border-radius:18px;background:linear-gradient(145deg,#0d555f,#14726f);color:#fff}.ux477-flowhead,.ux477-followhead{display:flex;align-items:center;justify-content:space-between;gap:8px}.ux477-flowhead>div,.ux477-followhead>div{display:grid;gap:2px}.ux477-flowhead small,.ux477-followhead small{font-size:8px;letter-spacing:.13em;font-weight:900;opacity:.78}.ux477-flowhead strong{font-size:14px}.ux477-flowhead>span{font-size:8px;padding:5px 7px;border-radius:999px;background:rgba(255,255,255,.11)}.ux477-flowgrid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:11px}.ux477-flowcol{display:grid;gap:3px;padding:10px;border-radius:14px;background:rgba(255,255,255,.08)}.ux477-flowcol>b{font-size:10px;margin-bottom:2px}.ux477-flowcol button{display:flex;justify-content:space-between;gap:6px;border:0;background:transparent;color:#fff;padding:6px 0;text-align:left}.ux477-flowcol button strong{font-size:10px}.ux477-flowcol button span{font-size:8px;opacity:.7}.ux477-flow>p,.ux477-loading{margin:9px 0 0;font-size:8.5px;opacity:.72}
      .ux477-followhub{margin:8px 0 10px;padding:10px 11px;border:1px solid var(--line);border-radius:15px;background:var(--soft)}.ux477-followhead strong{font-size:11px}.ux477-followhead>span{font-size:8px;color:var(--text2)}.ux477-followchips{display:flex;gap:6px;overflow-x:auto;margin-top:7px;scrollbar-width:none}.ux477-followchips button{flex:0 0 auto;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:999px;padding:7px 9px;font-size:9px;font-weight:800}.ux477-followhub p{margin:5px 0 0;font-size:8.5px;color:var(--text2)}
      .market-scenario-row .ux476-position-score{font-size:10px!important}.market-scenario-row .ux476-position-score em{font-style:normal;margin-left:4px;font-weight:900;color:#687b82}.market-scenario-row .ux476-position-score em.is-up{color:#168a69}.market-scenario-row .ux476-position-score em.is-down{color:#c05252}.market-scenario-row small>span em{font-style:normal;font-weight:800;color:#74858b}
      @media(max-width:620px){.ux477-flowgrid{grid-template-columns:1fr 1fr}.ux477-flow{padding:11px}.ux477-flowcol{padding:9px 8px}.ux477-flowcol button span{font-size:7.5px}}
    `;document.head.appendChild(st);
  }

  function apply(){const s=section();if(!s)return;hideLegacyControls(s);renderFlow(s);renderFollowHub(s);simplifySelectedPolitician(s);polishScenario();}

  document.addEventListener('click',e=>{
    const pick=e.target.closest?.('[data-ux477-pick]');if(pick){const s=section(),sel=s?.querySelector('[data-politician-select]');if(sel){sel.value=pick.dataset.ux477Pick;sel.dispatchEvent(new Event('change',{bubbles:true}));}return;}
    if(e.target.closest?.('[data-ux475-follow]'))setTimeout(()=>renderFollowHub(section()),40);
  },true);

  function start(){style();apply();loadFlow().then(()=>renderFlow(section()));const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();