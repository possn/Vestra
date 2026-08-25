/* Vestra Market Hotfix loader v4.73 — safe direct deploy. */
(() => {
  'use strict';
  const load=(src,key)=>{
    if(document.querySelector(`script[data-${key}]`)) return;
    const s=document.createElement('script');
    s.src=src;
    s.defer=true;
    s.dataset[key]='1';
    document.head.appendChild(s);
  };
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
  load('./vestra-politicians-simple-v472.js?v=4.72','vestraPoliticiansSimpleV472');
  load('./vestra-pol-portfolio-v473.js?v=4.73','vestraPolPortfolioV473');
})();