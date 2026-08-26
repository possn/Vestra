/* Vestra Market compatibility loader v4.95 — sequential, deterministic. */
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

  // app-utils.js is part of the ordered base bundle in index.html. Keep this
  // compatibility loader focused on market-only overlays to avoid duplicate work.
  load('./market-data-loader.js?v=2.0','vestraMarketDataLoader');
  load('./market-enhancements.js?v=4.50','vestraMarketEnhancements');
  load('./portfolio-navigation-fix.js?v=1.0','vestraPortfolioNavigationFix');
  load('./vestra-ux-v452.js?v=4.52','vestraUxV452');
  load('./market-opportunities.js?v=1.0','vestraMarketOpportunities');
  load('./vestra-portfolio-focus.js?v=1.0','vestraPortfolioFocus');
  load('./vestra-ux-v454.js?v=4.54','vestraUxV454');
  load('./vestra-portfolio-hierarchy.js?v=1.0','vestraPortfolioHierarchy');
  load('./vestra-ux-v456.js?v=4.56','vestraUxV456');
  load('./market-opportunity-lenses.js?v=1.0','vestraOpportunityLenses');
  load('./vestra-ai-brief-v459.js?v=4.59','vestraAiBriefV459');
  load('./vestra-portfolio-ui.js?v=1.0','vestraPortfolioUi');
  load('./vestra-portfolio-nav-fix-v464.js?v=4.64','vestraPortfolioNavFixV464');
  load('./market-close-controller.js?v=1.0','vestraMarketCloseController');
  load('./vestra-portfolio-dossier-routing-v482.js?v=4.82','vestraPortfolioDossierRoutingV482');

  load('./politicians.js?v=2.1','vestraPoliticiansCanonical');
})();
