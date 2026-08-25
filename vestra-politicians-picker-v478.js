/* Vestra v4.78 — politician search autocomplete + followed politicians dropdown. */
(() => {
  'use strict';
  const FOLLOW_KEY='vestra-politician-follows-v4';
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
  let pending=false;

  const section=()=>document.querySelector('.politicians-section');
  const picker=s=>s?.querySelector('[data-politician-select]');
  const searchInput=s=>[...s?.querySelectorAll('input')||[]].find(i=>/Procurar|Trump|Pelosi|Tuberville/i.test(t(i.placeholder)))||null;
  const follows=()=>{try{return JSON.parse(localStorage.getItem(FOLLOW_KEY)||'[]').filter(x=>x?.value&&x?.label)}catch{return[]}};
  const options=s=>[...picker(s)?.options||[]].map(o=>({value:t(o.value),label:t(o.textContent)})).filter(x=>x.value&&x.label);
  const choose=(s,value)=>{const sel=picker(s);if(!sel)return;sel.value=value;sel.dispatchEvent(new Event('change',{bubbles:true}));};

  function renderFollowDropdown(s){
    if(!s)return;
    const hub=s.querySelector('.ux476-followhub');
    if(!hub)return;
    const fs=follows();
    hub.innerHTML=`<div class="ux478-followhead"><div><small>A SEGUIR</small><strong>Políticos acompanhados</strong></div><span>${fs.length}</span></div>${fs.length?`<label class="ux478-followselect"><span>Escolher acompanhado</span><select data-ux478-followselect><option value="">Selecionar político…</option>${fs.map(x=>`<option value="${esc(x.value)}">★ ${esc(x.label)}</option>`).join('')}</select></label>`:'<p>Ainda não segues nenhum político.</p>'}`;
  }

  function setupSearch(s){
    const input=searchInput(s); if(!input)return;
    input.setAttribute('autocomplete','off');
    input.setAttribute('autocapitalize','none');
    input.setAttribute('spellcheck','false');
    let box=s.querySelector('.ux478-search-results');
    if(!box){box=document.createElement('div');box.className='ux478-search-results';input.insertAdjacentElement('afterend',box);}

    const paint=()=>{
      const q=t(input.value).toLocaleLowerCase('en');
      if(!q){box.hidden=true;box.innerHTML='';return;}
      const found=options(s).filter(x=>x.label.toLocaleLowerCase('en').includes(q)).slice(0,8);
      box.innerHTML=found.length?found.map(x=>`<button type="button" data-ux478-person="${esc(x.value)}"><b>${esc(x.label.split(' · ')[0])}</b><small>${esc(x.label.includes(' · ')?x.label.split(' · ').slice(1).join(' · '):'')}</small></button>`).join(''):'<div class="ux478-empty">Sem correspondências nos perfis carregados.</div>';
      box.hidden=false;
      // Hide legacy autocomplete status/result blocks so there is only one result surface.
      [...s.querySelectorAll('div,ul')].forEach(x=>{
        if(x===box||x.contains(box)||box.contains(x))return;
        const tx=t(x.textContent);
        if(tx==='Sem correspondências.'||tx==='Sem correspondências')x.hidden=true;
      });
    };
    if(!input.dataset.ux478Bound){
      input.dataset.ux478Bound='1';
      input.addEventListener('input',paint);
      input.addEventListener('focus',()=>{if(t(input.value))paint();});
      input.addEventListener('keydown',e=>{if(e.key==='Escape'){box.hidden=true;input.blur();}});
    }
    if(t(input.value))paint(); else box.hidden=true;
  }

  function style(){if(document.getElementById('vestra-v478-style'))return;const st=document.createElement('style');st.id='vestra-v478-style';st.textContent=`
    .ux476-followhub{padding:14px!important}.ux478-followhead{display:flex;align-items:center;justify-content:space-between;gap:10px}.ux478-followhead>div{display:grid;gap:2px}.ux478-followhead small{font-size:8px;letter-spacing:.14em;font-weight:900;color:var(--accent,#168e89)}.ux478-followhead strong{font-size:14px}.ux478-followhead>span{font-size:9px;color:var(--text2)}
    .ux478-followselect{display:grid;gap:5px;margin-top:10px}.ux478-followselect>span{font-size:8px;font-weight:850;color:var(--text2);letter-spacing:.08em;text-transform:uppercase}.ux478-followselect select{width:100%;border:1px solid var(--line);border-radius:13px;background:var(--soft);color:var(--text);padding:11px 12px;font:inherit;font-size:11px;font-weight:750}
    .politicians-section{position:relative}.ux478-search-results{position:relative;z-index:8;margin:-1px 0 10px;border:1px solid var(--line);border-radius:0 0 14px 14px;background:var(--card);box-shadow:0 12px 24px rgba(17,44,51,.10);overflow:hidden}.ux478-search-results[hidden]{display:none!important}.ux478-search-results button{display:grid;width:100%;gap:2px;padding:10px 12px;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--text);text-align:left}.ux478-search-results button:last-child{border-bottom:0}.ux478-search-results button:active{background:var(--soft)}.ux478-search-results b{font-size:11px}.ux478-search-results small{font-size:8.5px;color:var(--text2)}.ux478-empty{padding:11px 12px;font-size:10px;color:var(--text2);font-style:italic}
  `;document.head.appendChild(st);}

  function apply(){const s=section();if(!s)return;renderFollowDropdown(s);setupSearch(s);}
  document.addEventListener('change',e=>{
    const sel=e.target.closest?.('[data-ux478-followselect]'); if(sel&&sel.value){const s=section();choose(s,sel.value);sel.value='';}
  },true);
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-ux478-person]');if(b){const s=section(),input=searchInput(s),box=s?.querySelector('.ux478-search-results');choose(s,b.dataset.ux478Person);if(input)input.value='';if(box)box.hidden=true;return;}
    if(e.target.closest?.('[data-ux475-follow]'))setTimeout(()=>renderFollowDropdown(section()),40);
    if(!e.target.closest?.('.ux478-search-results')&&!e.target.closest?.('input')){const box=section()?.querySelector('.ux478-search-results');if(box)box.hidden=true;}
  },true);

  function start(){style();apply();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();