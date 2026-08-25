/* Vestra Market Hotfix loader v4.52 — safe direct deploy. */
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
})();
