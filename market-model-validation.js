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
    const link = document.createElement('link');
    link.id = 'vestraModelValidationStyles';
    link.rel = 'stylesheet';
    link.href = 'market-model-validation.css?v=1.0';
    document.head.appendChild(link);
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

  function segmentDiagnostics(payload) {
    const rows = [];
    for (const days of ['28', '84', '168']) {
      const horizon = payload?.horizons?.[days] || {};
      for (const [kind, source] of [['Modelo', horizon.by_score_model], ['Setor', horizon.by_sector]]) {
        if (!source || typeof source !== 'object') continue;
        for (const [name, stats] of Object.entries(source)) {
          if (!stats || typeof stats !== 'object') continue;
          const n = finite(stats.n) ?? 0;
          const ic = finite(stats.median_cohort_rank_ic ?? stats.rank_information_coefficient);
          const spread = finite(stats.median_cohort_top_minus_bottom_pct ?? stats.top_minus_bottom_pct);
          if (n < 20 && ic === null && spread === null) continue;
          rows.push({ kind, name, days: Number(days), n, ic, spread });
        }
      }
    }
    if (!rows.length) return '';
    rows.sort((a, b) => (b.days - a.days) || (b.n - a.n) || a.name.localeCompare(b.name));
    const selected = rows.slice(0, 12);
    return `<div class="model-validation-section"><h4>Por modelo e setor</h4><div class="model-validation-segments">${selected.map(row => `<div class="model-validation-segment"><div><small>${esc(row.kind)} · ${row.days}d</small><strong>${esc(row.name)}</strong></div><div><small>n</small><strong>${row.n}</strong></div><div><small>Rank IC</small><strong>${signed(row.ic,3)}</strong></div><div><small>Top − Bottom</small><strong>${signed(row.spread,2,'%')}</strong></div></div>`).join('')}</div><div class="model-validation-meta">Amostras segmentadas pequenas são apenas diagnósticas; não servem para recalibrar pesos isoladamente.</div></div>`;
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
        ${segmentDiagnostics(payload)}
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