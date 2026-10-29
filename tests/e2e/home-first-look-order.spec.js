const {test,expect}=require('@playwright/test');

test('iPhone/WebKit: first look is wealth, barometer, news, horizontal agenda, portfolio', async ({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const home=page.locator('#vestraIntelligenceHome');
 await expect(home).toBeVisible({timeout:20000});
 const report=await home.evaluate(host=>{
  const names=['.vi-wealth','.vi-market-reading','.vi-news-reading','.vi-events-reading','.vi-priorities','.vi-risk-reading'];
  const sections=names.map(selector=>host.querySelector(selector));
  const rail=host.querySelector('.vi-events-reading .vi-editorial-rail');
  const style=getComputedStyle(rail);
  return {
   present:sections.map(Boolean),
   order:sections.map(el=>el?.getBoundingClientRect().top),
   strip:!!host.querySelector('.vi-signal-strip'),
   overflowX:style.overflowX, snap:style.scrollSnapType,
   railWidth:rail.clientWidth,
   tileWidth:rail.querySelector('.vi-editorial-tile')?.getBoundingClientRect().width??0
  };
 });
 expect(report.present).toEqual([true,true,true,true,true,true]);
 for(let i=1;i<report.order.length;i++)
  expect(report.order[i], 'reading order '+i).toBeGreaterThan(report.order[i-1]);
 expect(report.strip).toBe(false);
 const editorial=await home.evaluate(host=>{
  const cards=Array.from(host.querySelectorAll('.vi-canonical-sections > .vi-canonical-card'));
  const heading=host.querySelector('.vi-headline');
  const wealth=host.querySelector('.vi-wealth');
  return {
   cards:cards.map(el=>({radius:getComputedStyle(el).borderTopLeftRadius,shadow:getComputedStyle(el).boxShadow})),
   wealthWidth:wealth.getBoundingClientRect().width,
   leadWidth:host.querySelector('.vi-lead').getBoundingClientRect().width,
   headingFont:parseFloat(getComputedStyle(heading).fontSize),
   headingFamily:getComputedStyle(heading).fontFamily
  };
 });
 expect(editorial.cards).toHaveLength(3);
 for(const card of editorial.cards){
  expect(card.radius).toBe('0px');
  expect(card.shadow).toBe('none');
 }
 expect(editorial.wealthWidth).toBeGreaterThan(editorial.leadWidth*0.8);
 expect(editorial.headingFont).toBeGreaterThan(20);
 expect(editorial.headingFamily).toContain('Georgia');
 const tokens=await home.evaluate(host=>{
  const cs=getComputedStyle(document.documentElement);
  const first=host.querySelector('.vi-canonical-sections > .vi-canonical-card');
  return {
   divider:cs.getPropertyValue('--vestra-editorial-divider-dark').trim(),
   border:getComputedStyle(first).borderBottomColor,
   focus:cs.getPropertyValue('--vestra-editorial-focus-gold').trim()
  };
 });
 expect(tokens.divider).toBe('rgba(200,223,208,.22)');
 expect(tokens.border).toBe('rgba(200, 223, 208, 0.22)');
 expect(tokens.focus).toBe('#d7bc89');
 const directChildren=await home.evaluate(host=>Array.from(host.querySelector('.vi-canonical-sections')?.children||[]).map(el=>
  el.classList.contains('vi-market-reading')?'market':
  el.classList.contains('vi-news-reading')?'news':
  el.classList.contains('vi-events-reading')?'events':'unexpected'));
 expect(directChildren).toEqual(['market','news','events']);
 expect(report.overflowX).toBe('auto');
 expect(report.snap).toContain('x');
 await expect(home.locator('.vi-events-reading .vi-editorial-rail')).toHaveAttribute('tabindex','0');
 await expect(home.locator('.vi-events-reading .vi-editorial-rail')).toHaveAttribute('role','region');
 // Fixture isolates the horizontal interaction from asynchronous calendar feeds.
 const scroll = await home.evaluate(host=>{
  const rail=host.querySelector('.vi-events-reading .vi-editorial-rail');
  rail.replaceChildren();
  for(let i=0;i<3;i++){
   const card=document.createElement('div');
   card.className='vi-editorial-tile';
   card.textContent='Evento de teste '+(i+1);
   rail.appendChild(card);
  }
  const before=rail.scrollLeft;
  const available=rail.scrollWidth-rail.clientWidth;
  rail.scrollTo({left:available,behavior:'instant'});
  return {before,after:rail.scrollLeft,available};
 });
 expect(scroll.available).toBeGreaterThan(0);
 expect(scroll.after).toBeGreaterThan(scroll.before);
 await expect(home.locator('.vi-priorities .vi-action')).toHaveCount(3);
});

test('iPhone: radar follows weekly events instead of opening the Home',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/index.html');
 const home=page.locator('#vestraIntelligenceHome');
 await expect(home).toBeVisible({timeout:20000});
 await expect(home.locator('[data-vi-prebreakout-spotlight]')).toHaveCount(1,{timeout:20000});
 const order=await home.evaluate(host=>{
  const events=host.querySelector('.vi-events-reading');
  const radar=host.querySelector('[data-vi-prebreakout-spotlight]');
  return {after:!!events&&events.nextElementSibling===radar,
          eventsTop:events?.getBoundingClientRect().top,
          radarTop:radar?.getBoundingClientRect().top};
 });
 expect(order.after).toBe(true);
 expect(order.radarTop).toBeGreaterThan(order.eventsTop);
});
