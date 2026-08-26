/* Vestra UI core v1.0 — DOM and Chart infrastructure extracted from app.js. */
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


  window.VestraUiCore = Object.freeze({ NOOP_EL, $, resolveChartHeight, prepareChartCanvas, buildNiceAxis, ensureChartCtx, ensureAllChartCanvasesReady, renderChartUnavailable, clearChartUnavailable });
})();
