const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: an empty opportunity lens clears previous rows instead of leaving stale candidates', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraMarketOpportunityLenses && window.VestraMarketOpportunities));
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 7_000 });

  await page.evaluate(() => {
    const rows = [{
      ticker: 'RECOV', name: 'Recovery Corp', quote_type: 'EQUITY',
      score: 72, data_coverage_pct: 82, confidence_score: 78,
      critical_metric_coverage_pct: 72, score_reliability: 'good', risk_gate: 'low',
      opportunity_timing_score: 66, estimate_signal: 'improving', recovery_status: 'confirmed'
    }];
    window.VestraMarketStaticUniverse = { getStocks: () => rows };
    const fixture = document.createElement('section');
    fixture.id = 'lensEmptyFixture';
    fixture.className = 'market-section';
    fixture.innerHTML = `
      <div class="market-section__head"><div><h3>Oportunidades agora</h3><p></p></div></div>
      <div class="market-list"></div>`;
    document.body.prepend(fixture);
    window.VestraMarketOpportunityLenses.select('recovery');
  });

  const fixture = page.locator('#lensEmptyFixture');
  await expect(fixture.locator('[data-market-ticker="RECOV"]')).toBeVisible();

  await fixture.locator('[data-vestra-lens="low52"]').tap();
  await expect(fixture.locator('[data-market-ticker="RECOV"]')).toHaveCount(0);
  await expect(fixture.locator('.market-row')).toHaveCount(0);
  await expect(fixture.locator('.vestra-lens-empty')).toBeVisible();
  await expect(fixture.locator('.vestra-lens-empty')).toContainText('mínimo de 52 semanas');
});