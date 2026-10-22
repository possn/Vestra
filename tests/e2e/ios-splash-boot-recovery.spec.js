const {test, expect}=require('@playwright/test');
test('iPhone splash mark is inline and startup recovery never clears storage',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const mark=page.locator('#appLoadingOverlay .vestra-splash__mark svg');
 await expect(mark).toHaveCount(1);
 expect(await mark.locator('path').count()).toBe(2);
 const source=await page.locator('script').evaluateAll(nodes=>nodes.map(n=>n.textContent||'').join('\n'));
 expect(source).toContain('Last-resort iOS startup release');
 expect(source).not.toContain('indexedDB.deleteDatabase');
 await expect(page.locator('#appLoadingOverlay')).toBeHidden({timeout:9000});
});
