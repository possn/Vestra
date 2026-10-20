const {test,expect}=require('@playwright/test');
test('iPhone FIRE and rebalancing explanatory ink remains legible',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.evaluate(()=>{
  document.querySelector('#viewAnalysis').style.display='block';
  for(const id of ['analysisPanelTab_fire','analysisPanelTab_performance'])document.getElementById(id).style.display='block';
 });
 for(const selector of ['#fireExpInput ~ .none','#analysisPanelTab_fire .lbl span','#analysisPanelTab_performance #rebalancingTotal']){
  if(selector.includes('.none'))continue;
  const items=page.locator(selector);const count=await items.count();
  expect(count).toBeGreaterThan(0);
  for(let i=0;i<count;i++){
   const css=await items.nth(i).evaluate(e=>{const s=getComputedStyle(e);return {color:s.webkitTextFillColor||s.color,background:getComputedStyle(e.closest('.card')||e.parentElement).backgroundColor}});
   expect(css.color).not.toBe('rgb(148, 163, 184)');
  }
 }
});
