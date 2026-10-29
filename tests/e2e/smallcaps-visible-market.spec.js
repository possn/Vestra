const {test,expect}=require('@playwright/test');
test('iPhone: Small Caps opens a closable research engine, not an inventory',async({page})=>{
  await page.goto('/index.html');
  await page.waitForFunction(()=>typeof window.setView==='function');
  await page.evaluate(()=>window.setView('market'));
  const tab=page.locator('#viewMarket [data-market-tool="smallcap-breakout"]');
  await expect(tab).toBeVisible();await tab.scrollIntoViewIfNeeded();await tab.click();
  const sheet=page.locator('#marketSheet');
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.market-smallcap-breakout')).toBeVisible();
  await expect(sheet).toContainText('Sem sinais validados');
  await expect(sheet.locator('.market-smallcap-breakout .market-row')).toHaveCount(0);
  await sheet.locator('.market-smallcap-breakout [data-market-close]').click();
  await expect(sheet).toBeHidden();
});
