const { test, expect } = require('@playwright/test');

test('iPhone/WebKit: editorial Home leads with reading, decisions and verified context', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => document.getElementById('vestraIntelligenceHome')?.dataset.vestraIntelligence === '1');
  const home = page.locator('#vestraIntelligenceHome');
  await expect(home).toBeVisible();
  const layout = await home.evaluate(el => {
    const shell = el.querySelector('.vi-shell');
    const names = ['.vi-opening', '.vi-priorities', '.vi-context-chapter'];
    const items = names.map(selector => shell.querySelector(selector));
    return {
      ordered: items.every(Boolean) && items.every((node, i) => i === 0 || (items[i - 1].compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0),
      decisions: el.querySelectorAll('.vi-home-overview button.vi-action').length,
      duplicateStrip: el.querySelectorAll('.vi-daily-snapshot').length,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      fontSize: parseFloat(getComputedStyle(el.querySelector('.vi-deck')).fontSize),
    };
  });
  expect(layout.ordered).toBe(true);
  expect(layout.decisions).toBe(3);
  expect(layout.duplicateStrip).toBe(0);
  expect(layout.overflow).toBeLessThanOrEqual(2);
  expect(layout.fontSize).toBeGreaterThanOrEqual(15);
});
