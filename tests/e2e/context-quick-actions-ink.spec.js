const {test,expect}=require('@playwright/test');
test('iPhone WebKit: context on charcoal and quick actions on ivory are legible',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
 await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
 await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
 const evidence=await page.evaluate(()=>{
  const specs=[
   ['context title','.vi-context-heading h3','light'],
   ['context deck','.vi-context-heading p','light'],
   ['quick actions','#dashboardQuickRecordsCard .card__title','dark'],
   ['quick explanation','#dashboardQuickRecordsCard .card__muted','dark']
  ];
  return specs.map(([name,sel,expected])=>{
   const el=document.querySelector(sel);
   if(!el)return {name,expected,missing:true};
   const s=getComputedStyle(el),ink=s.webkitTextFillColor||s.color;
   const match=ink.match(/rgba?\(([^)]+)\)/);
   const rgb=match?match[1].split(',').slice(0,3).map(Number):[];
   const brightness=rgb.length===3?rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722:null;
   return {name,expected,ink,brightness};
  });
 });
 for(const row of evidence){
  expect(row.missing,row.name).not.toBe(true);
  expect(row.brightness,row.name).not.toBeNull();
  if(row.expected==='light')expect(row.brightness,row.name).toBeGreaterThan(155);
  else expect(row.brightness,row.name).toBeLessThan(125);
 }
});
