const { test, expect } = require('@playwright/test');

// This test owns a mocked data source. The separate PWA tests cover service workers.
test.use({ serviceWorkers: 'block' });

async function waitForLaunch(page) {
  await page.goto('/index.html');
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 10_000 });
}

test('iPhone/WebKit: politician picker supports live name search', async ({ page }) => {
  const pageErrors = [];
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  let fixtureRequests = 0;
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.route(/\/data\/politicians\.json(?:\?.*)?$/, async route => {
    fixtureRequests += 1;
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        schema_version: 2,
        generated_at: now.toISOString(),
        source_last_updated: today,
        newest_disclosure: today,
        coverage_chambers: ['House', 'Senate'],
        source: 'Test disclosure feed',
        members: [
          { key: 'congress:visible-preset', name: 'Visible Preset', chamber: 'House' },
          { key: 'congress:alexandra-searchable-example', name: 'Alexandra Searchable Example', chamber: 'Senate' },
        ],
        trades: [
          {
            ticker: 'TEST',
            member: 'Alexandra Searchable Example',
            member_key: 'congress:alexandra-searchable-example',
            chamber: 'Senate',
            type: 'purchase',
            amount: '$1,001 - $15,000',
            transaction_date: today,
            disclosure_date: today,
            asset: 'Test asset',
          },
        ],
      }),
    });
  });
  await page.route(/\/data\/executives\.json(?:\?.*)?$/, async route => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ people: [], trades: [] }) });
  });

  await waitForLaunch(page);
  await page.evaluate(() => window.setView?.('market'));
  await page.waitForFunction(() => window.VestraMarket && typeof window.VestraMarket.ensureLoaded === 'function');
  await page.evaluate(() => window.VestraMarket.ensureLoaded());
  const politiciansMode = page.locator('[data-politicians-mode]');
  await expect(politiciansMode).toBeVisible();
  await politiciansMode.tap();
  await expect(page.locator('.politicians-section')).toBeVisible();
  expect(fixtureRequests, 'Politicians search must use the intercepted test feed').toBeGreaterThan(0);

  const search = page.locator('[data-politician-search]');
  await expect(search).toBeVisible();
  await search.fill('alexandra');

  const results = page.locator('[data-politician-search-results]');
  await expect(results).toBeVisible();
  const match = results.locator('[data-politician-search-result="congress:alexandra-searchable-example"]');
  await expect(match).toContainText('Alexandra Searchable Example');
  await match.tap();

  await expect(page.locator('#politicianProfile h3')).toHaveText('Alexandra Searchable Example');
  await expect(page.locator('[data-politician-search]')).toHaveValue('');
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
