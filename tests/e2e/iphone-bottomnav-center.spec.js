const {test,expect}=require('@playwright/test');
test('iPhone active bottom navigation indicator shares center with its button',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('#navMarket').click();
 const values=await page.locator('#navMarket').evaluate(btn=>{
   const icon=btn.querySelector('.navico'),nav=btn.closest('.bottomnav');
   const a=btn.getBoundingClientRect(),b=icon.getBoundingClientRect(),n=nav.getBoundingClientRect();
   return {delta:Math.abs((a.left+a.right)/2-(b.left+b.right)/2),
     navLeft:n.left,navRight:n.right,width:innerWidth,
     iconTransform:getComputedStyle(icon).transform};
 });
 expect(values.delta).toBeLessThanOrEqual(1);
 expect(values.navLeft).toBeGreaterThanOrEqual(-1);
 expect(values.navRight).toBeLessThanOrEqual(values.width+1);
 expect(values.iconTransform).toBe('none');
});
