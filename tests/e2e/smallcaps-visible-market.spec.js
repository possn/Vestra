const {test,expect}=require('@playwright/test');
test('iPhone: Small Caps lens adjacent to Pré-breakout, without inventory',async({page})=>{
 await page.goto('/index.html'); await page.waitForFunction(()=>typeof window.setView==='function');
 await page.evaluate(()=>window.setView('market'));
 const section=page.locator('#viewMarket .market-section:has(.ux454-opportunity-guide)').first();
 await expect(section).toBeVisible({timeout:20000});
 const chip=section.locator('[data-smallcap-prebreakout-lens]');
 await expect(chip).toBeVisible({timeout:20000});
 await expect(chip).toHaveText('Small Caps');
 await chip.click();
 await expect(chip).toHaveAttribute('aria-pressed','true');
 await expect(section.locator('.market-section__head h3')).toContainText('Small Caps');
 await expect(section).toContainText('Sem small caps em pré-breakout');
 await expect(page.locator('#marketPrimary .market-smallcaps')).toHaveCount(0);
});
