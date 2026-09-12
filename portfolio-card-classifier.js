/* Vestra Portfolio Card Classifier v1.2 — canonical card identity, tones, shortcuts and hints. */
(() => {
  'use strict';
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
  function classify(){
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
  function style(){
    if(document.getElementById('vestra-portfolio-card-classifier-style'))return;
    const link=document.createElement('link');
    link.id='vestra-portfolio-card-classifier-style';
    link.rel='stylesheet';
    link.href='portfolio-card-classifier.css?v=1.0';
    document.head.appendChild(link);
  }
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ux-jump]');if(b){e.preventDefault();e.stopPropagation();jumpPortfolio(b.dataset.uxJump);}});
  function start(){style();classify();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.VestraPortfolioCardClassifier=Object.freeze({refresh:classify,version:'1.2'});
})();
