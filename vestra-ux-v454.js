/* Vestra UX v4.54 — portfolio hierarchy, swap focus, opportunity podium and political flow. */
(() => {
  'use strict';
  const VERSION='4.54';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function rankOpportunityRows(){
    const section=[...document.querySelectorAll('.market-section')].find(x=>/Oportunidades agora|Melhores oportunidades/.test(t(x.querySelector('h3')?.textContent)));
    const list=section?.querySelector('.market-list');if(!section||!list)return;
    const rows=[...list.querySelectorAll('.market-row')];if(!rows.length)return;
    rows.forEach((r,i)=>{
      r.classList.toggle('ux454-podium',i<3);
      r.classList.toggle('ux454-podium-1',i===0);
      r.classList.toggle('ux454-podium-2',i===1);
      r.classList.toggle('ux454-podium-3',i===2);
      if(i<3&&!r.querySelector('.ux454-rank')){
        const b=document.createElement('span');b.className='ux454-rank';b.textContent=`#${i+1}`;r.prepend(b);
      }
    });
    if(!section.querySelector('.ux454-opportunity-guide')){
      const g=document.createElement('div');g.className='ux454-opportunity-guide';
      g.innerHTML='<span><b>ENTRY</b> combinação de qualidade + timing</span><span><b>Timing</b> evita perseguir preço esticado</span><span><b>Sinais</b> confirmações independentes</span>';
      const head=section.querySelector('.market-section__head');head?.insertAdjacentElement('afterend',g);
    }
  }

  function style(){
    if(document.getElementById('vestra-ux-v454-style'))return;
    const s=document.createElement('style');s.id='vestra-ux-v454-style';s.textContent=`
      .ux454-portfolio{--uxPad:14px}.ux454-nav-title{margin:10px 0 0;padding:14px 15px 4px;display:flex;align-items:end;justify-content:space-between}.ux454-nav-title div{display:grid}.ux454-nav-title small{font-size:8.5px;letter-spacing:.14em;font-weight:900;color:var(--accent,#168e89)}.ux454-nav-title strong{font-size:17px;margin-top:2px}.ux454-nav-title>span{font-size:9px;color:var(--text2);max-width:120px;text-align:right}.ux454-toolbar{margin-top:4px!important;border-radius:18px!important;background:linear-gradient(135deg,color-mix(in srgb,var(--accent,#168e89) 8%,var(--card)),var(--card))!important}.ux454-focus{margin-top:7px!important}.ux454-shortcuts{margin-top:7px!important;padding:3px!important;background:transparent!important;border:0!important;box-shadow:none!important}.ux454-shortcuts button{min-height:44px!important;border-radius:14px!important;background:var(--card)!important;border:1px solid var(--line)!important;box-shadow:0 4px 14px rgba(20,50,55,.045)!important}
      .ux454-group-label{display:grid;gap:2px;margin:18px 3px 8px;padding-left:3px}.ux454-group-label span{font-size:13px;font-weight:900;color:var(--text)}.ux454-group-label small{font-size:9.5px;color:var(--text2)}.ux454-purpose{display:none}.market-detail-card.is-collapsed>.ux454-purpose{display:block!important;position:absolute;left:52px;right:50px;bottom:12px;font-size:9px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ux454-portfolio .market-detail-card.is-collapsed{min-height:78px!important;padding-bottom:27px!important}.ux454-portfolio .market-detail-card:not(.is-collapsed){box-shadow:0 8px 26px rgba(18,52,58,.055)}
      .ux454-swap-head,.ux454-overlap-head{margin:-2px -2px 12px;padding:13px;border-radius:15px;background:linear-gradient(135deg,#f3efff,#faf8ff);display:flex;align-items:center;justify-content:space-between;gap:10px}.ux454-swap-head div{display:grid;gap:2px}.ux454-swap-head small,.ux454-overlap-head small{font-size:8px;font-weight:900;letter-spacing:.12em;color:#6a55aa}.ux454-swap-head strong,.ux454-overlap-head strong{font-size:14px}.ux454-swap-head span{font-size:9px;color:var(--text2)}.ux454-swap-head button{border:0;border-radius:999px;padding:8px 11px;background:#7664b7;color:white;font-size:10px;font-weight:800}.ux454-overlap-head{display:grid;background:linear-gradient(135deg,#fff3df,#fffaf1)}.ux454-overlap-head small{color:#9a6819}
      .ux454-opportunity-guide{display:flex;gap:6px;overflow-x:auto;padding:0 1px 9px;margin-top:-2px;scrollbar-width:none}.ux454-opportunity-guide span{flex:0 0 auto;padding:6px 8px;border-radius:999px;background:var(--soft);font-size:8.5px;color:var(--text2)}.ux454-opportunity-guide b{color:var(--text);margin-right:3px}.ux454-podium{position:relative!important;border-width:1.5px!important}.ux454-podium-1{background:linear-gradient(145deg,color-mix(in srgb,var(--accent,#168e89) 12%,var(--card)),var(--card))!important;box-shadow:0 10px 26px rgba(18,118,111,.10)!important}.ux454-podium-2{background:linear-gradient(145deg,#f3f6fb,var(--card))!important}.ux454-podium-3{background:linear-gradient(145deg,#fff7ec,var(--card))!important}.ux454-rank{position:absolute;right:8px;top:7px;font-size:8px;font-weight:900;letter-spacing:.08em;color:var(--text2);opacity:.8}
    `;document.head.appendChild(s);
  }

  function apply(){rankOpportunityRows();}
  function start(){style();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-ux454-open-swap]');if(!b)return;e.preventDefault();e.stopPropagation();const card=b.closest('[data-ux-kind="swap"]');if(card?.classList.contains('is-collapsed'))card.querySelector('[data-collapse-toggle]')?.click();setTimeout(()=>card?.scrollIntoView({behavior:'smooth',block:'start'}),20);
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
