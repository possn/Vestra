const { test, expect } = require('@playwright/test');

test.use({ serviceWorkers: 'block' });

test('iPhone/WebKit: Portfolio Optimize follows one canonical decision journey', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.waitForFunction(() => !!window.VestraMarket?.ensureLoaded);
  await page.evaluate(() => window.VestraMarket.ensureLoaded());

  await page.locator('[data-market-tool="portfolio"]').first().click();
  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible({ timeout: 15_000 });
  await expect(sheet).toHaveAttribute('data-tool', 'portfolio');
  await page.waitForFunction(() =>
    !!window.VestraPortfolioHierarchy &&
    !!window.VestraPortfolioUI &&
    !!window.VestraPortfolioCollapsibles
  );

  // Replace portfolio body with a deterministic canonical fixture. The test
  // verifies the user journey and canonical visible order without inventing a
  // DOM-reordering responsibility that the hierarchy does not own.
  await page.evaluate(() => {
    const content = document.getElementById('marketSheetContent');
    const cards = [
      ['swap', 'Alternativas no mesmo setor'],
      ['scenario', 'Se substituíres pelo mesmo valor'],
      ['rebalance', 'Onde melhora mais este capital?'],
      ['overlap', 'Concentração e overlap'],
      ['map', 'Mapa da carteira'],
      ['plan', 'Plano de rebalanceamento'],
    ];
    content.innerHTML = '<div class="market-decision-center"><small>PORTFOLIO DECISION CENTER</small><h4>O que merece atenção agora</h4></div>' +
      cards.map(([kind, title]) =>
        `<div class="market-detail-card" data-ux-kind="${kind}"><h4>${title}</h4><p>Fixture ${kind}</p></div>`
      ).join('') +
      '<section class="market-portfolio-section" id="e2eBaseHoldings"><h3>Ações, ETFs e fundos</h3></section>';
    window.VestraPortfolioHierarchy.refresh();
  });

  const explore = sheet.locator('[data-vpu-toggle]').first();
  await expect(explore).toBeVisible();
  await explore.click();
  await sheet.locator('[data-vpu-tab="optimize"]').click();

  const visibleCards = sheet.locator('.vpu-section-card:not(.vpu-hidden)');
  await expect(visibleCards).toHaveCount(6);
  expect(await visibleCards.evaluateAll(nodes => nodes.map(n => n.dataset.uxKind))).toEqual([
    'swap', 'scenario', 'rebalance', 'overlap', 'map', 'plan'
  ]);

  const guide = sheet.locator('.vpu-optimize-guide');
  await expect(guide).toBeVisible();
  await expect(guide).toContainText('Encontrar alternativa');
  await expect(guide).toContainText('Simular impacto');
  await expect(guide).toContainText('Redistribuir capital');

  for (const kind of ['swap', 'scenario', 'rebalance', 'overlap', 'map', 'plan']) {
    await expect(sheet.locator(`[data-ux-kind="${kind}"]`)).toHaveClass(/is-collapsed/);
  }

  const swap = sheet.locator('[data-ux-kind="swap"]');
  const scenario = sheet.locator('[data-ux-kind="scenario"]');
  const rebalance = sheet.locator('[data-ux-kind="rebalance"]');

  await swap.click({ position: { x: 24, y: 24 } });
  await expect(swap).not.toHaveClass(/is-collapsed/);

  await scenario.click({ position: { x: 24, y: 24 } });
  await expect(scenario).not.toHaveClass(/is-collapsed/);
  await expect(swap).toHaveClass(/is-collapsed/);

  await rebalance.locator(':scope > [data-collapse-toggle]').click();
  await expect(rebalance).not.toHaveClass(/is-collapsed/);
  await expect(scenario).toHaveClass(/is-collapsed/);

  await expect(sheet.locator('[data-ux-kind="overlap"]')).toHaveClass(/vpu-support-start/);
  await expect(sheet.locator('#e2eBaseHoldings')).toBeHidden();

  await sheet.locator('[data-vpu-exit]').click();
  await expect(sheet.locator('#e2eBaseHoldings')).toBeVisible();
  await expect(sheet.locator('.vpu-tabs-shell')).toBeHidden();

  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
