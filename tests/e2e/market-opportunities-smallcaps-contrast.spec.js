const {test,expect}=require('@playwright/test');
test('Opportunity heading remains readable without giant Small Caps CTA',async({page})=>{
 await page.goto('/index.html');await page.waitForFunction(()=>typeof window.setView==='function');
 await page.evaluate(()=>window.setView('market'));
 const section=page.locator('#viewMarket .market-section:has(.ux454-opportunity-guide)').first();
 await expect(section).toBeVisible({timeout:20000});
 await expect(section.locator('.vestra-smallcaps-entry')).toHaveCount(0);
 const color=await section.locator('.market-section__head h3').evaluate(e=>getComputedStyle(e).color);
 expect(color).toBe('rgb(245, 243, 236)');
});
