/* Vestra UX v4.52 — compact portfolio, clearer opportunities, politician radar. */
(() => {
  'use strict';
  const VERSION='4.52';
  const t=v=>String(v??'').trim();
  const PORTFOLIO_KINDS=[
    {q:'Fila de revisão',kind:'research',icon:'◌',tone:'violet'},
    {q:'Prioridades da carteira',kind:'priority',icon:'✦',tone:'teal'},
    {q:'Mapa da carteira',kind:'map',icon:'◎',tone:'blue'},
    {q:'Candidatos a reforço',kind:'reinforce',icon:'↗',tone:'green'},
    {q:'Posições a rever',kind:'review',icon:'!',tone:'coral'},
    {q:'Concentração e overlap',kind:'overlap',icon:'◉',tone:'amber'},
    {q:'Alternativas no mesmo setor',kind:'swap',icon:'⇄',tone:'purple'},
    {q:'Se substituíres pelo mesmo valor',kind:'scenario',icon:'↔',tone:'purple'},
    {q:'Aderência aos objetivos',kind:'target',icon:'✓',tone:'green'},
    {q:'A carteira está a melhorar?',kind:'history',icon:'↗',tone:'blue'},
    {q:'Diversificação da carteira',kind:'risk',icon:'◇',tone:'coral'},
    {q:'Como reage a carteira?',kind:'stress',icon:'≈',tone:'amber'}
  ];
  function cardTitle(card){return t(card.querySelector('.market-perspective-head h4')?.textContent||card.querySelector(':scope > h4')?.textContent||card.querySelector('h4')?.textContent);}
  function classifyPortfolioCards(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;
    c.classList.add('ux-portfolio');
    c.querySelectorAll('.market-detail-card[data-collapsible="1"]').forEach(card=>{
      const title=cardTitle(card);const cfg=PORTFOLIO_KINDS.find(x=>title.includes(x.q)); if(!cfg)return;
      card.dataset.uxKind=cfg.kind;card.dataset.uxTone=cfg.tone;
      let icon=card.querySelector(':scope > .ux-card-icon');
      if(!icon){icon=document.createElement('span');icon.className='ux-card-icon';icon.textContent=cfg.icon;card.appendChild(icon);}
    });
    const toolbar=c.querySelector('.market-collapse-toolbar');
    if(toolbar&&!c.querySelector('.ux-portfolio-shortcuts')){
      const bar=document.createElement('div');bar.className='ux-portfolio-shortcuts';
      bar.innerHTML='<button data-ux-jump="priority">✦ Prioridades</button><button data-ux-jump="swap">⇄ Trocas</button><button data-ux-jump="overlap">◉ Overlap</button><button data-ux-jump="risk">◇ Risco</button>';
      toolbar.insertAdjacentElement('afterend',bar);
    }
    const swap=c.querySelector('[data-ux-kind="swap"]'); if(swap&&!swap.querySelector('.ux-section-hint')){
      const hint=document.createElement('div');hint.className='ux-section-hint';hint.textContent='Trocas inteligentes · compara alternativas sem assumir que vender é obrigatório.';swap.appendChild(hint);
    }
    const overlap=c.querySelector('[data-ux-kind="overlap"]'); if(overlap&&!overlap.querySelector('.ux-section-hint')){
      const hint=document.createElement('div');hint.className='ux-section-hint';hint.textContent='Sobreposição · mostra onde várias posições estão a comprar a mesma exposição.';overlap.appendChild(hint);
    }
  }
  function jumpPortfolio(kind){
    const card=document.querySelector(`#marketSheetContent [data-ux-kind="${kind}"]`);if(!card)return;
    if(card.classList.contains('is-collapsed'))card.querySelector('[data-collapse-toggle]')?.click();
    setTimeout(()=>card.scrollIntoView({behavior:'smooth',block:'start'}),30);
  }

  function addStyle(){
    if(document.getElementById('vestra-ux-v452-style'))return;
    const s=document.createElement('style');s.id='vestra-ux-v452-style';s.textContent=`
      .ux-portfolio .market-collapse-toolbar{background:linear-gradient(135deg,rgba(23,123,120,.09),rgba(89,113,190,.06));border:0;padding:9px 10px;position:sticky;top:0;z-index:5;backdrop-filter:blur(10px)}
      .ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed{min-height:74px;padding:13px 52px 12px 50px!important;border-left:4px solid rgba(23,123,120,.25);box-shadow:0 3px 12px rgba(19,41,52,.035)}
      .ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed .market-perspective-head{min-height:44px;align-items:center}.ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed .market-perspective-head small{font-size:9px;letter-spacing:.13em}.ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed h4{font-size:16px;line-height:1.15}
      .ux-card-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);width:27px;height:27px;border-radius:9px;display:grid;place-items:center;background:rgba(23,123,120,.08);font-weight:900;color:#177b78}.market-detail-card:not(.is-collapsed)>.ux-card-icon{display:none}
      [data-ux-tone="violet"].is-collapsed{border-left-color:#8c78c5!important}[data-ux-tone="violet"] .ux-card-icon{color:#705bb0;background:#f1edfb}
      [data-ux-tone="teal"].is-collapsed{border-left-color:#1e9a95!important}[data-ux-tone="blue"].is-collapsed{border-left-color:#5b86c4!important}[data-ux-tone="green"].is-collapsed{border-left-color:#49a878!important}[data-ux-tone="coral"].is-collapsed{border-left-color:#da806f!important}[data-ux-tone="amber"].is-collapsed{border-left-color:#d6a34a!important}[data-ux-tone="purple"].is-collapsed{border-left-color:#9a78c9!important}
      .ux-portfolio-shortcuts{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:0 0 12px}.ux-portfolio-shortcuts button{border:0;border-radius:13px;padding:10px 5px;background:linear-gradient(145deg,var(--card),var(--soft));color:var(--text);font-size:10px;font-weight:800;box-shadow:0 3px 12px rgba(19,41,52,.05)}
      .ux-section-hint{font-size:11px;color:var(--text2);padding:8px 0 2px}.is-collapsed>.ux-section-hint{display:none!important}
      [data-ux-kind="swap"]:not(.is-collapsed),[data-ux-kind="scenario"]:not(.is-collapsed){background:linear-gradient(145deg,var(--card),rgba(143,112,199,.06))}[data-ux-kind="overlap"]:not(.is-collapsed){background:linear-gradient(145deg,var(--card),rgba(216,163,74,.07))}
      .ux-opp-row{align-items:center!important;padding:13px!important;border:1px solid var(--line);border-radius:18px!important;background:linear-gradient(135deg,var(--card),rgba(23,123,120,.045));margin-bottom:9px}.ux-opp-main{min-width:0;flex:1}.ux-opp-why{font-size:10.5px;color:#177b78;font-weight:700;margin-top:5px}.ux-opp-chips{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.ux-opp-chip{font-size:9px;padding:4px 7px;border-radius:999px;background:var(--soft);color:var(--text2)}.ux-opp-chip b{color:var(--text);font-weight:800}.ux-opp-chip.timing{background:rgba(23,123,120,.09)}.ux-opp-chip.upside{background:rgba(73,168,120,.11)}.ux-opp-score{width:58px;height:62px;border-radius:17px;background:linear-gradient(145deg,#dff3ef,#caebe6);display:grid;place-items:center;align-content:center;color:#126d69;flex:0 0 auto}.ux-opp-score small{font-size:8px;font-weight:900;letter-spacing:.12em}.ux-opp-score strong{font-size:22px;line-height:1}
      @media(max-width:420px){.ux-portfolio-shortcuts{grid-template-columns:repeat(2,1fr)}.ux-portfolio .market-detail-card[data-collapsible="1"].is-collapsed{min-height:68px}.ux-opp-chip{font-size:8.5px}.ux-opp-score{width:52px;height:57px}.ux-opp-score strong{font-size:20px}}
    `;document.head.appendChild(s);
  }

  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ux-jump]');if(b){e.preventDefault();e.stopPropagation();jumpPortfolio(b.dataset.uxJump);}});

  function apply(){classifyPortfolioCards();}
  function start(){addStyle();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
