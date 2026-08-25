/* Vestra Market Hotfix loader v4.60 — safe direct deploy. */
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
})();
