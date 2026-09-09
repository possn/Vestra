const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: filtered opportunity rows are actually hidden from layout', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraMarketOpportunityLenses));
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 7_000 });

  await page.evaluate(() => {
    window.VestraMarketStaticUniverse = { getStocks: () => [] };
    const fixture = document.createElement('section');
    fixture.id = 'lensRowHidingFixture';
    fixture.className = 'market-section';
    fixture.innerHTML = `
      <div class="market-section__head"><div><h3>Oportunidades agora</h3></div></div>
      <div class="market-list">
        <div class="market-row" data-market-ticker="AAA">AAA empresa estável</div>
        <div class="market-row" data-market-ticker="BBB">BBB recuperação confirmada</div>
      </div>`;
    document.body.prepend(fixture);
    const [a, b] = fixture.querySelectorAll('.market-row');
    a.__vestraStock = { ticker:'AAA', estimate_signal:'stable', recovery_status:'', opportunity_timing_score:52 };
    b.__vestraStock = { ticker:'BBB', estimate_signal:'improving', recovery_status:'confirmed', opportunity_timing_score:58 };
    window.VestraMarketOpportunityLenses.select('recovery');
  });

  const fixture = page.locator('#lensRowHidingFixture');
  const stable = fixture.locator('[data-market-ticker="AAA"]');
  const recovery = fixture.locator('[data-market-ticker="BBB"]');

  await expect(stable).toHaveClass(/vestra-lens-hidden/);
  await expect(stable).toHaveAttribute('data-vestra-lens-hidden', '1');
  await expect(stable).toBeHidden();
  await expect(recovery).toBeVisible();
});
