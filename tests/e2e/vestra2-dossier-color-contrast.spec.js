const { test, expect } = require('@playwright/test');

const ratio = (a, b) => {
  const rgb = value => (value.match(/rgba?\(([^)]+)\)/)?.[1] || '').split(',').slice(0, 3).map(Number);
  const lum = value => rgb(value).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
    .reduce((sum, value, i) => sum + value * [.2126, .7152, .0722][i], 0);
  const x = lum(a), y = lum(b);
  return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
};

test('iPhone/WebKit: company research sheet retains legible dark-surface heading and tabs', async ({ page }) => {
  await page.route('https://query1.finance.yahoo.com/v1/finance/search**', async route =>
    route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({quotes:[],news:[],lists:[]})}));
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof window.setView === 'function');
  await page.evaluate(() => window.setView('market'));
  await page.locator('#marketSearch').fill('MSFT');
  const row = page.locator('.market-row[data-market-ticker="MSFT"]').first();
  await expect(row).toBeVisible({timeout:15000});
  await row.click();
  await expect(page.locator('#marketSheet .market-sheet__panel')).toBeVisible();

  const colors = await page.evaluate(() => {
    const panel = document.querySelector('#marketSheet .market-sheet__panel');
    const tab = document.querySelector('#marketSheet .market-tab:not(.is-active)');
    const css = el => getComputedStyle(el);
    return {
      panelInk: css(panel).color,
      panelBackground: css(panel).backgroundColor,
      tabInk: tab && css(tab).color,
      tabBackground: tab && css(tab).backgroundColor,
    };
  });
  expect(ratio(colors.panelInk, colors.panelBackground), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
  if (colors.tabInk && colors.tabBackground)
    expect(ratio(colors.tabInk, colors.tabBackground), JSON.stringify(colors)).toBeGreaterThanOrEqual(4.5);
});
