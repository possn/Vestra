/* Vestra Intelligence Home — opt-in, non-financial shell. */
(() => {
  'use strict';
  const params = new URLSearchParams(window.location.search);
  const enabled = params.get('vestra2') === '1';
  if (!enabled) return;

  async function showCoverage(host) {
    const label = host.querySelector('[data-vestra-coverage]');
    const evidence = host.querySelector('[data-vestra-model-evidence]');
    if (!label) return;
    label.textContent = 'A verificar cobertura dos dados publicados…';
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      let response;
      try { response = await fetch('./data/coverage_guard.json', {cache:'no-store', signal:controller.signal}); }
      finally { clearTimeout(timeout); }
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const guard = await response.json();
      const date = Date.parse(guard?.generated_at);
      const rows = guard?.rows_checked;
      const violations = guard?.violation_count;
      if (!Number.isFinite(date) || date > Date.now() + 300000 ||
          !Number.isInteger(rows) || rows < 0 ||
          !Number.isInteger(violations) || violations < 0 ||
          typeof guard?.ok !== 'boolean') throw new Error('Dados incompletos');
      const ageHours = (Date.now() - date) / 3600000;
      const fresh = ageHours >= 0 && ageHours <= 36;
      const valid = guard.ok === true && violations === 0;
      if (evidence) {
        evidence.dataset.status = valid && fresh && rows > 0 ? 'observed' : 'stale';
        evidence.textContent = 'Model Evidence · integridade ' + (valid && fresh && rows > 0 ? 'verificada' : 'não confirmada') +
          ' · validação preditiva e fora da amostra não demonstrada neste relatório';
      }
      label.dataset.status = !valid ? 'bad' : fresh ? 'observed' : 'stale';
      const timestamp = new Date(date).toLocaleString('pt-PT');
      label.textContent = 'Cobertura publicada · ' + rows.toLocaleString('pt-PT') +
        ' ativos verificados · ' + violations + ' violações · ' +
        (valid ? (fresh ? 'verificada' : 'relatório antigo') : 'atenção') +
        ' · ' + timestamp + ' · Fonte: coverage_guard.json';
    } catch (_) {
      if (evidence) {
        evidence.dataset.status = 'missing';
        evidence.textContent = 'Model Evidence · integridade e validação preditiva não verificadas';
      }
      label.dataset.status = 'missing';
      label.textContent = 'Cobertura publicada indisponível · sem confirmação de integridade';
    }
  }

  async function showProspectiveValidation(host) {
    const output = host.querySelector('[data-vestra-prospective-evidence]');
    if (!output) return;
    output.dataset.status = 'missing';
    output.textContent = 'Validação prospetiva · a verificar histórico publicado…';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    async function readReport(path) {
      const response = await fetch(path, {cache:'no-store', signal:controller.signal});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }
    let results;
    try {
      results = await Promise.allSettled([
        readReport('./data/score_validation_report.json'),
        readReport('./data/opportunity_validation_report.json')
      ]);
    } finally { clearTimeout(timeout); }
    const score = results[0].status === 'fulfilled' ? results[0].value : null;
    const opportunity = results[1].status === 'fulfilled' ? results[1].value : null;
    const scoreTime = Date.parse(score?.generated_at);
    const validThrough = Date.parse(score?.freshness?.valid_through);
    const scoreFresh = Number.isFinite(scoreTime) && Number.isFinite(validThrough) &&
      scoreTime <= Date.now() + 300000 && Date.now() <= validThrough;
    const h = score?.horizons?.['28'];
    const n = h?.n, cohorts = h?.cohort_count, ic = h?.rank_information_coefficient;
    const scoreValid = scoreFresh && score?.schema_version === 5 &&
      Number.isInteger(n) && n >= 0 && Number.isInteger(cohorts) && cohorts >= 0 &&
      (ic === null || (typeof ic === 'number' && Number.isFinite(ic)));
    const oppTime = Date.parse(opportunity?.generated_at);
    const oppFresh = Number.isFinite(oppTime) && oppTime <= Date.now() + 300000 &&
      Date.now() - oppTime <= 36 * 3600000;
    const oppN = opportunity?.horizons?.['28']?.n;
    const oppValid = oppFresh && opportunity?.schema_version === 1 &&
      Number.isInteger(oppN) && oppN >= 0;
    const scoreText = scoreValid
      ? 'Score 28d: ' + n.toLocaleString('pt-PT') + ' observações em ' +
        cohorts + ' coortes · Rank IC ' + (ic == null ? 'indisponível' : ic.toFixed(3)) +
        ' · ' + (cohorts < 5 ? 'evidência temporal insuficiente' : 'evidência observacional')
      : 'Score: relatório indisponível ou desatualizado';
    const oppText = oppValid
      ? 'Oportunidades 28d: ' + oppN.toLocaleString('pt-PT') +
        ' resultados · ' + (oppN === 0 ? 'a recolher evidência' : 'evidência observacional')
      : 'Oportunidades: relatório indisponível ou desatualizado';
    output.dataset.status = scoreValid && oppValid && cohorts >= 5 && oppN > 0 ? 'observed'
      : scoreValid || oppValid ? 'stale' : 'missing';
    output.textContent = 'Validação prospetiva · ' + scoreText + ' · ' + oppText +
      ' · Fonte: relatórios prospetivos independentes';
  }

  function syncExistingBarometer(host) {
    const output = host.querySelector('[data-vestra-market-status]');
    if (!output) return;
    const barometer = document.getElementById('vestraMarketSentimentCard');
    const score = barometer?.querySelector('.dms-score');
    const label = barometer?.querySelector('.dms-label');
    const raw = score?.textContent?.trim() || '';
    const value = Number.parseInt(raw, 10);
    if (!barometer || !score || !Number.isInteger(value) || value < 0 || value > 100 || !label?.textContent?.trim()) {
      output.dataset.status = 'missing';
      output.textContent = 'Barómetro indisponível · consultar a secção de mercado';
      return;
    }
    output.dataset.status = 'observed';
    output.textContent = 'Barómetro existente · ' + value + '/100 · ' +
      label.textContent.trim() + ' · Fonte: Vestra Market Sentiment (proxy de preço, não breadth real)';
  }

  function syncPortfolioEvidence(host) {
    const output = host.querySelector('[data-vestra-portfolio-evidence]');
    if (!output) return;
    const api = window.VestraDashboardPortfolioConcentration;
    try {
      if (!api || typeof api.marketHoldings !== 'function' ||
          typeof api.concentrationSnapshot !== 'function') throw new Error('motor indisponível');
      const snapshot = api.concentrationSnapshot(api.marketHoldings());
      if (!snapshot || !Number.isInteger(snapshot.count) || snapshot.count <= 0 ||
          !Number.isFinite(snapshot.top3) || snapshot.top3 < 0 || snapshot.top3 > 1)
        throw new Error('cobertura insuficiente');
      output.dataset.status = 'observed';
      // Do not expose personal portfolio values in the dashboard preview.
      output.textContent = 'Carteira · concentração mensurável em ' +
        snapshot.count + ' posições de mercado · Rever pesos e sobreposição no módulo Carteira · Fonte: motor de concentração existente';
    } catch (_) {
      output.dataset.status = 'missing';
      output.textContent = 'Carteira · concentração não confirmada · abrir Carteira para verificar';
    }
  }


  // Session-only snapshot: never persisted across reloads or users.
  // Derived exclusively from the canonical rendered Decision Center.
  let lastDecision = null;
  function syncDecisionCenter(host) {
    const output = host.querySelector('[data-vestra-decision-state]');
    if (!output) return;
    const sheet = document.getElementById('marketSheet');
    const center = sheet?.dataset.tool === 'portfolio'
      ? sheet.querySelector('.market-decision-center[data-vpu-state]') : null;
    const state = center?.dataset.vpuState || '';
    const rawCoverage = center?.dataset.vpuCoverage;
    const coverage = rawCoverage === undefined || rawCoverage === '' ? NaN : Number(rawCoverage);
    const known = ['Rever', 'Atenção', 'Acompanhar', 'Dados parciais', 'Estável'];
    // Do not convert an absent/invalid coverage to zero or a healthy decision.
    if (center && known.includes(state) && Number.isFinite(coverage) &&
        coverage >= 0 && coverage <= 100) {
      lastDecision = {state, coverage, observedAt: Date.now()};
    }
    const snapshot = lastDecision;
    const currentReading = Boolean(center && known.includes(state) && Number.isFinite(coverage) &&
      coverage >= 0 && coverage <= 100);
    // Do not silently present an old diagnosis as current.
    const age = snapshot ? Date.now() - snapshot.observedAt : Infinity;
    if (!snapshot || age < 0 || age > 15 * 60 * 1000) {
      lastDecision = null;
      output.dataset.status = 'missing';
      output.textContent = 'Decision Center · sem leitura verificada nesta sessão · abrir análise da Carteira';
      return;
    }
    // A historical observation is never a live clearance to invest.
    output.dataset.status = !currentReading ? 'stale' :
      snapshot.state === 'Rever' || snapshot.state === 'Atenção' ? 'bad' :
      snapshot.state === 'Estável' && snapshot.coverage >= 99.5 ? 'observed' : 'stale';
    const elapsed = Math.max(0, Math.floor(age / 60000));
    output.textContent = 'Decision Center · ' + snapshot.state +
      ' · cobertura ' + Math.round(snapshot.coverage) + '% · ' +
      (currentReading ? 'leitura atual do dossier' : 'leitura anterior da sessão · confirmar após alterações à carteira') +
      ' · Fonte: motor de decisão da carteira';
  }

  function init() {
    const view = document.getElementById('viewDashboard');
    const host = document.getElementById('vestraIntelligenceHome');
    if (!view || !host) return;
    host.hidden = false;
    syncExistingBarometer(host);
    syncPortfolioEvidence(host);
    syncDecisionCenter(host);
    window.addEventListener('vestra:market-sheet-changed', () => syncDecisionCenter(host));
    window.addEventListener('vestra:local-state-writing', () => {
      lastDecision = null;
      const output = host.querySelector('[data-vestra-decision-state]');
      if (output) {
        output.dataset.status = 'missing';
        output.textContent = 'Decision Center · carteira ou estado local alterado · reabrir análise para atualizar';
      }
    });
    window.addEventListener('vestra:dashboard-signal-updated', event => {
      if (event?.detail?.source === 'market-sentiment') syncExistingBarometer(host);
    });
    showCoverage(host);
    showProspectiveValidation(host);
    host.dataset.vestraIntelligence = '1';
    host.setAttribute('data-theme', document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
    host.addEventListener('click', event => {
      const button = event.target.closest('button[data-vestra-go]');
      if (!button || !host.contains(button)) return;
      const target = button.dataset.vestraGo;
      if (!['market', 'portfolio', 'dashboard'].includes(target)) return;
      if (typeof window.setView === 'function') window.setView(target);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
