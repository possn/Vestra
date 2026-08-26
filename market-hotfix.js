/* Vestra Market compatibility loader v4.86 — sequential, deterministic. */
(() => {
  'use strict';

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
      const script = document.createElement('script');
      script.src = src;
      script.dataset[key] = '1';
      script.onload = next;
      script.onerror = next;
      document.head.appendChild(script);
    };
    next();
  }

  function load(src, key) {
    queue.push([src, key]);
    drain();
  }

  load('./market-data-loader.js?v=1.0','vestraMarketDataLoader');
  load('./market-enhancements.js?v=4.50','vestraMarketEnhancements');
  load('./portfolio-navigation-fix.js?v=1.0','vestraPortfolioNavigationFix');
  load('./vestra-ux-v452.js?v=4.52','vestraUxV452');
  load('./vestra-ux-v453.js?v=4.53','vestraUxV453');
  load('./vestra-ux-v454.js?v=4.54','vestraUxV454');
  load('./vestra-ux-v455.js?v=4.55','vestraUxV455');
  load('./vestra-ux-v456.js?v=4.56','vestraUxV456');
  load('./vestra-ux-v457.js?v=4.57','vestraUxV457');
  load('./market-opportunity-lenses.js?v=1.0','vestraOpportunityLenses');
  load('./vestra-ai-brief-v459.js?v=4.59','vestraAiBriefV459');

  // Canonical portfolio UI: replaces v460 + v461 + v479 + v480 and therefore
  // removes four overlapping MutationObservers / DOM reconstruction layers.
  load('./vestra-portfolio-ui.js?v=1.0','vestraPortfolioUi');

  load('./vestra-portfolio-nav-fix-v464.js?v=4.64','vestraPortfolioNavFixV464');
  load('./vestra-portfolio-close-v469.js?v=4.69','vestraPortfolioCloseV469');
  load('./vestra-portfolio-close-dedupe-v470.js?v=4.70','vestraPortfolioCloseDedupeV470');
  load('./vestra-market-close-cleanup-v471.js?v=4.71','vestraMarketCloseCleanupV471');
  load('./vestra-portfolio-dossier-routing-v482.js?v=4.82','vestraPortfolioDossierRoutingV482');

  const style = document.createElement('style');
  style.id = 'vestra-politicians-canonical-v486';
  style.textContent = '.politicians-section .ux454-flow{display:none!important}';
  document.head.appendChild(style);
  load('./politicians.js?v=1.3','vestraPoliticiansCanonical');
})();
