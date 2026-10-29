const {test,expect}=require('@playwright/test');

test('iPhone/WebKit: dossier editorial layout preserves two-column facts and touch tabs',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.locator('link[href*="vestra-dossier-v2.css"]').evaluate(link => link.sheet ? true : new Promise(resolve => link.addEventListener('load',()=>resolve(true),{once:true})));
 const values=await page.evaluate(()=>{
  // Isolated visual fixture uses the production market-sheet classes and CSS.
  // No market data, decision state or quote engine is mocked.
  const sheet=document.createElement('div');
  sheet.className='market-sheet';
  sheet.style.cssText='position:static;display:block;visibility:visible;';
  sheet.innerHTML='<div class="market-sheet__panel" style="position:static;display:block;width:390px;max-width:100%;"><div class="market-detail-head"><div><h2>Empresa</h2></div><div class="market-detail-actions"><button class="market-close">×</button></div></div><div class="market-metrics"><div class="market-metric">A</div><div class="market-metric">B</div></div><div class="market-tabs"><button class="market-tab">Tese</button><button class="market-tab">Valorização</button><button class="market-tab">Riscos</button></div></div>';
  document.body.append(sheet);
  const metrics=sheet.querySelector('.market-metrics');
  const tabs=sheet.querySelector('.market-tabs');
  const out={
   columns:getComputedStyle(metrics).gridTemplateColumns.split(' ').filter(Boolean).length,
   tabHeight:tabs.querySelector('.market-tab').getBoundingClientRect().height,
   headingFamily:getComputedStyle(sheet.querySelector('h2')).fontFamily,
   tabsOverflow:getComputedStyle(tabs).overflowX,
   tabsLayout:getComputedStyle(tabs).display,
   actions:!!sheet.querySelector('.market-detail-actions')
  };
  sheet.remove();
  return out;
 });
 expect(values.columns).toBe(2);
 expect(values.tabHeight).toBeGreaterThanOrEqual(44);
 expect(values.headingFamily).toContain('Georgia');
 expect(values.tabsOverflow).toBe('visible');
 expect(values.tabsLayout).toBe('grid');
 expect(values.actions).toBe(true);
});
