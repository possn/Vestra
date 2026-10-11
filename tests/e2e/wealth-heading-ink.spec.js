const { test, expect } = require('@playwright/test');

// Regressions observed in real iPhone screenshots: dark wealth chapter and
// ivory sources/goal/milestones cards must own distinct Safari text fill.
test('iPhone WebKit: wealth chapter and utility headings retain surface-specific ink', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/index.html');
  await expect(page.locator('#vestraIntelligenceHome')).toBeVisible({timeout:20000});
  await page.locator('#vestraIntelligenceHome [data-vestra-go="dashboard"]').first().click();
  await expect(page.locator('#vestraIntelligenceHome[data-legacy-open="true"]')).toHaveCount(1);
  const result=await page.evaluate(()=>{
    const targets=[
      ['wealth-heading','#v2-wealth-chapter h2','dark'],
      ['wealth-deck','#v2-wealth-chapter p','dark'],
      ['sources-heading','#portfolioSourcesCard .card__title','ivory'],
      ['goal-heading','#goalCard .card__title','ivory'],
      ['milestones-heading','#milestonesCard .card__title','ivory']
    ];
    const rgb=s=>{const m=s.match(/rgba?\(([^)]+)\)/);return m?m[1].split(',').slice(0,3).map(Number):null};
    const brightness=c=>c?(c[0]*.2126+c[1]*.7152+c[2]*.0722):null;
    return targets.map(([name,selector,surface])=>{
      const el=document.querySelector(selector);
      if(!el)return {name,error:'missing'};
      const style=getComputedStyle(el);
      const color=style.webkitTextFillColor||style.color;
      return {name,surface,color,brightness:brightness(rgb(color))};
    });
  });
  for(const item of result){
    expect(item.error,item.name).toBeUndefined();
    expect(item.brightness,item.name+' computed Safari ink').not.toBeNull();
    if(item.surface==='dark')expect(item.brightness,item.name+' needs light ink').toBeGreaterThan(155);
    else expect(item.brightness,item.name+' needs dark ink').toBeLessThan(125);
  }
});
