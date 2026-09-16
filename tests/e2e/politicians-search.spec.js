const { test, expect } = require('@playwright/test');

async function waitForLaunch(page) {
  await page.goto('/index.html');
  await expect(page.locator('#appLoadingOverlay')).toBeHidden({ timeout: 10_000 });
}

test('iPhone/WebKit: politician picker supports live name search', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.route('**/data/politicians.json?*', async route => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        schema_version: 2,
        generated_at: '2026-09-16T10:00:00Z',
        source_last_updated: '2026-09-16',
        newest_disclosure: '2026-09-10',
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
            transaction_date: '2026-09-01',
            disclosure_date: '2026-09-10',
            asset: 'Test asset',
          },
        ],
      }),
    });
  });
  await page.route('**/data/executives.json?*', async route => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ people: [], trades: [] }) });
  });

  await waitForLaunch(page);
  await page.locator('[data-politicians-mode]').tap();
  await expect(page.locator('.politicians-section')).toBeVisible();

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
