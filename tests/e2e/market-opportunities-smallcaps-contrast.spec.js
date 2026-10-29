const {test,expect}=require('@playwright/test');

test('iPhone opportunities: readable heading and Small Caps entry from scroll depth',async({page})=>{
  await page.goto('/index.html');
  await page.waitForFunction(()=>typeof window.setView==='function');
  await page.evaluate(()=>window.setView('market'));
  const section=page.locator('#viewMarket .market-section:has(.ux454-opportunity-guide)').first();
  await expect(section).toBeVisible({timeout:20000});
  const title=section.locator('.market-section__head h3');
  await expect(title).toBeVisible();
  const actual=await title.evaluate(el=>{
    const style=getComputedStyle(el),bg=getComputedStyle(el.closest('.market-section')).backgroundColor;
    return {color:style.color,fill:style.webkitTextFillColor,bg};
  });
  expect(actual.color).toBe('rgb(245, 243, 236)');
  expect(actual.fill).toBe('rgb(245, 243, 236)');
  const entry=section.locator('.vestra-smallcaps-entry');
  await expect(entry).toBeVisible();
  await entry.click();
  await expect(page.locator('#marketPrimary .market-smallcaps')).toBeVisible({timeout:20000});
  await expect(page.locator('#marketPrimary .market-smallcaps__disclaimer').first()).toContainText('não por probabilidade de subida');
});
