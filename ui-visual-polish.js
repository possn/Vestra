/* Vestra UI Visual Polish v1.0 — lighter hierarchy without changing app semantics. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraUiVisualPolishStyle';

  function ensureStyles() {
    if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      body{-webkit-tap-highlight-color:transparent}
      .card__title{letter-spacing:-.012em;line-height:1.2}
      .card__muted{line-height:1.45}
      .card__head{gap:12px}

      #viewDashboard .card:not(.hero):not(#dashboardWeeklyEventsCard),
      #viewCashflow .card,
      #viewSettings .card{
        box-shadow:none!important;
        border-color:rgba(31,56,66,.075)!important;
      }
      #viewDashboard .card .card,
      #viewCashflow .card .card,
      #viewSettings .more-group__body>.card{
        background:var(--card2);
        border-color:rgba(31,56,66,.055)!important;
        box-shadow:none!important;
      }

      .btn,.seg__btn,.navbtn,.market-tab,.market-mode,.market-chip,.market-watch,
      .more-shortcut,.snapshot-history-summary__btn{
        touch-action:manipulation;
        transition:transform .16s ease,background-color .16s ease,border-color .16s ease,color .16s ease,box-shadow .16s ease;
      }
      .btn:active,.seg__btn:active,.market-tab:active,.market-mode:active,.market-chip:active,
      .market-watch:active,.more-shortcut:active,.snapshot-history-summary__btn:active{
        transform:scale(.975);
      }
      button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{
        outline:3px solid rgba(23,123,120,.22);
        outline-offset:2px;
      }

      .seg__btn--active,.seg__btn.is-active{
        box-shadow:none!important;
      }

      #marketSheetContent .market-detail-card{
        box-shadow:none!important;
        border-color:rgba(31,56,66,.075)!important;
      }
      #marketSheetContent .market-metric{
        box-shadow:none!important;
        border-color:transparent!important;
        background:var(--card2)!important;
      }
      #marketSheetContent .market-tabs{
        gap:7px;
        padding-bottom:3px;
        scrollbar-width:none;
      }
      #marketSheetContent .market-tabs::-webkit-scrollbar{display:none}
      #marketSheetContent .market-tab{
        border-radius:999px;
        padding:9px 12px;
      }
      #marketSheetContent .market-tab.is-active{
        box-shadow:none;
      }
      #marketSheetContent .market-read,
      #marketSheetContent .market-case{
        box-shadow:0 10px 28px rgba(18,38,51,.07);
      }
      .market-row{box-shadow:none!important}

      .more-group{box-shadow:none!important}
      .more-group summary{touch-action:manipulation}

      @media(max-width:720px){
        .view{scroll-behavior:smooth}
        #viewDashboard .card:not(.hero),#viewCashflow .card,#viewSettings .card{border-radius:18px}
        #marketSheetContent .market-detail-card{border-radius:17px}
        #marketSheetContent .market-metric{border-radius:14px;padding:10px}
      }
      @media(prefers-reduced-motion:reduce){
        .btn,.seg__btn,.navbtn,.market-tab,.market-mode,.market-chip,.market-watch,
        .more-shortcut,.snapshot-history-summary__btn{transition:none!important}
        .view{scroll-behavior:auto!important}
      }
    `;
    document.head.appendChild(style);
  }

  function refresh() {
    ensureStyles();
  }

  function boot() {
    refresh();
    window.addEventListener('vestra:app-ready', refresh);
    window.addEventListener('vestra:market-ready', refresh);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once:true });
  else boot();

  window.VestraUiVisualPolish = Object.freeze({ refresh, version:'1.0' });
})();
