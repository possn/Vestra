const { test, expect } = require('@playwright/test');

const candidate = (ticker, extra = {}) => ({
  ticker,
  name: `${ticker} Corp`,
  quote_type: 'EQUITY',
  score: 70,
  data_coverage_pct: 80,
  confidence_score: 75,
  critical_metric_coverage_pct: 70,
  score_reliability: 'good',
  risk_gate: 'low',
  opportunity_timing_score: 60,
  ...extra,
});

async function waitForLaunch(page) {
  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraMarketOpportunityLenses && window.VestraMarketOpportunities));
  // Splash contract is 6.2s failsafe + 0.72s fade; leave scheduling headroom on CI WebKit.
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 10_000 });
}

test('iPhone/WebKit: each opportunity lens ranks the full universe independently', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await waitForLaunch(page);

  await page.evaluate((rows) => {
    window.VestraMarketStaticUniverse = { getStocks: () => rows };
    const fixture = document.createElement('section');
    fixture.id = 'lensFixture';
    fixture.className = 'market-section';
    fixture.innerHTML = `
      <div class="market-section__head"><div><h3>Oportunidades agora</h3><p></p></div></div>
      <div class="market-list"></div>`;
    document.body.prepend(fixture);
    window.VestraMarketOpportunityLenses.select('all');
  }, [
    candidate('EARLY', { estimate_signal: 'improving', recovery_status: '', thesis_direction: 'up', opportunity_timing_score: 68 }),
    candidate('RECOV', { estimate_signal: 'improving', recovery_status: 'confirmed', opportunity_timing_score: 66 }),
    candidate('LOW52', { low52_above_low_pct: 2.1, opportunity_timing_score: 55 }),
    candidate('VALUE', { fair_value_upside_pct: 34, valuation_signal: 'undervalued', opportunity_timing_score: 57 }),
  ]);

  const fixture = page.locator('#lensFixture');
  const bar = fixture.locator('.vestra-opportunity-lenses');
  await expect(bar).toBeVisible();

  const select = async (lens, ticker) => {
    const button = bar.locator(`[data-vestra-lens="${lens}"]`);
    await button.tap();
    await expect(button).toHaveClass(/is-active/);
    await expect(button).toHaveAttribute('aria-pressed', 'true');
    await expect(fixture.locator(`[data-market-ticker="${ticker}"]`)).toBeVisible();
    return fixture.locator('.market-row').evaluateAll(rows => rows.map(row => row.dataset.marketTicker));
  };

  const low52 = await select('low52', 'LOW52');
  expect(low52).toEqual(['LOW52']);

  const emerging = await select('emerging', 'EARLY');
  expect(emerging).toContain('EARLY');

  const recovery = await select('recovery', 'RECOV');
  expect(recovery).toContain('RECOV');

  const value = await select('value', 'VALUE');
  expect(value).toContain('VALUE');

  // Lenses are independent full-universe strategies, not mutually-exclusive
  // buckets. A company may legitimately satisfy more than one thesis; what
  // matters is that each lens can discover and rank its own qualifying names.
  expect(new Set([low52.join(','), emerging.join(','), recovery.join(','), value.join(',')]).size).toBeGreaterThan(2);
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: More-sector selection restricts opportunity shortlist', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await waitForLaunch(page);

  await page.evaluate((rows) => {
    window.VestraMarketStaticUniverse = { getStocks: () => rows };
    document.querySelector('#moreSectorFixture')?.remove();
    const fixture = document.createElement('section');
    fixture.id = 'moreSectorFixture';
    fixture.className = 'market-section';
    fixture.innerHTML = `
      <div class="market-section__head"><div><h3>Oportunidades agora</h3><p></p></div></div>
      <div class="market-sector-row">
        <button type="button" data-market-sector="all" class="is-active">Todos</button>
        <label class="market-sector-more"><span>Mais setores</span>
          <select data-market-sector-select>
            <option value="">Mais setores</option>
            <option value="Energy">Energy</option>
            <option value="Communication Services">Communication Services</option>
          </select>
        </label>
      </div>
      <div class="market-list"></div>`;
    document.body.prepend(fixture);
    window.VestraMarketOpportunityLenses.select('emerging');
  }, [
    candidate('ENERGY1', { sector: 'Energy', estimate_signal: 'improving', thesis_direction: 'up', opportunity_timing_score: 72 }),
    candidate('COMM1', { sector: 'Communication Services', estimate_signal: 'improving', thesis_direction: 'up', opportunity_timing_score: 71 }),
    candidate('TECH1', { sector: 'Technology', estimate_signal: 'improving', thesis_direction: 'up', opportunity_timing_score: 70 }),
  ]);

  const fixture = page.locator('#moreSectorFixture');
  const dropdown = fixture.locator('[data-market-sector-select]');

  await dropdown.selectOption('Energy');
  await expect(fixture.locator('.market-sector-more')).toHaveClass(/is-active/);
  await expect(fixture.locator('.market-sector-more')).toHaveAttribute('data-market-sector', 'Energy');
  await expect(fixture.locator('[data-market-ticker="ENERGY1"]')).toBeVisible();
  let tickers = await fixture.locator('.market-row').evaluateAll(rows => rows.map(row => row.dataset.marketTicker));
  expect(tickers).toEqual(['ENERGY1']);

  await dropdown.selectOption('Communication Services');
  await expect(fixture.locator('.market-sector-more')).toHaveAttribute('data-market-sector', 'Communication Services');
  await expect(fixture.locator('[data-market-ticker="COMM1"]')).toBeVisible();
  tickers = await fixture.locator('.market-row').evaluateAll(rows => rows.map(row => row.dataset.marketTicker));
  expect(tickers).toEqual(['COMM1']);

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
