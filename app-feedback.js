/* Vestra contextual help + toast feedback v1.0. */
(() => {
  'use strict';

  const TIPS = {
    compound:{title:'O que é o Juro Composto?',body:`O juro composto é o fenómeno em que os juros gerados também geram juros.<br><br><b>Exemplo:</b> 10.000€ a 5%/ano:<br>• Juro simples: +500€/ano → 15.000€ em 10 anos<br>• Juro composto: +500€ no ano 1, +525€ no ano 2… → 16.289€ em 10 anos<br><br>A diferença cresce exponencialmente com o tempo.`},
    yieldPct:{title:'O que é o Yield?',body:`O <b>yield</b> (rendimento) é a percentagem de retorno anual de um ativo.<br><br><b>Exemplos:</b><br>• ETF distribuidor: dividendos anuais / preço<br>• Certificados de aforro: taxa definida pelo Estado<br>• Depósito a prazo: taxa acordada com o banco<br>• Imobiliário: renda mensal / valor do imóvel × 12<br><br>Na app, o rendimento base projectado usa o rendimento configurado ou observado de cada ativo.`},
    passiveIncome:{title:'Rendimento Passivo',body:`O <b>rendimento passivo</b> é o dinheiro que a carteira gera sem trabalho ativo.<br><br><b>Fontes:</b><br>• Dividendos<br>• Juros<br>• Rendas<br><br>A Vestra distingue <b>projectado</b> e <b>real</b>, e mostra o mesmo rendimento por diferentes ângulos no Dashboard, no objetivo mensal e em Dividendos.`},
    fire:{title:'O que é FIRE?',body:`<b>FIRE</b> = Financial Independence, Retire Early.<br><br>O objetivo é acumular capital suficiente para que os rendimentos da carteira cubram as despesas, tornando o trabalho opcional.<br><br><b>Regra dos 4%:</b> como referência simples, 25× as despesas anuais corresponde a uma retirada inicial de 4%/ano.`},
    weightedYield:{title:'Yield Médio Ponderado',body:`O <b>yield médio ponderado</b> é a taxa média da carteira tendo em conta o peso de cada ativo.<br><br>É mais informativo do que uma média simples porque uma posição grande pesa mais no resultado do que uma posição pequena.`},
    savingsRate:{title:'Taxa de Poupança',body:`A <b>taxa de poupança</b> é a percentagem do rendimento que não é gasta.<br><br><b>Fórmula:</b> (Entradas − Saídas) / Entradas × 100.`},
    netWorth:{title:'Património Líquido',body:`O <b>património líquido</b> é a diferença entre tudo o que tens e tudo o que deves.<br><br><b>Fórmula:</b> Ativos − Passivos.`},
    diversification:{title:'Diversificação',body:`A <b>diversificação</b> distribui o capital por diferentes riscos.<br><br>Pode ser geográfica, por classe de ativo, moeda, setor e ao longo do tempo.`},
    dividends:{title:'Dividendos YTD',body:`<b>YTD</b> (Year To Date) é o total de dividendos registados desde o início do ano corrente.<br><br>Podes registá-los manualmente ou através das importações suportadas pela app.`},
    divSummary:{title:'Resumo Anual de Dividendos',body:`O <b>resumo anual</b> permite introduzir totais anuais de dividendos.<br><br><b>Bruto</b> é antes de impostos, <b>retenção</b> é o imposto retido e <b>líquido</b> é o recebido. Este histórico ajuda a validar o rendimento passivo real.`},
    forecast:{title:'Previsão de retorno',body:`A <b>previsão</b> estima o valor futuro com base nos pressupostos de retorno da carteira e, quando existe histórico suficiente, em métricas de performance observada.<br><br>É uma estimativa e não uma garantia de retorno.`},
    compare:{title:'Comparação de Períodos',body:`Compara a evolução do património entre períodos.<br><br><b>MoM</b> = mês contra mês. <b>YoY</b> = ano contra ano.<br><br>O histórico depende dos snapshots guardados na app.`},
    twr:{title:'O que é TWR?',body:`<b>TWR</b> (Time-Weighted Return) mede o desempenho dos investimentos reduzindo o efeito do momento em que entram ou saem fluxos de dinheiro.<br><br>É útil para comparar a performance da carteira com benchmarks de forma mais consistente.`}
  };

  function openTip(key){
    const tip=TIPS[key]; if(!tip) return;
    const el=document.getElementById('tipModal'), titleEl=document.getElementById('tipTitle'), bodyEl=document.getElementById('tipBody');
    if(!el||!titleEl||!bodyEl) return;
    titleEl.textContent=tip.title;
    bodyEl.innerHTML=tip.body;
    if(typeof window.openModal==='function') window.openModal('tipModal');
    else { el.hidden=false; el.setAttribute('aria-hidden','false'); }
  }

  function toast(msg,duration=3000){
    let el=document.getElementById('toastEl');
    if(!el){el=document.createElement('div');el.id='toastEl';el.setAttribute('role','status');el.setAttribute('aria-live','polite');el.setAttribute('aria-atomic','true');document.body.appendChild(el);}
    el.textContent=msg;el.classList.add('toast--show');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('toast--show'),duration);
  }

  window.VestraFeedback=Object.freeze({TIPS,openTip,toast});
  window.openTip=openTip;
  window.toast=toast;
})();
