const {test,expect}=require('@playwright/test');
test('iPhone/WebKit: explicit Small Caps tab displays real index cohort',async({page})=>{
  await page.goto('/index.html');
  await page.waitForFunction(()=>typeof window.setView==='function');
  await page.evaluate(()=>window.setView('market'));
  const tab=page.locator('#viewMarket .market-mode-grid [data-market-mode="smallcaps"]');
  await expect(tab).toBeVisible();
  await expect(tab).toBeInViewport();
  await tab.click();
  await expect(page.locator('#marketPrimary .market-smallcaps')).toBeVisible({timeout:20000});
  await expect(page.locator('#marketPrimary .market-smallcaps__disclaimer')).toContainText('não por probabilidade de subida');
  await expect(page.locator('#marketPrimary .market-smallcaps')).toContainText('100 M a 2 000 M USD');
});
