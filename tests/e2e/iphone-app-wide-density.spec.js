const { test, expect } = require('@playwright/test');
test('iPhone app-wide compact CSS contract', async ({page}) => {
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const css=await page.evaluate(()=>{
  const host=document.createElement('div'); host.className='view';host.innerHTML='<div class="card"><div class="card__title">Teste</div></div>';document.querySelector('.main').appendChild(host);
  const card=host.querySelector('.card'),heading=host.querySelector('.card__title');
  const metrics={padding:parseFloat(getComputedStyle(card).paddingTop),heading:parseFloat(getComputedStyle(heading).fontSize)};host.remove();return metrics;
 });
 expect(css.padding).toBeLessThanOrEqual(14);
 expect(css.heading).toBeLessThanOrEqual(18);
});