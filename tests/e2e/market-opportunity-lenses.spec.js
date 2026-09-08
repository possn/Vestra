const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: opportunity lenses are tappable and persist the selected filter', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => Boolean(window.VestraMarketOpportunityLenses));

  await page.evaluate(() => {
    const fixture = document.createElement('section');
    fixture.id = 'lensFixture';
    fixture.className = 'market-section';
    fixture.innerHTML = `
      <div class="market-section__head"><div><h3>Oportunidades agora</h3></div></div>
      <div class="market-list">
        <div class="market-row" data-market-ticker="AAA">AAA empresa estável</div>
        <div class="market-row" data-market-ticker="BBB">BBB recuperação confirmada</div>
      </div>`;
    document.body.prepend(fixture);
    const [a,b] = fixture.querySelectorAll('.market-row');
    a.__vestraStock = { ticker:'AAA', estimate_signal:'stable', recovery_status:'', opportunity_timing_score:52 };
    b.__vestraStock = { ticker:'BBB', estimate_signal:'improving', recovery_status:'confirmed', opportunity_timing_score:58 };
    window.VestraMarketOpportunityLenses.select('all');
  });

  const fixture = page.locator('#lensFixture');
  const bar = fixture.locator('.vestra-opportunity-lenses');
  await expect(bar).toBeVisible();

  const recovery = bar.locator('[data-vestra-lens="recovery"]');
  await recovery.tap();
  await expect(recovery).toHaveClass(/is-active/);
  await expect(recovery).toHaveAttribute('aria-pressed', 'true');
  await expect(fixture.locator('[data-market-ticker="AAA"]')).toBeHidden();
  await expect(fixture.locator('[data-market-ticker="BBB"]')).toBeVisible();

  await fixture.evaluate(node => {
    node.querySelector('.market-list').insertAdjacentHTML('beforeend', '<div class="market-row" data-market-ticker="CCC">CCC empresa estável</div>');
  });
  await expect.poll(async () => page.evaluate(() => window.VestraMarketOpportunityLenses.active)).toBe('recovery');
  await expect(fixture.locator('[data-market-ticker="CCC"]')).toBeHidden();

  const all = bar.locator('[data-vestra-lens="all"]');
  await all.tap();
  await expect(all).toHaveClass(/is-active/);
  await expect(fixture.locator('[data-market-ticker="AAA"]')).toBeVisible();
  await expect(fixture.locator('[data-market-ticker="CCC"]')).toBeVisible();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
