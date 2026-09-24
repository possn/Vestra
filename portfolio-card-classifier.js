/* Vestra Portfolio Card Classifier v1.4 — canonical card identity, tones, badges and hints. */
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
  const BADGES={
    swap:{cls:'is-purple',text:'⇄ TROCAS INTELIGENTES'},
    overlap:{cls:'is-amber',text:'◉ DUPLICAÇÃO DE EXPOSIÇÃO'},
    reinforce:{cls:'is-green',text:'↗ CAPITAL NOVO'}
  };
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
      const badgeCfg=BADGES[cfg.kind];
      if(badgeCfg&&!card.querySelector(':scope > .ux-card-badge')){
        const badge=document.createElement('span');badge.className=`ux-card-badge ${badgeCfg.cls}`;badge.textContent=badgeCfg.text;card.insertAdjacentElement('afterbegin',badge);
      }
    });
    const swap=c.querySelector('[data-ux-kind="swap"]'); if(swap&&!swap.querySelector('.ux-section-hint')){
      const hint=document.createElement('div');hint.className='ux-section-hint';hint.textContent='Trocas inteligentes · compara alternativas sem assumir que vender é obrigatório.';swap.appendChild(hint);
    }
    const overlap=c.querySelector('[data-ux-kind="overlap"]'); if(overlap&&!overlap.querySelector('.ux-section-hint')){
      const hint=document.createElement('div');hint.className='ux-section-hint';hint.textContent='Sobreposição · mostra onde várias posições estão a comprar a mesma exposição.';overlap.appendChild(hint);
    }
  }
  function style(){
    if(document.getElementById('vestra-portfolio-card-classifier-style'))return;
    const link=document.createElement('link');
    link.id='vestra-portfolio-card-classifier-style';
    link.rel='stylesheet';
    link.href='portfolio-card-classifier.css?v=1.1';
    document.head.appendChild(link);
  }
  function start(){style();classify();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.VestraPortfolioCardClassifier=Object.freeze({refresh:classify,version:'1.4'});
})();
