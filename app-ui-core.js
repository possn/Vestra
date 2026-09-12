/* Vestra UI core v2.0 — DOM, Chart infrastructure and canonical launch lifecycle. */
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

/* ─── PREMIUM LAUNCH LIFECYCLE ──────────────────────────────
   app-ui-core.js is the effective owner of splash visibility and release.
   The base stylesheet owns the single entrance animation because it starts
   before deferred JavaScript executes. Premium styles must not replace the
   animation-name after parse: doing that restarts the entrance on iOS/PWA.
   The premium class still owns containment, timing and the single fade-out.
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
        pointer-events:auto!important;transition:none!important;
        background:#eef0ec!important;
        backdrop-filter:none!important;-webkit-backdrop-filter:none!important;
      }
      .vestra-splash.vestra-splash--premium.vestra-splash--leaving{
        display:flex!important;opacity:0!important;pointer-events:none!important;
        transition:opacity .68s cubic-bezier(.4,0,.2,1)!important;
      }
      .vestra-splash--premium .vestra-splash__mark{
        width:138px!important;height:138px!important;margin-bottom:0!important;
      }
      .vestra-splash--premium .vestra-splash__mark::after{
        inset:-18px!important;border-radius:42px!important;
        background:radial-gradient(circle,rgba(32,129,126,.18),rgba(196,171,114,.09) 42%,transparent 72%)!important;
        filter:blur(10px)!important;
      }
      .vestra-splash--premium .vestra-splash__mark img{
        width:122px!important;height:122px!important;border-radius:29px!important;
        box-shadow:0 22px 54px rgba(18,42,56,.22),0 4px 14px rgba(18,42,56,.10)!important;
      }
      .vestra-splash--premium .vestra-splash__brand{
        margin-top:24px!important;font-size:31px!important;font-weight:650!important;
        letter-spacing:-.035em!important;
      }
      .vestra-splash--premium .vestra-splash__tagline{
        margin-top:9px!important;font-size:15px!important;font-weight:600!important;
        letter-spacing:.02em!important;color:#55646b!important;
      }
      .vestra-splash--premium.vestra-splash--copy-ready .vestra-splash__brand,
      .vestra-splash--premium.vestra-splash--copy-ready .vestra-splash__tagline{
        opacity:1!important;transform:none!important;filter:none!important;
      }
    `;
    document.head.appendChild(style);
  }

  splash.classList.add('vestra-splash--premium');
  splash.classList.remove('vestra-splash--leaving');
  const startedAt = performance.now();
  // Entrance is already in flight from styles.css before this deferred module runs.
  // Do not swap animation names here; only settle copy, hold, then fade once.
  const copyReadyMs = 2000;
  const minimumVisibleMs = 4000;
  const failsafeMs = 6200;
  let releasing = false;
  let releaseTimer = null;

  const copyReadyTimer = setTimeout(() => {
    if (!releasing) splash.classList.add('vestra-splash--copy-ready');
  }, copyReadyMs);

  const releaseSplash = () => {
    if (releasing) return;
    const elapsed = performance.now() - startedAt;
    const remaining = Math.max(0, minimumVisibleMs - elapsed);
    if (remaining > 0) {
      if (!releaseTimer) releaseTimer = setTimeout(() => {
        releaseTimer = null;
        releaseSplash();
      }, remaining);
      return;
    }
    releasing = true;
    clearTimeout(copyReadyTimer);
    if (releaseTimer) clearTimeout(releaseTimer);
    splash.classList.add('vestra-splash--copy-ready');
    // The leaving class is the only effective fade owner. Its !important rules
    // beat any stale inline opacity/display writes that app.js may have queued.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      splash.classList.add('vestra-splash--leaving');
    }));
    setTimeout(() => {
      splash.style.display = 'none';
      splash.style.opacity = '0';
      splash.style.pointerEvents = 'none';
      splash.classList.remove('vestra-splash--premium', 'vestra-splash--copy-ready', 'vestra-splash--leaving');
    }, 720);
  };

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
    wrap.style.width = "100%";
    wrap.style.minWidth = "0";
    wrap.style.minHeight = `${height}px`;
    wrap.style.height = `${height}px`;
    wrap.style.maxHeight = `${height}px`;
    wrap.style.overflow = "hidden";
    wrap.dataset.chartHeightApplied = String(height);
  }
  canvas.style.setProperty("display", "block", "important");
  canvas.style.setProperty("width", "100%", "important");
  canvas.style.setProperty("min-width", "0", "important");
  canvas.style.setProperty("height", `${height}px`, "important");
  canvas.style.maxHeight = `${height}px`;
  canvas.dataset.chartHeightApplied = String(height);
  canvas.setAttribute("height", String(height));
  return canvas;
}

let chartStabilizeToken = 0;
function resizeVisibleCharts(root = document) {
  if (typeof Chart === "undefined") return 0;
  const scope = root && typeof root.querySelectorAll === "function" ? root : document;
  let resized = 0;
  scope.querySelectorAll(".chartWrap canvas").forEach(canvas => {
    const wrap = canvas.closest ? canvas.closest(".chartWrap") : null;
    if (!wrap) return;
    const wrapWidth = Math.round(wrap.getBoundingClientRect?.().width || wrap.clientWidth || 0);
    if (wrapWidth < 2) return;
    prepareChartCanvas(canvas);
    const chart = typeof Chart.getChart === "function" ? Chart.getChart(canvas) : null;
    if (chart && typeof chart.resize === "function") {
      chart.resize();
      resized += 1;
    }
  });
  return resized;
}

function scheduleChartStabilization(root = document) {
  const token = ++chartStabilizeToken;
  const run = () => {
    if (token !== chartStabilizeToken) return;
    try { resizeVisibleCharts(root); } catch (_) {}
  };
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(() => requestAnimationFrame(run));
  } else {
    setTimeout(run, 0);
  }
  setTimeout(run, 140);
  setTimeout(run, 420);
  return token;
}

function installChartReflowGuards() {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  const schedule = () => scheduleChartStabilization(document);
  window.addEventListener("resize", schedule, { passive: true });
  window.addEventListener("orientationchange", schedule, { passive: true });
  window.addEventListener("pageshow", schedule);
  window.addEventListener("vestra:app-ready", schedule);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") schedule();
  });
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
  scheduleChartStabilization(document);
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

try { installChartReflowGuards(); } catch (_) {}

  window.VestraUiCore = Object.freeze({
    NOOP_EL, $, resolveChartHeight, prepareChartCanvas, buildNiceAxis,
    ensureChartCtx, ensureAllChartCanvasesReady, renderChartUnavailable,
    clearChartUnavailable, resizeVisibleCharts, scheduleChartStabilization,
    installPremiumSplashWatchdog
  });
})();