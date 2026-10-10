const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Preserve real rendered evidence after a green WebKit run as well as failures.
test('iPhone/WebKit: Intelligence Home responsive evidence at phone and desktop widths', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({ timeout: 20000 });
  const out = path.join('test-results', 'visual-evidence');
  fs.mkdirSync(out, { recursive: true });

  for (const viewport of [
    { name: 'iphone-390', width: 390, height: 844 },
    { name: 'desktop-1280', width: 1280, height: 800 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.waitForTimeout(350);
    const home = page.locator('#vestraIntelligenceHome');
    const actions = home.locator('.vi-priorities .vi-action');
    await expect(actions).toHaveCount(3);
    await expect(actions.first()).toBeVisible();
    const measures = await page.evaluate(() => {
      const host = document.getElementById('vestraIntelligenceHome');
      const rows = Array.from(host.querySelectorAll('.vi-priorities .vi-action'));
      const rectangles = rows.map(e => e.getBoundingClientRect());
      return {
        width: document.documentElement.clientWidth,
        hostWidth: host.getBoundingClientRect().width,
        documentWidth: document.documentElement.scrollWidth,
        hostScrollWidth: host.scrollWidth,
        hostClientWidth: host.clientWidth,
        lefts: rectangles.map(r => Math.round(r.left)),
        tops: rectangles.map(r => Math.round(r.top)),
        overflow: rows.some(e => e.scrollWidth > e.clientWidth + 3),
        offenders: Array.from(document.querySelectorAll('body *'))
          .filter(e => {
            const style = getComputedStyle(e);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const r = e.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && (r.right > innerWidth + 4 || r.left < -4);
          })
          .sort((a,b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right)
          .slice(0,20)
          .map(e => {
            const r=e.getBoundingClientRect();
            return { tag:e.tagName, id:e.id, className:String(e.className).slice(0,120),
              left:Math.round(r.left), right:Math.round(r.right), width:Math.round(r.width) };
          }),
      };
    });
    fs.writeFileSync(path.join(out, 'layout-' + viewport.name + '.json'), JSON.stringify(measures, null, 2));
    await home.screenshot({ path: path.join(out, 'intelligence-' + viewport.name + '.png'), animations: 'disabled' });
    await page.screenshot({ path: path.join(out, 'page-' + viewport.name + '.png'), fullPage: true, animations: 'disabled' });
    expect(measures.documentWidth).toBeLessThanOrEqual(viewport.width + 3);
    expect(measures.hostScrollWidth).toBeLessThanOrEqual(measures.hostClientWidth + 3);
    expect(measures.overflow).toBe(false);
    if (viewport.width < 600) {
      expect(measures.tops[1]).toBeGreaterThan(measures.tops[0]);
      expect(measures.tops[2]).toBeGreaterThan(measures.tops[1]);
    } else {
      expect(Math.abs(measures.tops[1] - measures.tops[0])).toBeLessThan(8);
      expect(Math.abs(measures.tops[2] - measures.tops[0])).toBeLessThan(8);
    }
  }
  expect(errors).toEqual([]);
});
