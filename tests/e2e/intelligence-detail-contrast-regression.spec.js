const {test,expect}=require('@playwright/test');
test('iPhone: expanded Intelligence has readable headline and card contrast',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
 await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
 await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
 const report=await page.evaluate(()=>{
  const rgb=s=>{const m=String(s).match(/rgba?\\(([^)]+)\\)/);return m?m[1].split(',').slice(0,3).map(Number):null;};
  const L=c=>c.reduce((a,n,i)=>{const x=n/255;return a+(x<=.04045?x/12.92:((x+.055)/1.055)**2.4)*[.2126,.7152,.0722][i]},0);
  const backgrounds=['#viewDashboard','#dashboardQuickRecordsCard','.v2-home-stage.card.hero'];
  const checks=[
   ['30-second heading','.vi-context-heading h3',null],
   ['30-second explanation','.vi-context-heading p',null],
   ['quick actions title','#dashboardQuickRecordsCard .card__title','#dashboardQuickRecordsCard'],
   ['quick actions copy','#dashboardQuickRecordsCard .card__muted','#dashboardQuickRecordsCard']
  ];
  return checks.map(([name,selector,owner])=>{
   const el=document.querySelector(selector);
   if(!el)return {name,error:'missing'};
   const style=getComputedStyle(el);
   const fg=rgb(style.webkitTextFillColor||style.color);
   const ownerNode=owner?document.querySelector(owner):el.parentElement;
   let bg=null;
   for(let n=ownerNode;n;n=n.parentElement){
    const c=rgb(getComputedStyle(n).backgroundColor);
    if(c&&getComputedStyle(n).backgroundColor.match(/rgba?\\([^)]*\\)/)&&!getComputedStyle(n).backgroundColor.endsWith(', 0)')){bg=c;break;}
   }
   // Transparent descendants reveal the CSS canvas. Use the document canvas
   // (white by CSS painting rules) if no ancestor defines a solid background.
   if(!bg)bg=[255,255,255];
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
