/* Vestra contextual help + toast feedback v1.1 — extracted without product-copy changes. */
(() => {
  'use strict';

  const TIPS = {
    compound: {
      title: "O que é o Juro Composto?",
      body: `O juro composto é o fenómeno em que os juros gerados também geram juros.<br><br>
<b>Exemplo:</b> 10.000€ a 5%/ano:<br>
• Juro simples: +500€/ano → 15.000€ em 10 anos<br>
• Juro composto: +500€ no ano 1, +525€ no ano 2… → 16.289€ em 10 anos<br><br>
A diferença cresce exponencialmente com o tempo — por isso Einstein terá dito que o juro composto é "a oitava maravilha do mundo".`
    },
    yieldPct: {
      title: "O que é o Yield?",
      body: `O <b>yield</b> (rendimento) é a percentagem de retorno anual de um ativo.<br><br>
<b>Exemplos:</b><br>
• ETF VWCE: yield dividendo ≈ 1.5–2%/ano<br>
• Certificados de aforro: taxa fixa definida pelo Estado<br>
• Depósito a prazo: taxa acordada com o banco<br>
• Imobiliário: renda mensal / valor do imóvel × 12<br><br>
Na app, o rendimento base projectado da carteira é calculado automaticamente com base no rendimento configurado em cada ativo ou, na falta dele, pelos pressupostos por classe.`
    },
    passiveIncome: {
      title: "Rendimento Passivo",
      body: `O <b>rendimento passivo</b> é o dinheiro que a tua carteira gera automaticamente, sem trabalho ativo.<br><br>
<b>Fontes:</b><br>
• Dividendos de ações/ETFs<br>
• Juros de depósitos e obrigações<br>
• Rendas de imóveis<br>
• Juros de PPR e fundos<br><br>
A app calcula dois valores:<br>
• <b>Projectado</b>: valor atual × yield configurado/observado de cada ativo<br>
• <b>Real</b>: rendimento efetivamente registado/TTM, usado para histórico e validação<br><br>
<b>Onde vês isto na app</b> — é o mesmo número, mostrado de ângulos diferentes:<br>
• Esta barra e o cartão "Rend. passivo/mês": o total actual, todas as fontes<br>
• Cartão "Objetivo de rendimento": o mesmo total, comparado com a tua meta mensal<br>
• Separador <b>Dividendos</b>: só a fatia de acções/ETFs, com histórico e detalhe por posição<br><br>
Não são números diferentes — é o mesmo rendimento, visto no todo (aqui) ou em detalhe (Dividendos).`
    },
    fire: {
      title: "O que é FIRE?",
      body: `<b>FIRE</b> = Financial Independence, Retire Early.<br><br>
O objetivo é acumular capital suficiente para que os rendimentos passivos cubram as despesas, tornando o trabalho opcional.<br><br>
<b>Regra dos 4% (SWR):</b><br>
Se retirares 4% do teu portfólio por ano, historicamente o capital dura mais de 30 anos. Isso significa que precisas de 25× as tuas despesas anuais.<br><br>
<b>Exemplo:</b> Despesas de 2.000€/mês = 24.000€/ano → precisas de 600.000€ investidos.`
    },
    weightedYield: {
      title: "Yield Médio Ponderado",
      body: `O <b>yield médio ponderado</b> é a taxa de retorno média da carteira, tendo em conta o peso de cada ativo.<br><br>
<b>Exemplo:</b><br>
• 80.000€ em ETFs com 5% → contribui 4.000€/ano<br>
• 20.000€ em depósitos com 3% → contribui 600€/ano<br>
• Total: 100.000€ → 4.600€/ano → rendimento base ponderado = 4,6%<br><br>
É mais preciso do que fazer a média simples dos yields porque tem em conta o tamanho de cada posição.`
    },
    savingsRate: {
      title: "Taxa de Poupança",
      body: `A <b>taxa de poupança</b> é a percentagem do rendimento que guardas (não gastas).<br><br>
<b>Fórmula:</b> (Entradas − Saídas) / Entradas × 100<br><br>
<b>Referências:</b><br>
• < 10%: baixa — difícil acumular capital<br>
• 10–20%: razoável<br>
• 20–40%: boa — acelera a independência financeira<br>
• > 50%: excelente — caminho rápido para FIRE<br><br>
Com 50% de taxa de poupança, podes reformar-te em ~17 anos (partindo do zero).`
    },
    netWorth: {
      title: "Património Líquido",
      body: `O <b>património líquido</b> (net worth) é a diferença entre tudo o que tens e tudo o que deves.<br><br>
<b>Fórmula:</b> Ativos − Passivos<br><br>
<b>Ativos:</b> imóveis, ações, depósitos, cripto, ouro…<br>
<b>Passivos:</b> crédito habitação, crédito pessoal, cartões…<br><br>
É a métrica mais importante para medir a saúde financeira. O objetivo é aumentá-lo todos os meses através de poupança e valorização dos ativos.`
    },
    diversification: {
      title: "Diversificação",
      body: `A <b>diversificação</b> consiste em distribuir o capital por diferentes tipos de ativos para reduzir o risco.<br><br>
<b>Princípio:</b> "Não coloques todos os ovos no mesmo cesto."<br><br>
<b>Dimensões de diversificação:</b><br>
• <b>Geográfica:</b> Portugal, Europa, Mundo<br>
• <b>Classe de ativo:</b> ações, obrigações, imóveis, ouro<br>
• <b>Moeda:</b> EUR, USD, GBP<br>
• <b>Temporal:</b> investir regularmente (DCA)<br><br>
Um ETF global (ex: VWCE) oferece diversificação em mais de 3.000 empresas de uma vez.`
    },
    dividends: {
      title: "Dividendos YTD",
      body: `Os <b>dividendos</b> são pagamentos em dinheiro feitos pelas empresas aos seus acionistas, normalmente trimestrais ou anuais.<br><br>
<b>YTD</b> (Year To Date) = total recebido desde o início do ano corrente.<br><br>
<b>Como registar:</b><br>
• Vai ao separador <b>Divid.</b> e usa o botão +<br>
• Ou importa o extrato da corretora (CSV/Excel)<br><br>
O valor mostrado aqui é o líquido (já descontada a retenção na fonte).`
    },
    divSummary: {
      title: "Resumo Anual de Dividendos",
      body: `O <b>resumo anual</b> permite introduzir os totais de dividendos do ano diretamente — útil se tens o extrato anual da corretora.<br><br>
<b>Campos:</b><br>
• <b>Bruto:</b> total recebido antes de impostos<br>
• <b>Retenção:</b> imposto retido na fonte pela corretora<br>
• <b>Líquido:</b> o que efectivamente recebeste (Bruto − Retenção)<br>
• <b>Yield:</b> dividendos / valor da carteira × 100<br><br>
Este valor é usado como fonte principal no cálculo do Rendimento Passivo.`
    },
    forecast: {
      title: "Previsão de retorno",
      body: `A <b>previsão</b> estima o valor futuro de cada ativo com base no seu retorno esperado.<br><br>
<b>Como funciona:</b><br>
• Soma rendimento base e valorização esperada de cada ativo<br>
• Usa TWR anualizado da carteira quando existe histórico robusto para a projeção global<br>
• Projeta para o horizonte temporal escolhido com reinvestimento implícito<br><br>
<b>Nota:</b> É uma estimativa — os retornos reais dependem das condições de mercado.`
    },
    compare: {
      title: "Comparação de Períodos",
      body: `Compara a evolução do teu património entre diferentes períodos.<br><br>
<b>MoM</b> (Month over Month): variação mês a mês<br>
<b>YoY</b> (Year over Year): variação ano a ano<br><br>
Os dados são baseados nos <b>snapshots</b> que guardas usando o botão <b>"Registar mês"</b> no Dashboard.<br><br>
Regista um snapshot no fim de cada mês para teres um historial completo.`
    },
    twr: {
      title: "O que é TWR?",
      body: `<b>TWR</b> (Time-Weighted Return / Retorno Ponderado pelo Tempo) mede o desempenho real dos teus investimentos, ignorando o efeito de quando entraste ou saíste dinheiro.<br><br>
<b>Porquê importa:</b> se investires 1000€ mesmo antes de uma subida, o teu retorno em euros parece óptimo — mas isso é sorte de timing, não desempenho. O TWR remove essa distorção, tal como os fundos de investimento reportam a sua performance.<br><br>
<b>Sem histórico suficiente</b> (definido em "anos mínimos" ao lado), a app usa uma estimativa baseada no rendimento e valorização esperados de cada ativo — menos precisa, mas disponível desde o primeiro dia.<br><br>
Isto só afecta previsões e comparações de performance — o valor da tua carteira e o rendimento passivo mostrado no Dashboard não mudam.`
    }
  };

  function openTip(key) {
    const tip = TIPS[key];
    if (!tip) return;
    const el = document.getElementById("tipModal");
    const titleEl = document.getElementById("tipTitle");
    const bodyEl = document.getElementById("tipBody");
    if (!el || !titleEl || !bodyEl) return;
    titleEl.textContent = tip.title;
    bodyEl.innerHTML = tip.body;
    if (typeof window.openModal === "function") window.openModal("tipModal");
    else { el.hidden = false; el.setAttribute("aria-hidden", "false"); }
  }

  function toast(msg, duration = 3000) {
    let el = document.getElementById("toastEl");
    if (!el) {
      el = document.createElement("div");
      el.id = "toastEl";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      el.setAttribute("aria-atomic", "true");
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("toast--show");
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("toast--show"), duration);
  }

  window.VestraFeedback = Object.freeze({ TIPS, openTip, toast });
  window.openTip = openTip;
  window.toast = toast;
})();
