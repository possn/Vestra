const {test,expect}=require('@playwright/test');

test('iPhone/WebKit: turning evidence opens by touch and survives market-card rerender',async({page})=>{
  await page.addInitScript(()=>{
    const today=new Date().toISOString().slice(0,10);
    const yesterday=new Date(Date.now()-86400000).toISOString().slice(0,10);
    localStorage.setItem('PF_STATE_V6',JSON.stringify({
      settings:{currency:'EUR',workerUrl:'https://example.invalid',autoRefreshQuotes:false},
      assets:[],liabilities:[],transactions:[],bankTransactions:[],dividends:[],divSummaries:[],history:[],
      brokerData:{files:[],events:[],positions:[]},priceHistory:{},fxHistory:{},
    }));
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
  await page.goto('/index.html?vestra2=0');
  await page.waitForFunction(()=>window.__vestraAppHydrated===true);
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
