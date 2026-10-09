const { test, expect } = require('@playwright/test');

// Compare computed foreground with the actual opaque card it belongs to.
function contrast(text, background) {
  const rgb = value => (value.match(/rgba?\(([^)]+)\)/)?.[1] || '').split(',').slice(0, 3).map(Number);
  const light = channels => channels.map(n => n / 255).map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4)
    .reduce((sum, n, index) => sum + n * [.2126, .7152, .0722][index], 0);
  const a = light(rgb(text)), b = light(rgb(background));
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
}

test('iPhone/WebKit: portfolio summary foreground remains readable on both surface types', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('assets'));
  await expect(page.locator('#viewAssets .portfolio-glance')).toBeVisible();
  const colors = await page.evaluate(() => {
    const css = selector => getComputedStyle(document.querySelector(selector));
    return {
      mainText: css('#viewAssets .portfolio-glance__main strong').color,
      mainCard: css('#viewAssets .portfolio-glance__main').backgroundColor,
      statText: css('#viewAssets .portfolio-glance__stat strong').color,
      statCard: css('#viewAssets .portfolio-glance__stat').backgroundColor,
      incomeText: css('#viewAssets .portfolio-income-strip small').color,
      incomeCard: css('#viewAssets .portfolio-income-strip>div').backgroundColor,
    };
  });
  expect(contrast(colors.mainText, colors.mainCard), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(colors.statText, colors.statCard), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(colors.incomeText, colors.incomeCard), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
});

test('iPhone/WebKit: Market analysis panel title has readable ink on light card', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  const panel = page.locator('#viewMarket .market-analysis-tools');
  await expect(panel).toBeVisible({ timeout: 15000 });
  const colors = await page.evaluate(() => {
    const panel = document.querySelector('#viewMarket .market-analysis-tools');
    return {
      title: getComputedStyle(panel.querySelector('.market-analysis-tools__head strong')).color,
      card: getComputedStyle(panel).backgroundColor,
    };
  });
  expect(contrast(colors.title, colors.card), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
});
