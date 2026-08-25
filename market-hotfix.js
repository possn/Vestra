/* Vestra Market Hotfix loader v4.50 — safe direct deploy. */
(() => {
  'use strict';
  if (document.querySelector('script[data-vestra-market-enhancements]')) return;
  const s=document.createElement('script');
  s.src='./market-enhancements.js?v=4.50';
  s.defer=true;
  s.dataset.vestraMarketEnhancements='1';
  document.head.appendChild(s);
})();
