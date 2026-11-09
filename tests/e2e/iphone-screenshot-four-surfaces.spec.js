const {test,expect}=require('@playwright/test');

test('iPhone/WebKit: four screenshot surfaces keep financial content and readable geometry',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 await page.waitForFunction(()=>typeof window.setView==='function');
 const style=await page.evaluate(()=>{
  const link=[...document.querySelectorAll('link[rel="stylesheet"]')].find(l=>l.href.includes('vestra-iphone-screenshot-repairs.css'));
  return link && link.sheet && [...link.sheet.cssRules].length>0;
 });
 expect(style).toBeTruthy();
 // The P&L pane can be empty in CI. Recreate its actual element structure
 // without changing any financial data or calculations.
 await page.evaluate(()=>window.setView('assets'));
 const portfolio=page.locator('#viewAssets');
 await expect(portfolio).toBeVisible();
 const layout=await page.evaluate(()=>{
  const host=document.querySelector('#equityPnLContent');
  const saved=host.innerHTML;
  host.innerHTML=`<div style="background:linear-gradient(135deg,#059669,#10b981);padding:16px 16px 14px">
    <div>Retorno Total do Portfólio</div>
    <div style="display:flex;align-items:baseline;gap:10px"><div>+20,07%</div><div>+26 346 €</div></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px">
      <div>Investido 131 291 €</div><div>Latente +17 885 €</div>
      <div>Realizado +4 575 €</div><div>Dividendos +3 887 €</div>
    </div><div>529 posições</div></div>
    <div style="border-left:3px solid green"><div style="display:grid;grid-template-columns:1fr auto auto auto;gap:6px">
      <div>O · Realty Income</div><div>PM 51,34 €</div>
      <div>355 €</div><div>+632 €</div></div></div>`;
  const hero=host.firstElementChild;
  const metrics=hero.children[2];
  const position=host.lastElementChild;
  const calc=el=>({columns:getComputedStyle(el).gridTemplateColumns,width:el.getBoundingClientRect().width,scroll:el.scrollWidth});
  const output={metrics:calc(metrics),position:calc(position.firstElementChild),
    parent:calc(host),viewport:document.documentElement.clientWidth};
  host.innerHTML=saved;
  return output;
 });
 expect(layout.metrics.columns.split(' ').length).toBe(2);
 expect(layout.position.columns.split(' ').length).toBe(2);
 expect(layout.parent.scroll).toBeLessThanOrEqual(layout.parent.width+2);
 const ledger=await page.evaluate(()=>{
  const host=document.querySelector('#itemsList');
  const node=document.createElement('div');
  node.className='item';
  node.innerHTML='<div class="item__l"><div class="item__t">Finantia 2</div><div class="item__s">Depósitos</div></div><div class="item__v">100 000 €</div>';
  host.append(node);
  const value={background:getComputedStyle(node).backgroundColor,
    height:node.getBoundingClientRect().height,
    text:getComputedStyle(node.querySelector('.item__v')).color};
  node.remove();
  return value;
 });
 expect(ledger.background).toBe('rgb(20, 47, 43)');
 expect(ledger.text).toBe('rgb(241, 243, 237)');
 expect(ledger.height).toBeLessThan(65);

 await page.evaluate(()=>window.setView('dashboard'));
 const home=page.locator('#vestraIntelligenceHome .vi-market-reading');
 await expect(home).toBeVisible();
 const sentiment=await home.evaluate(root=>{
  const orb=root.querySelector('.vi-sentiment-orb').getBoundingClientRect();
  const label=root.querySelector('.vi-market-reading-body h4').getBoundingClientRect();
  return {orbRight:orb.right,labelLeft:label.left};
 });
 expect(sentiment.labelLeft).toBeGreaterThanOrEqual(sentiment.orbRight+12);

 await page.evaluate(()=>window.setView('market'));
 const market=page.locator('#viewMarket');
 await expect(market).toBeVisible();
 const chip=await market.evaluate(root=>{
  const node=document.createElement('button');
  node.dataset.vestraLens='smallcap_breakout';
  node.textContent='Small Caps';
  root.append(node);
  const colors=()=>{
   const s=getComputedStyle(node);
   return {bg:s.backgroundColor,ink:s.webkitTextFillColor||s.color,height:node.getBoundingClientRect().height};
  };
  const inactive=colors();
  node.classList.add('is-active');node.setAttribute('aria-pressed','true');
  const active=colors();
  node.remove();
  return {inactive,active};
 });
 expect(chip.inactive.ink).toBe('rgb(24, 62, 59)');
 expect(chip.active.ink).toBe('rgb(255, 255, 255)');
 expect(chip.inactive.height).toBeGreaterThanOrEqual(44);
});
