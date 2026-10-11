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

test('iPhone WebKit: screenshot-reported headings meet 4.5:1 against their surfaces',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
 await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
 await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
 const report=await page.evaluate(()=>{
  const rgb=s=>{const m=s.match(/rgba?\(([^)]+)\)/);return m?m[1].split(',').slice(0,3).map(Number):null};
  const luminance=v=>v.reduce((total,n,i)=>{const c=n/255;return total+(c<=.04045?c/12.92:Math.pow((c+.055)/1.055,2.4))*[.2126,.7152,.0722][i]},0);
  const checks=[
   ['context title','.vi-context-heading h3',null],
   ['context deck','.vi-context-heading p',null],
   ['quick title','#dashboardQuickRecordsCard .card__title','#dashboardQuickRecordsCard'],
   ['quick deck','#dashboardQuickRecordsCard .card__muted','#dashboardQuickRecordsCard']
  ];
  return checks.map(([name,sel,owner])=>{
   const el=document.querySelector(sel);
   if(!el)return {name,error:'missing heading'};
   const fg=rgb(getComputedStyle(el).webkitTextFillColor||getComputedStyle(el).color);
   // Resolve the actual rendered background from the nearest opaque ancestor.
   // No assumed theme color: a future surface change must be caught in WebKit.
   let surface=owner?document.querySelector(owner):el.parentElement;
   let bg=null;
   while(surface&&!bg){
    const style=getComputedStyle(surface), raw=style.backgroundColor;
    const alpha=raw.startsWith('rgba(')?Number(raw.slice(5,-1).split(',')[3]):1;
    if(alpha>=0.99)bg=rgb(raw);
    surface=surface.parentElement;
   }
   if(!fg||!bg)return {name,error:'non-rgb surface or ink'};
   const l1=luminance(fg),l2=luminance(bg);
   return {name,contrast:(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05),visible:el.getClientRects().length>0};
  });
 });
 for(const item of report){
  expect(item.error,item.name).toBeUndefined();
  expect(item.visible,item.name+' rendered').toBe(true);
  expect(item.contrast,item.name+' contrast').toBeGreaterThanOrEqual(4.5);
 }
});
