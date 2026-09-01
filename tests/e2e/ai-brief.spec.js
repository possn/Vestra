const { test, expect } = require('@playwright/test');

const WORKER = 'https://delicate-bar-cc80.pedrossnunes.workers.dev';

test('iPhone/WebKit: dossier AI brief uses Worker contract and preserves evidence-only UI', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  let requestBody = null;
  let sessionHeader = '';
  await page.route(`${WORKER}/ai-brief`, async route => {
    const req = route.request();
    requestBody = req.postDataJSON();
    sessionHeader = req.headers()['x-vestra-session'] || '';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: { 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({
        brief: {
          thesis: 'Tese baseada apenas na evidência Vestra disponível.',
          why_now: 'Estimativas e recuperação justificam acompanhamento.',
          risks: ['Cobertura incompleta continua a limitar a confiança.'],
          catalysts: ['Melhoria sustentada das estimativas.'],
          what_changes_the_thesis: 'Deterioração material de crescimento ou cash flow.'
        },
        model: '@cf/meta/llama-3.3-70b-instruct-fp8-fast',
        cached: false
      })
    });
  });
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ quotes: [], news: [], lists: [] }) });
  });

  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));

  const search = page.locator('#marketSearch');
  await search.fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({ timeout: 15_000 });
  await row.click();

  const sheet = page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  const card = sheet.locator('.ai459-card');
  await expect(card).toBeVisible({ timeout: 15_000 });
  await expect(card.locator('.ai459-status')).toContainText('Brief local');

  await card.locator('[data-ai459-run]').click();
  await expect(card.locator('.ai459-status')).toHaveText('Vestra AI · evidência atual');
  await expect(card.locator('.ai459-content')).toContainText('Tese baseada apenas na evidência Vestra disponível.');
  await expect(card.locator('.ai459-content')).toContainText('Cobertura incompleta continua a limitar a confiança.');

  expect(requestBody?.type).toBe('company_brief');
  expect(requestBody?.version).toBe('1');
  expect(requestBody?.data?.ticker).toBe('MSFT');
  expect(requestBody?.data).toHaveProperty('score');
  expect(requestBody?.data).toHaveProperty('confidence');
  expect(sessionHeader).toMatch(/^[A-Za-z0-9._-]{8,128}$/);
  expect(pageErrors, `Browser page errors: ${pageErrors.join(' | ')}`).toEqual([]);
});
