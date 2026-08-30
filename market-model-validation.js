/* Vestra Market Model Validation — read-only prospective score diagnostics. */
(() => {
  'use strict';

  const REPORT_URL = './data/score_validation_report.json';
  const STATUS = {
    collecting_evidence: { label: 'A recolher dados', tone: 'neutral' },
    early_signal: { label: 'Sinal inicial', tone: 'amber' },
    multiple_cohorts_available: { label: 'Evidência múltipla', tone: 'green' }
  };
  const FACTOR_LABELS = {
    score: 'Score', quality_pct: 'Qualidade', growth_pct: 'Crescimento', balance_pct: 'Balanço',
    cashflow_pct: 'Cash flow', value_pct: 'Valuation', execution_pct: 'Execução',
    earnings_quality_pct: 'Qualidade dos resultados', capital_allocation_pct: 'Alocação de capital',
    stability_pct: 'Estabilidade'
  };

  let report = null;
  let loading = null;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));

  const finite = value => {
    if (value === null || value === undefined || value === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  };

  const signed = (value, digits = 2, suffix = '') => {
    const number = finite(value);
    if (number === null) return '—';
    return `${number > 0 ? '+' : ''}${number.toFixed(digits)}${suffix}`;
  };

  const dateLabel = value => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return '—';
    return new Intl.DateTimeFormat('pt-PT', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
  };

  async function loadReport(force = false) {
    if (report && !force) return report;
    if (loading && !force) return loading;
    loading = (async () => {
      const response = await fetch(`${REPORT_URL}?ts=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (!payload || typeof payload !== 'object' || !payload.horizons) throw new Error('Relatório inválido');
      report = payload;
      return payload;
    })();
    try { return await loading; }
    finally { loading = null; }
  }

  function ensureStyles() {
    if (document.getElementById('vestraModelValidationStyles')) return;
    const style = document.createElement('style');
    style.id = 'vestraModelValidationStyles';
    style.textContent = `
      .model-validation-trigger{display:inline-flex;align-items:center;gap:8px;margin-top:12px;padding:8px 12px;border:1px solid color-mix(in srgb,var(--border,#d7ddd9) 82%,transparent);border-radius:999px;background:color-mix(in srgb,var(--surface,#fff) 88%,transparent);color:var(--text,#17211e);font:inherit;font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 1px 0 rgba(0,0,0,.02)}
      .model-validation-trigger:hover{transform:translateY(-1px)}
      .model-validation-trigger__dot{width:7px;height:7px;border-radius:50%;background:#d39c38;box-shadow:0 0 0 3px rgba(211,156,56,.12)}
      .model-validation-overlay{position:fixed;inset:0;z-index:9998;background:rgba(12,18,16,.46);backdrop-filter:blur(8px);display:flex;align-items:flex-end;justify-content:center;padding:16px env(safe-area-inset-right) max(16px,env(safe-area-inset-bottom)) env(safe-area-inset-left)}
      .model-validation-sheet{width:min(760px,100%);max-height:min(88vh,900px);overflow:auto;background:var(--surface,#fff);color:var(--text,#17211e);border:1px solid var(--border,#dfe5e2);border-radius:24px 24px 20px 20px;box-shadow:0 28px 70px rgba(0,0,0,.24)}
      .model-validation-head{position:sticky;top:0;z-index:2;display:flex;justify-content:space-between;gap:16px;align-items:flex-start;padding:20px 20px 14px;background:color-mix(in srgb,var(--surface,#fff) 94%,transparent);backdrop-filter:blur(18px);border-bottom:1px solid var(--border,#e3e8e5)}
      .model-validation-kicker{font-size:11px;letter-spacing:.11em;text-transform:uppercase;color:var(--muted,#6d7a75);font-weight:800}.model-validation-head h3{margin:4px 0 4px;font-size:23px;letter-spacing:-.03em}.model-validation-head p{margin:0;color:var(--muted,#6d7a75);font-size:12px;line-height:1.45;max-width:520px}
      .model-validation-close{border:0;background:var(--surface-2,#f2f5f3);color:inherit;width:34px;height:34px;border-radius:50%;font-size:18px;cursor:pointer;flex:0 0 auto}
      .model-validation-body{padding:18px 20px 26px}.model-validation-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:16px}
      .model-validation-card{border:1px solid var(--border,#e0e6e3);border-radius:17px;padding:14px;background:var(--surface-2,#f7f9f8)}.model-validation-card__top{display:flex;align-items:center;justify-content:space-between;gap:8px}.model-validation-card__h{font-size:17px;font-weight:800}.model-validation-status{font-size:10px;font-weight:800;padding:5px 8px;border-radius:999px;background:#eef1ef;color:#65716c}.model-validation-status[data-tone="amber"]{background:#fff2d9;color:#8d5f0a}.model-validation-status[data-tone="green"]{background:#def4e8;color:#17633e}
      .model-validation-metrics{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.model-validation-metric small{display:block;color:var(--muted,#6d7a75);font-size:10px;margin-bottom:2px}.model-validation-metric strong{font-size:15px}.model-validation-card__foot{margin-top:11px;padding-top:10px;border-top:1px solid var(--border,#e0e6e3);font-size:10px;color:var(--muted,#6d7a75)}
      .model-validation-section{margin-top:18px}.model-validation-section h4{margin:0 0 8px;font-size:14px}.model-validation-note{border-left:3px solid #177b78;padding:11px 12px;background:color-mix(in srgb,#177b78 7%,var(--surface,#fff));border-radius:0 12px 12px 0;color:var(--muted,#66736e);font-size:11px;line-height:1.5}.model-validation-factor-list{display:grid;gap:7px}.model-validation-factor{display:grid;grid-template-columns:minmax(120px,1fr) 70px 1.3fr;align-items:center;gap:10px;font-size:11px}.model-validation-factor__bar{height:7px;background:var(--surface-2,#eef2f0);border-radius:999px;overflow:hidden}.model-validation-factor__fill{height:100%;border-radius:inherit;background:#177b78}.model-validation-factor__fill.is-negative{background:#b85a53}.model-validation-empty{padding:22px;border:1px dashed var(--border,#dfe5e2);border-radius:16px;text-align:center;color:var(--muted,#6d7a75);font-size:12px;line-height:1.5}.model-validation-meta{margin-top:14px;color:var(--muted,#6d7a75);font-size:10px}
      @media(max-width:640px){.model-validation-overlay{padding:0}.model-validation-sheet{max-height:92vh;border-radius:24px 24px 0 0}.model-validation-summary{grid-template-columns:1fr}.model-validation-factor{grid-template-columns:minmax(105px,1fr) 58px 1fr}.model-validation-head,.model-validation-body{padding-left:16px;padding-right:16px}}
    `;
    document.head.appendChild(style);
  }

  function horizonCard(days, data = {}) {
    const status = STATUS[data.status] || STATUS.collecting_evidence;
    const cohortCount = finite(data.cohort_count) ?? 0;
    const expectedCohorts = finite(data.expected_matured_cohorts);
    const capturePct = finite(data.cohort_capture_pct);
    const n = finite(data.n) ?? 0;
    const medianIc = data.median_cohort_rank_ic ?? data.rank_information_coefficient;
    const medianSpread = data.median_cohort_top_minus_bottom_pct ?? data.top_minus_bottom_pct;
    const nextMaturity = data.next_pending_maturity_date;
    const cohortLabel = expectedCohorts !== null && expectedCohorts > 0
      ? `${cohortCount}/${expectedCohorts}${capturePct !== null ? ` · ${capturePct.toFixed(0)}%` : ''}`
      : String(cohortCount);
    return `
      <article class="model-validation-card">
        <div class="model-validation-card__top">
          <div class="model-validation-card__h">${days} dias</div>
          <span class="model-validation-status" data-tone="${status.tone}">${status.label}</span>
        </div>
        <div class="model-validation-metrics">
          <div class="model-validation-metric"><small>Cohorts maturados / esperados</small><strong>${cohortLabel}</strong></div>
          <div class="model-validation-metric"><small>Observações</small><strong>${n}</strong></div>
          <div class="model-validation-metric"><small>Rank IC mediano</small><strong>${signed(medianIc, 3)}</strong></div>
          <div class="model-validation-metric"><small>Top − Bottom</small><strong>${signed(medianSpread, 2, '%')}</strong></div>
        </div>
        <div class="model-validation-card__foot">${cohortCount < 4 ? (nextMaturity ? `Próxima maturação prevista: ${dateLabel(nextMaturity)}. Ainda sem cohorts independentes suficientes para interpretar.` : 'Ainda sem cohorts independentes suficientes para interpretar.') : cohortCount < 8 ? 'Sinal preliminar; não usar para recalibrar pesos.' : 'Base mínima de cohorts atingida; confirmar noutro horizonte antes de calibrar.'}</div>
      </article>`;
  }

  function factorDiagnostics(payload) {
    const candidates = [];
    for (const days of ['28', '84', '168']) {
      const factors = payload?.horizons?.[days]?.factor_rank_information_coefficient;
      if (!factors || typeof factors !== 'object') continue;
      for (const [key, value] of Object.entries(factors)) {
        const number = finite(value);
        if (number !== null) candidates.push({ key, value: number, days: Number(days) });
      }
    }
    if (!candidates.length) return '<div class="model-validation-empty">Os IC por pilar aparecem automaticamente quando existirem pelo menos 20 observações comparáveis num horizonte.</div>';
    const bestByFactor = new Map();
    candidates.forEach(item => {
      const existing = bestByFactor.get(item.key);
      if (!existing || item.days > existing.days) bestByFactor.set(item.key, item);
    });
    const rows = [...bestByFactor.values()].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, 8);
    return `<div class="model-validation-factor-list">${rows.map(item => {
      const width = Math.min(100, Math.abs(item.value) * 200);
      return `<div class="model-validation-factor"><span>${esc(FACTOR_LABELS[item.key] || item.key)}</span><strong>${signed(item.value, 3)}</strong><div class="model-validation-factor__bar"><div class="model-validation-factor__fill ${item.value < 0 ? 'is-negative' : ''}" style="width:${width.toFixed(1)}%"></div></div></div>`;
    }).join('')}</div>`;
  }

  function render(payload) {
    const horizons = payload.horizons || {};
    const snapshotCount = finite(payload.snapshots_available) ?? 0;
    const outcomes = finite(payload.realised_outcomes) ?? Object.values(horizons).reduce((sum, item) => sum + (finite(item?.n) ?? 0), 0);
    return `
      <div class="model-validation-head">
        <div><div class="model-validation-kicker">Vestra Research · validação prospetiva</div><h3>Validação do modelo</h3><p>Mede se scores mais altos ficaram associados a retornos futuros melhores. Não é uma previsão de retorno nem uma recomendação de investimento.</p></div>
        <button class="model-validation-close" data-model-validation-close aria-label="Fechar">×</button>
      </div>
      <div class="model-validation-body">
        <div class="model-validation-summary">${['28','84','168'].map(days => horizonCard(days, horizons[days] || {})).join('')}</div>
        <div class="model-validation-section"><h4>Leitura dos pilares</h4>${factorDiagnostics(payload)}</div>
        <div class="model-validation-section"><h4>Como interpretar</h4><div class="model-validation-note"><strong>Rank IC</strong> é a correlação de Spearman entre o score conhecido na data do cohort e o retorno posterior. <strong>Top − Bottom</strong> compara o retorno médio do quintil de score mais alto com o mais baixo. O Vestra só deve reconsiderar pesos quando houver vários cohorts, consistência em pelo menos dois horizontes e estabilidade entre modelos/setores.</div></div>
        <div class="model-validation-meta">${snapshotCount} snapshot${snapshotCount === 1 ? '' : 's'} · ${outcomes} resultados realizados · relatório ${dateLabel(payload.generated_at)} · schema v${esc(payload.schema_version ?? '—')}</div>
      </div>`;
  }

  function closePanel() {
    document.getElementById('modelValidationOverlay')?.remove();
    document.body.style.removeProperty('overflow');
  }

  async function openPanel() {
    ensureStyles();
    closePanel();
    const overlay = document.createElement('div');
    overlay.id = 'modelValidationOverlay';
    overlay.className = 'model-validation-overlay';
    overlay.innerHTML = '<section class="model-validation-sheet" role="dialog" aria-modal="true" aria-label="Validação do modelo"><div class="model-validation-body"><div class="model-validation-empty">A carregar validação prospetiva…</div></div></section>';
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
    overlay.addEventListener('click', event => { if (event.target === overlay || event.target.closest('[data-model-validation-close]')) closePanel(); });
    document.addEventListener('keydown', onEscape, { once: true });
    try {
      const payload = await loadReport(true);
      const sheet = overlay.querySelector('.model-validation-sheet');
      if (sheet) sheet.innerHTML = render(payload);
    } catch (error) {
      const sheet = overlay.querySelector('.model-validation-sheet');
      if (sheet) sheet.innerHTML = `<div class="model-validation-head"><div><div class="model-validation-kicker">Vestra Research</div><h3>Validação do modelo</h3></div><button class="model-validation-close" data-model-validation-close aria-label="Fechar">×</button></div><div class="model-validation-body"><div class="model-validation-empty">Não foi possível carregar o relatório agora.<br><small>${esc(error?.message || 'Erro desconhecido')}</small></div></div>`;
    }
  }

  function onEscape(event) {
    if (event.key === 'Escape') closePanel();
  }

  function mountTrigger() {
    ensureStyles();
    const hero = document.querySelector('#viewMarket .market-hero-simple');
    if (!hero || hero.querySelector('[data-model-validation-open]')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'model-validation-trigger';
    button.dataset.modelValidationOpen = '1';
    button.innerHTML = '<span class="model-validation-trigger__dot"></span><span>Validação do modelo</span>';
    button.addEventListener('click', openPanel);
    hero.appendChild(button);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountTrigger, { once: true });
  else mountTrigger();

  window.VestraModelValidation = { open: openPanel, refresh: () => loadReport(true) };
})();
