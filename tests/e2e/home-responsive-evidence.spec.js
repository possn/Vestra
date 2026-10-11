const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Screenshots and measured layout evidence from the real WebKit DOM, not CSS regexes.
// Each breakpoint gets a clean page so stale width-dependent state cannot leak.
for (const width of [390, 600, 601, 740, 741, 820, 1099, 1100, 1440]) {
  test('editorial Home: responsive composition at ' + width + 'px', async ({page}) => {
    await page.setViewportSize({width,height:900});
    await page.goto('/index.html');
    const home=page.locator('#vestraIntelligenceHome');
    await expect(home).toBeVisible({timeout:20000});
    const result=await page.evaluate(() => {
      const root=document.querySelector('#vestraIntelligenceHome');
      const select=s=>root.querySelector(s);
      const opening=select('.vi-opening');
      const lead=select('.vi-opening .vi-lead');
      const wealth=select('.vi-opening .vi-wealth');
      const priorities=select('.vi-priorities');
      const decisions=select('.vi-priorities .vi-decisions');
      const rect=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,width:r.width,height:r.height};};
      return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
        opening:rect(opening),lead:rect(lead),wealth:rect(wealth),
        priorities:rect(priorities),decisions:rect(decisions),
        openingColumns:getComputedStyle(opening).gridTemplateColumns,
        priorityColumns:getComputedStyle(priorities).gridTemplateColumns,
        primaryActions:decisions.querySelectorAll('.vi-action').length};
    });
    const out=path.join('test-results','visual-evidence','home-responsive');
    fs.mkdirSync(out,{recursive:true});
    fs.writeFileSync(path.join(out,width+'.json'),JSON.stringify(result,null,2));
    await home.screenshot({path:path.join(out,width+'.png'),animations:'disabled'});
    expect(result.documentWidth,'Horizontal overflow at '+width).toBeLessThanOrEqual(width+2);
    expect(result.primaryActions,'Missing decision actions at '+width).toBeGreaterThanOrEqual(3);
    expect(result.lead.width,'Empty editorial lead at '+width).toBeGreaterThan(100);
    if(width<=740){
      expect(result.wealth.y,'Wealth should follow lead on narrow screens').toBeGreaterThanOrEqual(result.lead.y);
      expect(result.decisions.x,'Decisions should align with chapter').toBeGreaterThanOrEqual(result.priorities.x-2);
    }else{
      expect(result.wealth.x,'Wealth should occupy right editorial column').toBeGreaterThan(result.lead.x+20);
    }
  });
}
