from pathlib import Path

p=Path('market.js')
s=p.read_text()
anchor="  function renderPortfolioDecisionCenter(rows,total){\n"
if anchor not in s: raise SystemExit('decision center anchor missing')
block=r'''  const RESEARCH_QUEUE_KEY='vestra_research_queue_v1';
  function loadResearchQueue(){
    try{ const x=JSON.parse(localStorage.getItem(RESEARCH_QUEUE_KEY)||'{}'); return x&&typeof x==='object'?x:{}; }
    catch{return {};}
  }
  function saveResearchQueue(x){ try{localStorage.setItem(RESEARCH_QUEUE_KEY,JSON.stringify(x||{}));}catch{} }
  function researchQueueState(ticker){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(), x=all[key]||{};
    if(x.status==='snoozed'&&Number(x.snoozeUntil||0)<=Date.now()) return {...x,status:'new',snoozeUntil:0};
    return {status:x.status||'new',snoozeUntil:Number(x.snoozeUntil||0),updatedAt:Number(x.updatedAt||0)};
  }
  function setResearchQueueState(ticker,status){
    const all=loadResearchQueue(), key=txt(ticker).toUpperCase(); if(!key)return;
    all[key]={status,updatedAt:Date.now(),snoozeUntil:status==='snoozed'?Date.now()+7*86400000:0};
    saveResearchQueue(all);
  }
  function renderResearchQueue(review){
    const rank={new:0,in_review:1,snoozed:2,reviewed:3};
    const items=review.map(r=>({r,state:researchQueueState(r.stock.ticker)})).sort((a,b)=>(rank[a.state.status]??9)-(rank[b.state.status]??9)||(a.r.conviction??999)-(b.r.conviction??999));
    const counts=items.reduce((a,x)=>{a[x.state.status]=(a[x.state.status]||0)+1;return a;},{});
    const visible=items.filter(x=>x.state.status!=='reviewed'&&x.state.status!=='snoozed').slice(0,12);
    const label={new:'Novo',in_review:'Em revisão',reviewed:'Revisto',snoozed:'Adiado'};
    const tone={new:'is-risk',in_review:'is-warn',reviewed:'is-positive',snoozed:''};
    const rows=visible.length?visible.map(({r,state})=>`<div class="market-research-queue-row" data-queue-ticker="${esc(r.stock.ticker)}"><button type="button" class="market-research-queue-main" data-market-ticker="${esc(r.stock.ticker)}"><span><strong>${esc(r.stock.ticker)}</strong><small>${r.conviction==null?'convicção insuficiente':`convicção ${Math.round(r.conviction)}/100`} · ${esc(txt(r.stock.risk_gate)||'clear')}</small></span><em class="${tone[state.status]||''}">${label[state.status]||'Novo'}</em></button><div class="market-research-queue-actions"><button type="button" data-queue-status="in_review">Em revisão</button><button type="button" data-queue-status="reviewed">Revisto</button><button type="button" data-queue-status="snoozed">Adiar 7d</button></div></div>`).join(''):'<p class="market-case-note">Sem revisões ativas pendentes. Itens adiados regressam automaticamente após 7 dias.</p>';
    return `<div class="market-detail-card market-research-queue"><div class="market-perspective-head"><div><small>RESEARCH QUEUE · LOCAL</small><h4>Fila de revisão</h4></div><span class="market-data-age">${(counts.new||0)+(counts.in_review||0)} pendentes</span></div><div class="market-action-context"><span>${counts.new||0} novos</span><span>${counts.in_review||0} em revisão</span><span>${counts.snoozed||0} adiados</span><span>${counts.reviewed||0} revistos</span></div><p class="market-case-note">Memória operacional: organiza o research sem alterar Score Vestra, Action Map ou carteira.</p><div class="market-research-queue-list">${rows}</div>${items.length>12?`<p class="market-case-note">A mostrar as 12 prioridades ativas mais urgentes de ${items.length} posições sinalizadas.</p>`:''}</div>`;
  }

'''
s=s.replace(anchor,block+anchor,1)
needle='<p class="market-case-note">Síntese executiva: toca num sinal para abrir diretamente o detalhe correspondente. Não cria um novo score de investimento.</p></div>`;\n  }\n\n  function portfolioIntelligence(rows,total){'
repl='<p class="market-case-note">Síntese executiva: toca num sinal para abrir diretamente o detalhe correspondente. Não cria um novo score de investimento.</p></div>${renderResearchQueue(review)}`;\n  }\n\n  function portfolioIntelligence(rows,total){'
if needle not in s: raise SystemExit('decision template tail missing')
s=s.replace(needle,repl,1)
handler_anchor="  // v6.0.1 — Action Map summary acts as an immediate filter.\n"
if handler_anchor not in s: raise SystemExit('handler anchor missing')
handler=r'''  // v6.2 — Research Queue state is local operational memory.
  document.addEventListener('click', e=>{
    const btn=e.target.closest?.('[data-queue-status]'); if(!btn)return;
    const row=btn.closest('.market-research-queue-row'); if(!row)return;
    e.preventDefault(); e.stopPropagation();
    setResearchQueueState(row.dataset.queueTicker||'',btn.dataset.queueStatus||'new');
    renderPrimary();
    requestAnimationFrame(()=>document.querySelector('.market-research-queue')?.scrollIntoView?.({behavior:'smooth',block:'start'}));
  });

'''
s=s.replace(handler_anchor,handler+handler_anchor,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text(); c += r'''

/* v6.2 — Research Queue */
.market-research-queue-list{display:grid;gap:8px;margin-top:10px}.market-research-queue-row{border:1px solid var(--line2);border-radius:15px;background:var(--item-bg);overflow:hidden}.market-research-queue-main{width:100%;border:0;background:transparent;color:var(--text);padding:11px 12px;display:flex;justify-content:space-between;align-items:center;gap:10px;text-align:left;cursor:pointer}.market-research-queue-main span{min-width:0}.market-research-queue-main strong{display:block;font-size:13px}.market-research-queue-main small{display:block;color:var(--muted);font-size:10px;margin-top:2px}.market-research-queue-main em{font-style:normal;font-size:9px;font-weight:850;border-radius:999px;padding:5px 8px;background:var(--card2);white-space:nowrap}.market-research-queue-main em.is-risk{background:rgba(229,88,77,.10);color:#9b4b44}.market-research-queue-main em.is-warn{background:rgba(210,174,101,.16);color:#80652e}.market-research-queue-main em.is-positive{background:rgba(73,180,103,.12);color:#34764a}.market-research-queue-actions{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line2)}.market-research-queue-actions button{border:0;border-right:1px solid var(--line2);background:transparent;color:var(--muted);padding:8px 4px;font:inherit;font-size:9px;font-weight:800;cursor:pointer}.market-research-queue-actions button:last-child{border-right:0}
'''
p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v6.2 — Research Queue\n\n- Nova fila operacional de research dentro de As minhas posições, logo após o Decision Center.\n- Posições a rever entram automaticamente como Novo e podem ser marcadas Em revisão, Revisto ou Adiar 7 dias.\n- Estado fica apenas no dispositivo via localStorage e não altera Score Vestra, Action Map, Risk Gate ou carteira.\n- A fila prioriza pendentes e evita que uma carteira grande obrigue a recomeçar sempre a revisão do zero.\n- PWA cache: `vestra-cache-v59`.\n\n"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('vestra-cache-v58','vestra-cache-v59'); p.write_text(w)
