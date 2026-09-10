const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: opportunity lenses are tappable and persist the selected filter', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraMarketOpportunityLenses));
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 7_000 });

  await page.evaluate(() => {
    // This test owns an isolated opportunity section. The live opportunity renderer
    // watches the same heading and would otherwise replace the fixture rows with the
    // real ranked universe on its next MutationObserver pass.
    window.VestraMarketStaticUniverse = { getStocks: () => [] };

    const fixture = document.createElement('section');
    fixture.id = 'lensFixture';
    fixture.className = 'market-section';
    fixture.innerHTML = `
      <div class="market-section__head"><div><h3>Oportunidades agora</h3></div></div>
      <div class="market-list">
        <div class="market-row" data-market-ticker="AAA">AAA empresa estável</div>
        <div class="market-row" data-market-ticker="BBB">BBB recuperação confirmada</div>
        <div class="market-row" data-market-ticker="CCC">CCC junto do mínimo anual</div>
      </div>`;
    document.body.prepend(fixture);
    const [a,b,c] = fixture.querySelectorAll('.market-row');
    a.__vestraStock = { ticker:'AAA', estimate_signal:'stable', recovery_status:'', opportunity_timing_score:52, low52_above_low_pct:11.2 };
    b.__vestraStock = { ticker:'BBB', estimate_signal:'improving', recovery_status:'confirmed', opportunity_timing_score:58, low52_above_low_pct:7.1 };
    c.__vestraStock = { ticker:'CCC', estimate_signal:'stable', recovery_status:'', opportunity_timing_score:56, low52_above_low_pct:3.2 };
    window.VestraMarketOpportunityLenses.select('all');
  });

  const fixture = page.locator('#lensFixture');
  const bar = fixture.locator('.vestra-opportunity-lenses');
  await expect(bar).toBeVisible();

  const low52 = bar.locator('[data-vestra-lens="low52"]');
  await low52.tap();
  await expect(low52).toHaveClass(/is-active/);
  await expect(low52).toHaveAttribute('aria-pressed', 'true');
  await expect(fixture.locator('[data-market-ticker="AAA"]')).toBeHidden();
  await expect(fixture.locator('[data-market-ticker="BBB"]')).toBeHidden();
  await expect(fixture.locator('[data-market-ticker="CCC"]')).toBeVisible();

  const recovery = bar.locator('[data-vestra-lens="recovery"]');
  await recovery.tap();
  await expect(recovery).toHaveClass(/is-active/);
  await expect(recovery).toHaveAttribute('aria-pressed', 'true');
  await expect(fixture.locator('[data-market-ticker="AAA"]')).toBeHidden();
  await expect(fixture.locator('[data-market-ticker="BBB"]')).toBeVisible();

  await fixture.evaluate(node => {
    node.querySelector('.market-list').insertAdjacentHTML('beforeend', '<div class="market-row" data-market-ticker="DDD">DDD empresa estável</div>');
  });
  await expect.poll(async () => page.evaluate(() => window.VestraMarketOpportunityLenses.active)).toBe('recovery');
  await expect(fixture.locator('[data-market-ticker="DDD"]')).toBeHidden();

  const all = bar.locator('[data-vestra-lens="all"]');
  await all.tap();
  await expect(all).toHaveClass(/is-active/);
  await expect(fixture.locator('[data-market-ticker="AAA"]')).toBeVisible();
  await expect(fixture.locator('[data-market-ticker="DDD"]')).toBeVisible();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
