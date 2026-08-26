/* Vestra Market Hotfix loader v4.82 — safe direct deploy. */
(() => {
  'use strict';
  // v1.1: "s.defer=true" não tem qualquer efeito em <script> criados
  // dinamicamente — essa propriedade só é respeitada em scripts estáticos
  // do HTML. Sem isto, os ficheiros carregavam por ordem de rede (o que
  // chegasse primeiro), não pela ordem da lista — e como o v480 depende de
  // classes que o v479 cria (e assim por diante ao longo da série), a
  // funcionalidade podia falhar de forma imprevisível consoante a rede.
  // Fila sequencial: só pede o próximo ficheiro depois do anterior carregar.
  const queue = [];
  let draining = false;
  function drain() {
    if (draining) return;
    draining = true;
    const next = () => {
      const job = queue.shift();
      if (!job) { draining = false; return; }
      const [src, key] = job;
      if (document.querySelector(`script[data-${key}]`)) { next(); return; }
      const s = document.createElement('script');
      s.src = src;
      s.dataset[key] = '1';
      s.onload = next;
      s.onerror = next; // não bloquear a fila toda por um ficheiro a falhar
      document.head.appendChild(s);
    };
    next();
  }
  const load = (src, key) => { queue.push([src, key]); drain(); };
  load('./market-enhancements.js?v=4.50','vestraMarketEnhancements');
  load('./portfolio-navigation-fix.js?v=1.0','vestraPortfolioNavigationFix');
  load('./vestra-ux-v452.js?v=4.52','vestraUxV452');
  load('./vestra-ux-v453.js?v=4.53','vestraUxV453');
  load('./vestra-ux-v454.js?v=4.54','vestraUxV454');
  load('./vestra-ux-v455.js?v=4.55','vestraUxV455');
  load('./vestra-ux-v456.js?v=4.56','vestraUxV456');
  load('./vestra-ux-v457.js?v=4.57','vestraUxV457');
  load('./vestra-ux-v458.js?v=4.58','vestraUxV458');
  load('./vestra-ai-brief-v459.js?v=4.59','vestraAiBriefV459');
  load('./vestra-portfolio-overview-v460.js?v=4.60','vestraPortfolioOverviewV460');
  load('./vestra-portfolio-overview-v461.js?v=4.61','vestraPortfolioOverviewV461');
  load('./vestra-portfolio-overview-v462.js?v=4.62','vestraPortfolioOverviewV462');
  load('./vestra-politicians-dedupe-v463.js?v=4.63','vestraPoliticiansDedupeV463');
  load('./vestra-portfolio-nav-fix-v464.js?v=4.64','vestraPortfolioNavFixV464');
  load('./vestra-politician-ledger-v466.js?v=4.66','vestraPoliticianLedgerV466');
  load('./vestra-portfolio-close-v469.js?v=4.69','vestraPortfolioCloseV469');
  load('./vestra-portfolio-close-dedupe-v470.js?v=4.70','vestraPortfolioCloseDedupeV470');
  load('./vestra-market-close-cleanup-v471.js?v=4.71','vestraMarketCloseCleanupV471');
  load('./vestra-politicians-clean-v475.js?v=4.75','vestraPoliticiansCleanV475');
  load('./vestra-politicians-portfolio-v476.js?v=4.76','vestraPoliticiansPortfolioV476');
  load('./vestra-politicians-flow-v477.js?v=4.77','vestraPoliticiansFlowV477');
  load('./vestra-politicians-picker-v478.js?v=4.78','vestraPoliticiansPickerV478');
  load('./vestra-portfolio-tabs-v479.js?v=4.79','vestraPortfolioTabsV479');
  load('./vestra-portfolio-tabs-v480.js?v=4.80','vestraPortfolioTabsV480');
  load('./vestra-politicians-search-v481.js?v=4.82','vestraPoliticiansSearchV481');
  load('./vestra-portfolio-dossier-routing-v482.js?v=4.82','vestraPortfolioDossierRoutingV482');
})();