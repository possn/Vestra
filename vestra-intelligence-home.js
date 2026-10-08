/* Vestra Intelligence Home — opt-in, non-financial shell. */
(() => {
  'use strict';
  const params = new URLSearchParams(window.location.search);
  const enabled = params.get('vestra2') === '1';
  if (!enabled) return;

  async function showCoverage(host) {
    const label = host.querySelector('[data-vestra-coverage]');
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
      label.dataset.status = !valid ? 'bad' : fresh ? 'observed' : 'stale';
      const timestamp = new Date(date).toLocaleString('pt-PT');
      label.textContent = 'Cobertura publicada · ' + rows.toLocaleString('pt-PT') +
        ' ativos verificados · ' + violations + ' violações · ' +
        (valid ? (fresh ? 'verificada' : 'relatório antigo') : 'atenção') +
        ' · ' + timestamp + ' · Fonte: coverage_guard.json';
    } catch (_) {
      label.dataset.status = 'missing';
      label.textContent = 'Cobertura publicada indisponível · sem confirmação de integridade';
    }
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

  function init() {
    const view = document.getElementById('viewDashboard');
    const host = document.getElementById('vestraIntelligenceHome');
    if (!view || !host) return;
    host.hidden = false;
    syncExistingBarometer(host);
    syncPortfolioEvidence(host);
    window.addEventListener('vestra:dashboard-signal-updated', event => {
      if (event?.detail?.source === 'market-sentiment') syncExistingBarometer(host);
    });
    showCoverage(host);
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
