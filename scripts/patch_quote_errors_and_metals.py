#!/usr/bin/env python3
"""Guarded integration patch for quote-error UX + Metals Market mode."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 marker, found {count}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')


# 1) Load metals module immediately after the canonical Market runtime.
index = ROOT / 'index.html'
old = '<script defer="" src="market.js?v=20260821v5"></script>\n<script defer="" src="market-data-loader.js?v=2.0"></script>'
new = '<script defer="" src="market.js?v=20260821v5"></script>\n<script defer="" src="market-metals.js?v=1.0"></script>\n<script defer="" src="market-data-loader.js?v=2.0"></script>'
replace_once(index, old, new, 'index metals script')

# 2) Give renderPrimary a first-class metals branch. The Metals module remains lazy.
market = ROOT / 'market.js'
old = """  function renderPrimary(){
    const root=$m('marketPrimary'); if(!root || !M.loaded) return;
    root.innerHTML = M.mode==='funds'?renderFunds():M.mode==='smart'?renderSmart():M.mode==='watch'?renderWatch():M.mode==='lows'?renderLows():renderDiscover();
  }
"""
new = """  function renderPrimary(){
    const root=$m('marketPrimary'); if(!root || !M.loaded) return;
    if(M.mode==='metals' && window.VestraMetals?.renderInto){
      window.VestraMetals.renderInto(root);
      return;
    }
    root.dataset.metalsActive='0';
    root.innerHTML = M.mode==='funds'?renderFunds():M.mode==='smart'?renderSmart():M.mode==='watch'?renderWatch():M.mode==='lows'?renderLows():renderDiscover();
  }
"""
replace_once(market, old, new, 'market renderPrimary')

# 3) Restore one canonical, visible error-details action.
app = ROOT / 'app.js'
text = app.read_text(encoding='utf-8')

helper_marker = "let quoteErrorsInlineOpen = false;\n\nfunction renderQuoteErrorsInline(forceOpen = quoteErrorsInlineOpen) {"
helper = """let quoteErrorsInlineOpen = false;

function openQuoteErrorDetails(reportOverride = null) {
  const report = reportOverride || ((((state || {}).settings || {}).lastQuoteRefresh) || { updated:0, failed:0, errors:[] });
  const errors = Array.isArray(report.errors) ? report.errors : [];
  const failed = Number(report.failed || errors.length || 0);
  showQuoteErrors(Number(report.updated || 0), failed, errors, Number(report.updated || 0), failed);
  // Explicit user action must always open a visible surface in the current view.
  // The inline list belongs to Carteira and is hidden while the user is in Mais.
  openModal('modalQuoteErrors');
}

function renderQuoteErrorsInline(forceOpen = quoteErrorsInlineOpen) {"""
if text.count(helper_marker) != 1:
    raise SystemExit(f'quote details helper marker: expected 1, found {text.count(helper_marker)}')
text = text.replace(helper_marker, helper, 1)

old_listener = """  const btnQuoteErrors = document.getElementById('btnQuoteErrors');
  if (btnQuoteErrors) btnQuoteErrors.addEventListener('click', () => {
    const report = (((state || {}).settings || {}).lastQuoteRefresh) || { updated:0, failed:0, errors:[] };
    showQuoteErrors(report.updated || 0, report.failed || 0, report.errors || [], report.updated || 0, report.failed || 0);
    quoteErrorsInlineOpen = true;
    renderQuoteErrorsInline(true);
    const panel = document.getElementById('quoteErrorsInline');
    if (panel && panel.scrollIntoView) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
"""
new_listener = """  const btnQuoteErrors = document.getElementById('btnQuoteErrors');
  if (btnQuoteErrors) btnQuoteErrors.addEventListener('click', () => openQuoteErrorDetails());
"""
if text.count(old_listener) != 1:
    raise SystemExit(f'quote error listener: expected 1, found {text.count(old_listener)}')
text = text.replace(old_listener, new_listener, 1)

old_callback = """        () => {
          showQuoteErrors(updated, failed, errors, updated, failed);
          quoteErrorsInlineOpen = true;
          renderQuoteErrorsInline(true);
          const panel = document.getElementById('quoteErrorsInline');
          if (panel && panel.scrollIntoView) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 6500
"""
new_callback = """        () => openQuoteErrorDetails({ updated, failed, errors }), 6500
"""
if text.count(old_callback) != 1:
    raise SystemExit(f'partial-failure toast callback: expected 1, found {text.count(old_callback)}')
text = text.replace(old_callback, new_callback, 1)

old_callback2 = """        () => {
          showQuoteErrors(0, failed, errors, 0, failed);
          quoteErrorsInlineOpen = true;
          renderQuoteErrorsInline(true);
          const panel = document.getElementById('quoteErrorsInline');
          if (panel && panel.scrollIntoView) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 6500
"""
new_callback2 = """        () => openQuoteErrorDetails({ updated:0, failed, errors }), 6500
"""
if text.count(old_callback2) != 1:
    raise SystemExit(f'full-failure toast callback: expected 1, found {text.count(old_callback2)}')
text = text.replace(old_callback2, new_callback2, 1)

# 4) Put a persistent error-details control directly in the Settings quote card.
status_tail = """  } else if (report && report.updated > 0) {
    const secs = report.durationMs ? ` · ${Math.max(1, Math.round(report.durationMs/1000))} s` : "";
    const skipped = report.skipped ? ` · ${report.skipped} ignoradas` : "";
    const mode = report.workerMode === "single" ? " · compatibilidade" : "";
    meta.textContent = `${report.updated} atualizadas${skipped}${mode}${secs} · automático`;
  } else meta.textContent = auto ? "Automático · atualiza se >30 min" : "Automático desativado";
}
"""
status_new = """  } else if (report && report.updated > 0) {
    const secs = report.durationMs ? ` · ${Math.max(1, Math.round(report.durationMs/1000))} s` : "";
    const skipped = report.skipped ? ` · ${report.skipped} ignoradas` : "";
    const mode = report.workerMode === "single" ? " · compatibilidade" : "";
    meta.textContent = `${report.updated} atualizadas${skipped}${mode}${secs} · automático`;
  } else meta.textContent = auto ? "Automático · atualiza se >30 min" : "Automático desativado";

  const copy = card.querySelector('.quote-sync-card__copy');
  let errorBtn = copy && copy.querySelector('[data-quote-errors-open]');
  const errorCount = report && Array.isArray(report.errors) ? report.errors.length : 0;
  if (copy && errorCount > 0) {
    if (!errorBtn) {
      errorBtn = document.createElement('button');
      errorBtn.type = 'button';
      errorBtn.dataset.quoteErrorsOpen = '1';
      errorBtn.style.cssText = 'border:0;background:transparent;color:var(--teal,#178c88);padding:4px 0 0;text-align:left;font:inherit;font-size:12px;font-weight:850;cursor:pointer;align-self:flex-start';
      errorBtn.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); openQuoteErrorDetails(); });
      copy.appendChild(errorBtn);
    }
    errorBtn.style.display = '';
    errorBtn.textContent = `Ver ${errorCount} erro${errorCount === 1 ? '' : 's'} →`;
  } else if (errorBtn) errorBtn.style.display = 'none';
}
"""
if text.count(status_tail) != 1:
    raise SystemExit(f'renderQuoteSyncStatus tail: expected 1, found {text.count(status_tail)}')
text = text.replace(status_tail, status_new, 1)
app.write_text(text, encoding='utf-8')

print('Integrated quote error modal + Metals mode')
