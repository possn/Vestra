const {test,expect}=require('@playwright/test');
test('iPhone: Opportunity title readable; no giant Small Caps CTA in shortlist',async({page})=>{
  await page.goto('/index.html');
  await page.waitForFunction(()=>typeof window.setView==='function');
  await page.evaluate(()=>window.setView('market'));
  const section=page.locator('#viewMarket .market-section:has(.ux454-opportunity-guide)').first();
  await expect(section).toBeVisible({timeout:20000});
  const title=section.locator('.market-section__head h3');
  await expect(title).toBeVisible();
  const actual=await title.evaluate(el=>{const s=getComputedStyle(el);return {color:s.color,fill:s.webkitTextFillColor};});
  expect(actual.color).toBe('rgb(245, 243, 236)');
  expect(actual.fill).toBe('rgb(245, 243, 236)');
  await expect(section.locator('.vestra-smallcaps-entry')).toHaveCount(0);
});
