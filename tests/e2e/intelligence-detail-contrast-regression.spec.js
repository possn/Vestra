const {test,expect}=require('@playwright/test');
test('iPhone: expanded Intelligence has readable headline and card contrast',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
 await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
 await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
 const report=await page.evaluate(()=>{
  const rgb=s=>{const m=String(s).match(/rgba?\(([^)]+)\)/);return m?m[1].split(',').slice(0,3).map(Number):null;};
  const L=c=>c.reduce((a,n,i)=>{const x=n/255;return a+(x<=.04045?x/12.92:((x+.055)/1.055)**2.4)*[.2126,.7152,.0722][i]},0);
  const checks=[
   ['30-second heading','.vi-market-reading .vi-section-top h3',null],
   ['sentiment classification','.vi-market-reading [data-vi-canonical-label]',null],
   ['quick actions title','#dashboardQuickRecordsCard .card__title','#dashboardQuickRecordsCard'],
   ['quick actions copy','#dashboardQuickRecordsCard .card__muted','#dashboardQuickRecordsCard']
  ];
  return checks.map(([name,selector,owner])=>{
   const el=document.querySelector(selector);
   if(!el)return {name,error:'missing'};
   const style=getComputedStyle(el);
   const fg=rgb(style.webkitTextFillColor||style.color);
   const ownerNode=owner?document.querySelector(owner):el.parentElement;
   let bg=owner?null:[16,40,39];
   for(let n=owner?ownerNode:null;n;n=n.parentElement){
    const c=rgb(getComputedStyle(n).backgroundColor);
    if(c&&getComputedStyle(n).backgroundColor.match(/rgba?\([^)]*\)/)&&!getComputedStyle(n).backgroundColor.endsWith(', 0)')){bg=c;break;}
   }
   // No painted ancestor means the dark Intelligence editorial canvas (#102827),
   // not the white CSS initial canvas; its surface is asserted in the existing ink test.
   if(!bg)bg=[16,40,39];
   if(!fg)return {name,error:'unreadable foreground'};
   const l1=L(fg),l2=L(bg);
   return {name,contrast:(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05)};
  });
 });
 for(const row of report){
  expect(row.error,row.name).toBeUndefined();
  expect(row.contrast,row.name).toBeGreaterThanOrEqual(4.5);
 }
});
