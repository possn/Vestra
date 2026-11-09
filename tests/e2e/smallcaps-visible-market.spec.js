const {test,expect}=require('@playwright/test');
test('Small Caps is a compact pre-breakout lens with no inventory',async({page})=>{
 await page.goto('/index.html');await page.waitForFunction(()=>typeof window.setView==='function');
 await page.evaluate(()=>window.setView('market'));
 const chip=page.locator('#viewMarket [data-vestra-lens="smallcap_breakout"]');
 await expect(chip).toBeVisible({timeout:20000});
 await chip.click();
 await expect(chip).toHaveAttribute('aria-pressed','true');
 const age=page.locator('#marketPrimary .market-section:has(.ux454-opportunity-guide) .market-data-age');
 await expect(age).toContainText('OHLCV');
 await expect(age).not.toContainText('Dados ');
 await expect(page.locator('#marketPrimary')).toContainText('Small Caps · Pré-breakout');
 await expect(page.locator('#marketPrimary')).toContainText('Sem small caps em pré-breakout elegíveis');
 await expect(page.locator('#marketPrimary .market-smallcaps')).toHaveCount(0);
 await expect(page.locator('#viewMarket [data-market-mode="smallcaps"]')).toHaveCount(0);
 // Leaving this research lens must restore canonical stock-index provenance.
 await page.locator('#marketPrimary .market-section:has(.ux454-opportunity-guide) [data-vestra-lens="all"]').click();
 await expect(age).not.toContainText('OHLCV');
});
