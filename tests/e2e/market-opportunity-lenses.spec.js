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
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 10_000 });
  await page.locator('#navMarket').tap();
  await page.waitForFunction(() => Boolean(window.VestraMarketOpportunityLenses && window.VestraMarketOpportunities));
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
  expect(new Set([low52.join(','), emerging.join(','), recovery.join(','), value.join(',')]).size).toBeGreaterThan(2);
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});

test('iPhone/WebKit: More sectors defers canonical rerender until the native picker has closed', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await waitForLaunch(page);

  await page.evaluate((rows) => {
    window.VestraMarketStaticUniverse = { getStocks: () => rows };
    window.__sectorCommitLog = [];
    document.querySelector('#moreSectorFixture')?.remove();
    const fixture = document.createElement('section');
    fixture.id = 'moreSectorFixture';
    fixture.className = 'market-section';
    fixture.style.cssText = 'position:fixed;left:8px;right:8px;top:96px;z-index:2147483647;max-height:70vh;overflow:auto;background:#fff;';
    fixture.innerHTML = `
      <div class="market-section__head"><div><h3>Oportunidades agora</h3><p></p></div></div>
      <div class="market-sector-row">
        <button type="button" data-market-sector="all" class="is-active">Todos</button>
        <button type="button" data-market-sector="Technology">Technology</button>
        <label class="market-sector-more"><span>Mais</span>
          <select data-market-sector-select aria-label="Mais setores">
            <option value="">Mais setores</option>
            <option value="Energy">Energy</option>
            <option value="Communication Services">Communication Services</option>
          </select>
        </label>
      </div>
      <div class="market-list"></div>`;
    document.body.prepend(fixture);

    // Mimic market.js's delegated canonical ownership. A native change must be
    // suppressed in capture; only the deferred change on whichever select is
    // currently connected may reach this owner.
    document.addEventListener('change', event => {
      const select = event.target;
      if (!select?.matches?.('#moreSectorFixture [data-market-sector-select]')) return;
      window.__sectorCommitLog.push({ value: select.value, connected: select.isConnected, at: performance.now() });
      window.VestraMarketOpportunities.refresh('emerging', select.value || 'all');
    });
    window.VestraMarketOpportunityLenses.select('emerging');
  }, [
    candidate('ENERGY1', { sector: 'Energy', estimate_signal: 'improving', thesis_direction: 'up', opportunity_timing_score: 72 }),
    candidate('COMM1', { sector: 'Communication Services', estimate_signal: 'improving', thesis_direction: 'up', opportunity_timing_score: 71 }),
    candidate('TECH1', { sector: 'Technology', estimate_signal: 'improving', thesis_direction: 'up', opportunity_timing_score: 70 }),
  ]);

  const fixture = page.locator('#moreSectorFixture');
  const dropdown = fixture.locator('[data-market-sector-select]');
  const more = fixture.locator('.market-sector-more');
  const rowTickers = () => fixture.locator('.market-row').evaluateAll(rows => rows.map(row => row.dataset.marketTicker));

  const assertLiveNativeSelect = async () => {
    await expect(more).toBeVisible();
    await expect(dropdown).toBeEnabled();
    await expect(dropdown).toHaveCSS('pointer-events', 'auto');
    const hit = await dropdown.evaluate(select => {
      const r = select.getBoundingClientRect();
      const target = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return {
        width: r.width,
        height: r.height,
        connected: select.isConnected,
        targetIsSelectOrInsideLabel: target === select || Boolean(target?.closest?.('.market-sector-more')),
      };
    });
    expect(hit.connected).toBe(true);
    expect(hit.width).toBeGreaterThan(0);
    expect(hit.height).toBeGreaterThan(0);
    expect(hit.targetIsSelectOrInsideLabel).toBe(true);
  };

  const chooseMore = async (value) => {
    await assertLiveNativeSelect();
    const beforeCommits = await page.evaluate(() => window.__sectorCommitLog.length);
    const immediate = await dropdown.evaluate((select, next) => {
      window.__sectorOriginalNode = select;
      select.value = next;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return {
        connected: select.isConnected,
        sameNode: document.querySelector('#moreSectorFixture [data-market-sector-select]') === select,
      };
    }, value);
    // The native event must not synchronously reach the canonical owner or
    // replace the select while WebKit is dismissing the picker.
    expect(immediate.connected).toBe(true);
    expect(immediate.sameNode).toBe(true);
    expect(await page.evaluate(() => window.__sectorCommitLog.length)).toBe(beforeCommits);

    await expect.poll(() => page.evaluate(() => window.__sectorCommitLog.length)).toBeGreaterThan(beforeCommits);
    const lastCommit = await page.evaluate(() => window.__sectorCommitLog.at(-1));
    expect(lastCommit.value).toBe(value);
    expect(lastCommit.connected).toBe(true);
    await assertLiveNativeSelect();
  };

  await chooseMore('Energy');
  await expect(more).toHaveClass(/is-active/);
  await expect(more).not.toHaveAttribute('data-market-sector', /.+/);
  await expect.poll(rowTickers).toEqual(['ENERGY1']);

  const firstCommitCount = await page.evaluate(() => window.__sectorCommitLog.length);
  expect(firstCommitCount).toBe(1);

  await chooseMore('Communication Services');
  await expect(dropdown).toHaveValue('Communication Services');
  await expect(more).not.toHaveAttribute('data-market-sector', /.+/);
  await expect.poll(rowTickers).toEqual(['COMM1']);

  const commits = await page.evaluate(() => window.__sectorCommitLog.map(item => item.value));
  expect(commits).toEqual(['Energy', 'Communication Services']);
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});