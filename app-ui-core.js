/* Vestra UI core v1.3 — DOM, Chart infrastructure and launch watchdog. */
(() => {
  'use strict';
/* ─── DOM HELPER ──────────────────────────────────────────── */
const NOOP_EL = {
  _missing: true, addEventListener(){}, removeEventListener(){},
  classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
  setAttribute(){}, getAttribute(){ return null; },
  querySelector(){ return null; }, querySelectorAll(){ return []; },
  appendChild(){}, remove(){}, style: {}, value: "", checked: false,
  files: null, innerHTML: "", textContent: "", focus(){}, disabled: false
};

function $(id) { return document.getElementById(id) || NOOP_EL; }

/* ─── PREMIUM LAUNCH WATCHDOG ───────────────────────────────
   The splash must never depend on app.js reaching the end of its bootstrap.
   If any later module fails, this guard still releases the UI. It also owns
   the staged identity animation: mark first, then brand, then tagline.
────────────────────────────────────────────────────────────── */
function installPremiumSplashWatchdog() {
  const splash = document.getElementById('appLoadingOverlay');
  if (!splash || splash.dataset.premiumWatchdog === '1') return;
  splash.dataset.premiumWatchdog = '1';

  if (!document.getElementById('vestraPremiumSplashStyles')) {
    const style = document.createElement('style');
    style.id = 'vestraPremiumSplashStyles';
    style.textContent = `
      .vestra-splash.vestra-splash--premium{
        display:flex!important;opacity:1!important;
        background:
          radial-gradient(circle at 50% 42%,rgba(255,255,255,.96) 0,rgba(244,242,235,.98) 30%,rgba(224,227,222,.99) 66%,#d4d8d3 100%)!important;
      }
      .vestra-splash--premium .vestra-splash__mark{
        width:138px!important;height:138px!important;margin-bottom:0!important;
        animation:vestraPremiumMarkIn .82s cubic-bezier(.16,1,.3,1) both!important;
      }
      .vestra-splash--premium .vestra-splash__mark::after{
        inset:-18px!important;border-radius:42px!important;
        background:radial-gradient(circle,rgba(32,129,126,.18),rgba(196,171,114,.09) 42%,transparent 72%)!important;
        filter:blur(10px)!important;animation:vestraPremiumGlow 2.1s ease-in-out infinite alternate!important;
      }
      .vestra-splash--premium .vestra-splash__mark img{
        width:122px!important;height:122px!important;border-radius:29px!important;
        box-shadow:0 22px 54px rgba(18,42,56,.22),0 4px 14px rgba(18,42,56,.10)!important;
      }
      .vestra-splash--premium .vestra-splash__brand{
        margin-top:24px!important;font-size:31px!important;font-weight:650!important;
        letter-spacing:-.035em!important;opacity:0;
        animation:vestraPremiumBrandIn .82s .72s cubic-bezier(.16,1,.3,1) both!important;
      }
      .vestra-splash--premium .vestra-splash__tagline{
        margin-top:9px!important;font-size:15px!important;font-weight:600!important;
        letter-spacing:.02em!important;color:#55646b!important;opacity:0;
        animation:vestraPremiumTaglineIn .72s 1.18s cubic-bezier(.16,1,.3,1) both!important;
      }
      @keyframes vestraPremiumMarkIn{
        0%{opacity:0;transform:scale(.78) translateY(8px);filter:blur(3px)}
        60%{opacity:1;filter:blur(0)}
        100%{opacity:1;transform:scale(1) translateY(0)}
      }
      @keyframes vestraPremiumBrandIn{
        from{opacity:0;transform:translateY(9px);letter-spacing:.015em}
        to{opacity:1;transform:translateY(0);letter-spacing:-.035em}
      }
      @keyframes vestraPremiumTaglineIn{
        from{opacity:0;transform:translateY(7px)}
        to{opacity:1;transform:translateY(0)}
      }
      @keyframes vestraPremiumGlow{
        from{opacity:.36;transform:scale(.94)}
        to{opacity:.86;transform:scale(1.06)}
      }
      @media(prefers-reduced-motion:reduce){
        .vestra-splash--premium .vestra-splash__mark,
        .vestra-splash--premium .vestra-splash__brand,
        .vestra-splash--premium .vestra-splash__tagline,
        .vestra-splash--premium .vestra-splash__mark::after{animation-duration:.01ms!important;animation-delay:0ms!important}
      }
    `;
    document.head.appendChild(style);
  }

  splash.classList.add('vestra-splash--premium');
  const startedAt = performance.now();
  // The copy is fully visible around 1.9s. Keep the complete identity on screen
  // for roughly another 1.6s so it can actually be read before the app opens.
  const minimumVisibleMs = 3500;
  const failsafeMs = 5400;
  let releasing = false;
  let releaseTimer = null;

  const keepSplashVisible = () => {
    if (releasing) return;
    splash.style.transition = 'none';
    splash.style.display = 'flex';
    splash.style.opacity = '1';
    splash.style.pointerEvents = 'auto';
  };

  const releaseSplash = () => {
    if (releasing) return;
    const elapsed = performance.now() - startedAt;
    const remaining = Math.max(0, minimumVisibleMs - elapsed);
    if (remaining > 0) {
      keepSplashVisible();
      if (!releaseTimer) releaseTimer = setTimeout(() => {
        releaseTimer = null;
        releaseSplash();
      }, remaining);
      return;
    }
    releasing = true;
    observer.disconnect();
    splash.style.display = 'flex';
    splash.style.opacity = '1';
    splash.style.pointerEvents = 'auto';
    splash.style.transition = 'opacity .52s cubic-bezier(.4,0,.2,1)';
    requestAnimationFrame(() => requestAnimationFrame(() => { splash.style.opacity = '0'; }));
    setTimeout(() => {
      splash.style.display = 'none';
      splash.style.pointerEvents = 'none';
      splash.classList.remove('vestra-splash--premium');
    }, 570);
  };

  const observer = new MutationObserver(() => {
    if (releasing) return;
    const appTriedToHide = splash.style.opacity === '0' || splash.style.display === 'none';
    if (!appTriedToHide) return;
    const elapsed = performance.now() - startedAt;
    if (elapsed < minimumVisibleMs) {
      // app.js still contains the legacy early fade. Neutralise it until the
      // mark → brand → tagline sequence has been visible long enough to read.
      keepSplashVisible();
      if (!releaseTimer) releaseTimer = setTimeout(() => {
        releaseTimer = null;
        releaseSplash();
      }, Math.max(0, minimumVisibleMs - elapsed));
      return;
    }
    releaseSplash();
  });
  observer.observe(splash, { attributes: true, attributeFilter: ['style'] });

  window.addEventListener('vestra:app-ready', releaseSplash, { once: true });
  setTimeout(() => releaseSplash(), failsafeMs);
}

try { installPremiumSplashWatchdog(); } catch (_) {}

function resolveChartHeight(canvas, fallbackHeight = 220) {
  const desired = Number.isFinite(Number(fallbackHeight)) && Number(fallbackHeight) > 80
    ? Number(fallbackHeight)
    : NaN;
  const explicit = parseInt(canvas?.dataset?.chartHeight || canvas?.getAttribute?.("height") || "", 10);
  if (Number.isFinite(desired) && desired > 80) return Math.round(desired);
  if (Number.isFinite(explicit) && explicit > 80) return explicit;
  return 220;
}

function prepareChartCanvas(canvas, fallbackHeight = 220) {
  if (!canvas || canvas._missing || typeof canvas.getContext !== "function") return null;
  const height = resolveChartHeight(canvas, fallbackHeight);
  const wrap = canvas.closest ? canvas.closest(".chartWrap") : null;
  if (wrap) {
    wrap.style.position = "relative";
    wrap.style.minHeight = `${height}px`;
    wrap.style.height = `${height}px`;
    wrap.style.maxHeight = `${height}px`;
    wrap.style.overflow = "hidden";
    wrap.dataset.chartHeightApplied = String(height);
  }
  canvas.style.setProperty("display", "block", "important");
  canvas.style.setProperty("width", "100%", "important");
  canvas.style.setProperty("height", `${height}px`, "important");
  canvas.style.maxHeight = `${height}px`;
  canvas.dataset.chartHeightApplied = String(height);
  canvas.setAttribute("height", String(height));
  return canvas;
}
function buildNiceAxis(maxValue, targetSteps = 4) {
  const v = Math.max(1, Number(maxValue) || 0);
  const rawStep = v / Math.max(2, targetSteps);
  const exp = Math.floor(Math.log10(rawStep));
  const base = Math.pow(10, exp);
  const frac = rawStep / base;
  const niceFrac = frac <= 1 ? 1 : frac <= 2 ? 2 : frac <= 2.5 ? 2.5 : frac <= 5 ? 5 : 10;
  const step = niceFrac * base;
  const steps = Math.max(2, Math.ceil(v / step));
  return { max: step * steps, step, steps };
}

function ensureChartCtx(id, fallbackHeight = 220) {
  if (typeof Chart === "undefined") {
    renderChartUnavailable(id, "Biblioteca de gráficos não carregada");
    return null;
  }
  const canvas = prepareChartCanvas(document.getElementById(id), fallbackHeight);
  if (!canvas) return null;
  return canvas.getContext("2d");
}

function ensureAllChartCanvasesReady() {
  document.querySelectorAll(".chartWrap canvas").forEach(c => prepareChartCanvas(c));
}

function renderChartUnavailable(canvasId, message = "Gráfico indisponível") {
  const canvas = document.getElementById(canvasId);
  const wrap = canvas && canvas.closest ? canvas.closest(".chartWrap") : null;
  if (!wrap) return;
  let note = wrap.querySelector(".chartFallback");
  if (!note) {
    note = document.createElement("div");
    note.className = "chartFallback";
    note.style.cssText = "display:flex;align-items:center;justify-content:center;height:100%;min-height:140px;font-size:12px;color:var(--muted);text-align:center;padding:12px";
    wrap.appendChild(note);
  }
  note.textContent = message;
}

function clearChartUnavailable(canvasId) {
  const canvas = document.getElementById(canvasId);
  const wrap = canvas && canvas.closest ? canvas.closest(".chartWrap") : null;
  if (!wrap) return;
  const note = wrap.querySelector(".chartFallback");
  if (note) note.remove();
}

  window.VestraUiCore = Object.freeze({ NOOP_EL, $, resolveChartHeight, prepareChartCanvas, buildNiceAxis, ensureChartCtx, ensureAllChartCanvasesReady, renderChartUnavailable, clearChartUnavailable, installPremiumSplashWatchdog });
})();
