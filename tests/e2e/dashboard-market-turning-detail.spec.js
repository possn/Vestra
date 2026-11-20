const {test,expect}=require('@playwright/test');

test('iPhone/WebKit: turning evidence opens by touch and survives market-card rerender',async({page})=>{
  await page.addInitScript(()=>{
    const today=new Date().toISOString().slice(0,10);
    const yesterday=new Date(Date.now()-86400000).toISOString().slice(0,10);
    localStorage.setItem('vestra-market-sentiment-v5',JSON.stringify({ts:Date.now(),data:{
      current:{score:50,trend:50,momentum:50,participation:50,vol:{score:50,current:25},parts:[]},
      previousDay:null,previousWeek:null,
      priceFreshness:{date:today,coverage:7},generatedAt:new Date().toISOString(),
      turningInputs:{date:yesterday,spyDaily:[],creditContext:{observed:false,value:'Sem observação'},
        factors:[
          {name:'VIX',value:'25',bottom:false,top:false},
          {name:'RSI semanal',value:'45',bottom:false,top:false},
          {name:'S&P 500',value:'Estável',bottom:false,top:false},
          {name:'Participação proxy',value:'6/6',bottom:false,top:false},
        ]},
    }}));
  });
  // Isolate the actual companion from other Dashboard refreshers: the user
  // interaction must not depend on loading the entire portfolio application.
  await page.route('**/turning-fixture.html',route=>route.fulfill({
    status:200,contentType:'text/html',body:`<!doctype html><html lang="pt"><head>
      <meta name="viewport" content="width=device-width,initial-scale=1"></head><body>
      <div id="viewDashboard"><div id="dashboardTodayBrief"></div></div>
      <script>window.state={settings:{workerUrl:'https://example.invalid'}};</script>
      <script src="/dashboard-market-sentiment.js?v=2.0-turning-tap"></script>
      </body></html>`,
  }));
  await page.goto('/turning-fixture.html');
  await page.waitForFunction(()=>Boolean(window.VestraDashboardMarketSentiment));
  await page.evaluate(()=>window.VestraDashboardMarketSentiment.load(false));
  const card=page.locator('#vestraMarketSentimentCard');
  const toggle=card.locator('[data-dms-turning-toggle]');
  const evidence=card.locator('#dmsTurningEvidence');
  await expect(toggle).toBeVisible({timeout:15000});
  await expect(toggle).toHaveAttribute('aria-expanded','false');
  await toggle.tap();
  await expect(toggle).toHaveAttribute('aria-expanded','true');
  await expect(evidence).toBeVisible();
  await expect(evidence).toContainText('RSI semanal');
  await page.evaluate(()=>window.VestraDashboardMarketSentiment.render());
  await expect(toggle).toHaveAttribute('aria-expanded','true');
  await expect(evidence).toBeVisible();
  await toggle.tap();
  await expect(toggle).toHaveAttribute('aria-expanded','false');
  await expect(evidence).toBeHidden();
});

test('iPhone/WebKit: full app loads market sentiment CSS before showing the card',async({page})=>{
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(()=>window.__vestraAppHydrated===true);
  await page.getByRole('button',{name:'Abrir barómetro de mercado'}).click();
  const card=page.locator('#vestraMarketSentimentCard');
  await expect(card).toBeVisible({timeout:15000});
  const appearance=await card.evaluate(el=>{
    const s=getComputedStyle(el);
    const needle=el.querySelector('.dms-needle');
    return {background:s.backgroundColor,borderRadius:s.borderRadius,
      needleColor:needle?getComputedStyle(needle).stroke:null,
      preloaded:!!document.querySelector('head > link#vestraDashboardMarketSentimentStyle[rel="stylesheet"]')};
  });
  expect(appearance.preloaded).toBe(true);
  expect(appearance.borderRadius).not.toBe('0px');
  expect(appearance.background).not.toBe('rgba(0, 0, 0, 0)');
  if(appearance.needleColor)expect(appearance.needleColor).not.toBe('rgb(0, 0, 0)');
});
