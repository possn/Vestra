## Vestra v6.6.5 — Proven Quote Refresh & Asset-Specific News

- Reposto o mecanismo de cotações comprovado na app Património: `/quote` individual com fallback por candidato Yahoo, agora com concorrência limitada.
- Removido o estado experimental `quoteWorkerMode` e a dependência do endpoint batch `/quotes`.
- Ativos sem identidade segura são ignorados, não apresentados como falhas de rede.
- Notícias passam a pesquisar nome da empresa + ticker e a aplicar filtro de relevância.
- A tab Notícias do dossier mostra apenas títulos confirmadamente relacionados com o ativo aberto.
- PWA cache: `vestra-cache-v68`.

## Vestra v6.6.4 — Quote Refresh Compatibility & Diagnostics

- O refresh deteta automaticamente um Worker sem `/quotes` compatível e faz fallback para `/quote` individual com concorrência limitada.
- Se o endpoint batch responder mas falhar quase todo o lote, a app também muda automaticamente para o modo de compatibilidade.
- Ativos sem identidade segura deixam de ser apresentados como erros de rede: são contados como ignorados e mantêm o último valor conhecido.
- O estado da sincronização mostra quando foi usado modo de compatibilidade.
- Manual e automático usam exatamente o mesmo caminho.
- PWA cache: `vestra-cache-v67`.

## Vestra v6.6.3 — Quote Refresh Scope Repair

- Revisto o caminho completo de atualização manual e automática de cotações após o erro Safari `normalizeTickerLookupKey is not defined`.
- O validador de identidade usado pelo refresh é agora totalmente autocontido e não depende de helpers em scopes internos.
- Mantém validação conservadora: ISIN, yahooTicker/ticker estruturado, tags explícitas e rejeição de nomes descritivos de produtos como tickers.
- Manual e automático continuam a usar o mesmo `refreshLiveQuotesCore()`.
- Adicionado smoke test de execução do helper, além de `node --check`.
- PWA cache: `vestra-cache-v66`.

## Vestra v6.6.2 — Risk Budget Clarity & Quote Refresh Repair

- A box Diversificação real passa a usar blocos legíveis, barras de exposição, limites explícitos e uma leitura curta do score.
- Excessos de fator/moeda/região ficam destacados sem depender de chips pequenos.
- Corrige o erro `hasStrongQuoteIdentity is not defined` no caminho de atualização de cotações, preservando as proteções contra colisões de ticker e identidade fraca.
- A mesma correção desbloqueia a atualização manual e o caminho automático que usa o mesmo motor de cotações ao abrir/regressar à app.
- PWA cache: `vestra-cache-v65`.

## Vestra v6.6.1 — Research Queue Repair & Low52 Opportunity Rank

- Research Queue agora atualiza a própria janela de Portfolio Intelligence imediatamente ao marcar Em revisão / Revisto / Adiar 7d.
- Fechar “As minhas posições” regressa ao separador Carteira, em vez de deixar o utilizador no Mercado por trás do modal.
- Novo Low52 Opportunity Rank 0–100 ordena os mínimos combinando Low52 intelligence, Recovery Confirmation, qualidade, confiança, valuation e comportamento relativo ao setor.
- O Opportunity Rank é apenas ranking de research e não altera o Score Vestra.
- PWA cache: `vestra-cache-v64`.

## Vestra v6.6 — Recovery Confirmation

- Empresas em drawdown/mínimos passam a distinguir simples ressalto de recuperação apoiada por evidência.
- Estados: Sem confirmação, Estabilização, Recuperação em curso, Recuperação confirmada, Ressalto sem confirmação e Falha de recuperação.
- Cruza retornos 20/60 dias com expectativas, aceleração de receita, margens, tese, tendência da causa da queda e comportamento relativo ao setor.
- Novo card Recovery Confirmation no dossier e contexto adicional em Mínimos 52s.
- Não altera Score Vestra nem constitui sinal de entrada.
- Dataset schema: 521. PWA cache: `vestra-cache-v63`.

## Vestra v6.5 — Sector-relative Drawdown & Flow Ranking Repair

- Corrige os rankings de Fluxos: Maiores ganhos (€/% ) mostram apenas ganhos positivos; perdas e zeros deixam de contaminar o ranking.
- A ordenação dos rankings deixa de usar valor absoluto, evitando que uma grande perda apareça como maior ganho.
- Novo contexto empresa vs setor: retorno 1 ano de cada empresa comparado com a mediana de pelo menos 4 pares do mesmo setor.
- Classifica a queda como sobretudo específica da empresa, pior que o setor, próxima do setor ou melhor que o setor.
- Mínimos 52s e o card “Porque caiu?” passam a mostrar esta comparação; não altera Score Vestra.
- Dataset schema: 520. PWA cache: `vestra-cache-v62`.

## Vestra v6.4 — Drawdown Diagnosis

- Empresas com drawdown material passam a ter diagnóstico explícito do provável motor da queda: operação, expectativas, balanço/financiamento, diluição, compressão de múltiplos ou mercado/setor residual.
- Cada driver tem intensidade 0–100, evidência curta e tendência: a melhorar, estável ou a piorar.
- O diagnóstico aparece no dossier em “Porque caiu?” e também contextualiza a lista de Mínimos 52s.
- Não prova causalidade e não altera o Score Vestra; é uma camada explicável de research.
- Dataset schema: 519. PWA cache: `vestra-cache-v61`.

## Vestra v6.3 — Thesis Checkpoints & Low52 Intelligence

- Research Queue passa a guardar checkpoint da tese e uma nota curta por posição, localmente no dispositivo.
- Checkpoints: Mantém, Deteriorou, Aguardar earnings, A melhorar e Rever saída; não alteram Score Vestra nem a carteira.
- Novo motor específico para empresas perto dos mínimos de 52 semanas: combina qualidade, balanço, cash flow, confiança, valuation, expectativas, receita/margens, diluição, estrutura de capital e Risk Gate.
- Cada empresa perto do mínimo é classificada como Oportunidade potencial, Queda saudável / acompanhar, Indeterminado, Risco de value trap ou Deterioração estrutural.
- Fallen Angels e Mínimos intactos passam a consumir esta classificação em vez de apenas thresholds simples.
- Dataset schema: 518. PWA cache: `vestra-cache-v60`.

## Vestra v6.2 — Research Queue

- Nova fila operacional de research dentro de As minhas posições, logo após o Decision Center.
- Posições a rever entram automaticamente como Novo e podem ser marcadas Em revisão, Revisto ou Adiar 7 dias.
- Estado fica apenas no dispositivo via localStorage e não altera Score Vestra, Action Map, Risk Gate ou carteira.
- A fila prioriza pendentes e evita que uma carteira grande obrigue a recomeçar sempre a revisão do zero.
- PWA cache: `vestra-cache-v59`.

## Vestra v6.1 — Interactive Decision Center

- Portfolio Decision Center deixa de ser apenas uma síntese passiva e passa a navegar diretamente para o detalhe relevante.
- KPIs de Convicção, Risk Budget, Pior Stress e Rever/Substituir são tocáveis.
- Prioridades e Próxima ação abrem o dossier da posição ou saltam para Targets, Rebalancer, Stress Test, Risk Budget ou Action Map.
- O pior cenário de stress é selecionado automaticamente quando aberto a partir do Decision Center.
- Mantém a arquitetura de research: navegação e priorização, sem executar ordens.
- PWA cache: `vestra-cache-v58`.

## Vestra v6.0.1 — Action Map Filters

- Reforçar / Manter / Rever / Substituir passam a ser filtros interativos no Action Map.
- Tocar num estado mostra imediatamente apenas as posições dessa categoria; tocar novamente repõe a lista completa.
- O filtro selecionado fica visualmente ativo e mostra quantas posições estão visíveis.
- Os detalhes expandem automaticamente quando o filtro tem resultados fora das primeiras 12 posições.
- PWA cache: `vestra-cache-v57`.

## Vestra v6.0 — Portfolio Decision Center

- Nova síntese executiva no topo de As minhas posições.
- Consolida convicção ponderada, Risk Budget, pior Stress Test, concentração e posições a rever.
- Mostra prioridades e uma próxima ação de research sem criar um novo score de investimento.
- Mantém Action Map, Targets, Stress Test, Fresh Capital Planner e Rebalancer abaixo para detalhe.
- PWA cache: `vestra-cache-v56`.

## Vestra v5.9 — Portfolio Stress Test

- Novo Stress Test proxy dentro de As minhas posições, sem alterar a navegação principal.
- Cenários iniciais: Taxas +100 bps, Nasdaq -20%, Petróleo -25%, USD -10% e Recessão europeia.
- Mostra impacto ponderado estimado, Stress Resilience 0–100, peso com exposição forte e posições que mais contribuem para o choque.
- Usa fatores, setor/indústria, beta, moeda e região já disponíveis; é explicitamente uma heurística de stress, não previsão, VaR ou modelo de correlação.
- Nenhum cenário altera Score Vestra, Investment Case ou Portfolio Targets.
- PWA cache: `vestra-cache-v55`.

## Vestra v5.8.1 — Candidate Fallbacks

- Fresh Capital Planner e Assisted Rebalancer deixam de falhar silenciosamente quando nenhum ativo cumpre simultaneamente todos os filtros ideais.
- Candidatos são classificados em Preferido, Aceitável com alertas e Apenas research; Risk Gate high/severe continua a ser exclusão dura.
- Portfolio Targets continuam prioritários, mas existe um soft budget limitado quando pequenas ultrapassagens bloqueiam todos os candidatos.
- A interface mostra confiança baixa/ausente, valuation exigente, expectativas em deterioração e soft budget em vez de esconder o candidato.
- Rebalancer deixa de sugerir um montante superior ao valor da posição de origem.
- PWA cache: `vestra-cache-v54`.

## Vestra v5.8 — Portfolio Risk Budget

- Novo Risk Budget proxy na Portfolio Intelligence: fatores, moeda, região e sensibilidade provável a taxas.
- Fatores suportados com os dados atuais: Growth, Value, Dividendos, Small caps e Sensível a taxas.
- Portfolio Targets passam a incluir máximos configuráveis por fator, moeda e região.
- Assisted Rebalancer e Fresh Capital Planner penalizam destinos que agravem concentrações acima desses orçamentos.
- País/moeda usam dados explícitos quando disponíveis e fallback pelo ticker/mercado quando necessário; a interface identifica a leitura como proxy.
- O Risk Budget mede construção/diversificação e não substitui VaR, volatilidade ou análise macro profissional.
- PWA cache: `vestra-cache-v53`.

## Vestra v5.7 — Fresh Capital Planner

- Novo simulador para alocar capital novo sem vender posições existentes.
- Distribui o montante por até 3 destinos principais, podendo usar destinos adicionais quando os limites impedem a alocação completa.
- Respeita máximo por posição, máximo por setor, política de overlap e prioridade Equilibrado/Quality/Growth/Dividendos.
- Exclui Risk Gate alto/severo, confiança <60, valuation excessivo e expectativas em deterioração.
- Mostra impacto estimado na convicção ponderada e peso/setor após cada reforço.
- PWA cache: `vestra-cache-v52`.

## Vestra v5.6 — Portfolio Health Timeline

- Guarda localmente um snapshot diário da saúde da carteira; reabrir no mesmo dia atualiza o snapshot em vez de o duplicar.
- Histórico inclui Target Fit, convicção ponderada, maior posição, maior setor, overlap indireto e número de posições em Rever/Substituir.
- Mostra tendência vs snapshot anterior e os últimos 8 registos diretamente em As minhas posições.
- Ao guardar novos Portfolio Targets, Target Fit e snapshot são recalculados imediatamente.
- Histórico fica apenas no dispositivo e mantém até 120 snapshots.
- PWA cache: `vestra-cache-v51`.

## Vestra v5.5 — Target Fit & Drift

- Novo Target Fit 0–100 na Portfolio Intelligence para medir aderência aos objetivos definidos na v5.4.
- Identifica posições acima do peso máximo, setores acima do limite e overlap indireto relevante quando o objetivo é reduzi-lo.
- Mostra os principais desvios em linguagem simples, antes do painel de configuração e do rebalanceador.
- O score de aderência é de construção de carteira e não altera o Score Vestra das empresas.
- PWA cache: `vestra-cache-v50`.

## Vestra v5.4 — Portfolio Target Engine

- Objetivos persistentes e locais para orientar o rebalanceamento: máximo por posição, máximo por setor, política de overlap e prioridade de carteira.
- Perfis de prioridade: Equilibrado, Quality, Growth e Dividendos.
- Assisted Rebalancer e Multi-Move Plan passam a usar estes objetivos em vez de thresholds fixos.
- Destinos que excedem os limites recebem penalização progressiva; reduzir overlap pode ser imposto como objetivo explícito.
- Nenhuma alteração é executada automaticamente; os objetivos são guardados apenas no dispositivo.
- PWA cache: `vestra-cache-v49`.

## Vestra v5.3 — Multi-Move Rebalance Plan

- Novo plano de rebalanceamento com até 3 movimentos coerentes a partir das posições mais frágeis.
- Cada movimento usa o Assisted Rebalancer v5.2 e evita repetir o mesmo destino.
- O plano mostra capital total realocado e impacto agregado estimado na convicção ponderada e overlap indireto.
- Prefere movimentos com melhoria de convicção e rejeita cenários com agravamento excessivo de overlap quando há alternativa.
- Não altera a carteira nem considera impostos/spreads/comissões; continua a ser simulação de research.
- PWA cache: `vestra-cache-v48`.

## Vestra v5.2 — Assisted Rebalancer

- Novo simulador interativo em As minhas posições: escolhe a posição de origem e o montante a libertar.
- Mantém o valor total da carteira e ordena até 5 destinos elegíveis por convicção, concentração, overlap indireto e valuation.
- Destinos com Risk Gate alto/severo, confiança <60, valuation excessivo ou expectativas em deterioração são excluídos.
- Mostra peso e setor após a realocação, impacto estimado na convicção ponderada e alteração de overlap via ETFs.
- Não executa ordens nem inclui fiscalidade/custos; é uma ferramenta de research e cenário.
- PWA cache: `vestra-cache-v47`.

## Vestra v5.1 — Portfolio Scenario Preview

- As substituições sugeridas passam a mostrar um preview antes/depois mantendo o mesmo valor da posição.
- A simulação estima a alteração da convicção ponderada da carteira e do overlap indireto via ETFs.
- Como as alternativas são do mesmo setor, a concentração setorial é assumida como inalterada nesta primeira versão.
- Cada cenário é marcado como Melhora / Neutro / Piora e continua a ser apenas apoio a research.
- PWA cache: `vestra-cache-v46`.

## Vestra v5.0 — Portfolio Optimization Context

- O Portfolio Action Map passa a considerar o impacto de cada posição na carteira, não apenas a qualidade isolada do ativo.
- Peso da posição, concentração setorial e exposição indireta via ETFs entram no contexto de Reforçar / Manter / Rever / Substituir.
- Uma posição forte mas já demasiado grande deixa de ser candidata automática a reforço.
- Alternativas do mesmo setor são penalizadas quando aumentam overlap indireto e destacadas quando o reduzem.
- O mapa mostra indicadores de concentração e overlap antes das ações por posição.
- Continua a ser priorização de research, não uma ordem automática de transação.
- PWA cache: `vestra-cache-v45`.

## Vestra v4.9 — Portfolio Action Map

- Novo mapa por posição em As minhas posições: Reforçar / Manter / Rever / Substituir.
- A classificação usa Convicção, Confidence Engine, valuation, estimate momentum, thesis direction, Risk Gate e alternativas já identificadas.
- “Substituir” só aparece quando a posição está materialmente fraca e existe uma alternativa do mesmo setor já filtrada como superior.
- Cada linha mostra a razão principal e abre diretamente o dossier da posição.
- É uma classificação de research, não uma ordem automática de compra/venda.
- PWA cache: `vestra-cache-v44`.

## Vestra v4.8 — Catalyst & Risk Engine

- Novo timeline auditável no dossier: “o que pode mexer esta ação e quando”.
- Usa apenas eventos com evidência já recolhida: earnings, estimate momentum, insiders, trajetória da tese, estrutura de capital e STOCK Act.
- Datas só são mostradas quando existem na fonte; sinais sem data aparecem como janelas (“30d”, “filings recentes”), nunca como datas inventadas.
- Eventos de estrutura de capital herdam severidade do Risk Gate e podem dominar o painel quando são materiais.
- Dataset schema: 517. PWA cache: `vestra-cache-v43`.

## Vestra v4.7.2 — Portfolio Intelligence Contrast

- Corrige texto secundário ilegível nos cards claros de Portfolio Intelligence.
- O override é scoped a `.market-detail-card`, preservando o texto claro do Investment Case escuro.
- PWA cache: `vestra-cache-v42`.

## Vestra v4.7.1 — Portfolio Intelligence Access

- “As minhas posições” deixa de ficar escondido em Mais ferramentas e passa a ter acesso direto visível na área Mercado.
- O acesso abre a mesma inteligência v4.7: convicção, candidatos a reforço, posições a rever, concentração/overlap e alternativas.
- Mantém-se o layout global; apenas se torna visível uma funcionalidade já existente.
- PWA cache: `vestra-cache-v41`.

## Vestra v4.7 — Portfolio Intelligence

- A área As minhas posições passa a incluir inteligência de carteira sem alterar a navegação global.
- Convicção de research combina Score Vestra, Confidence Engine, valuation, estimate momentum e Risk Gate; permanece explicável e não é uma recomendação automática.
- Novos blocos: candidatos a reforço, posições a rever, concentração/overlap e alternativas melhores no mesmo setor.
- Overlap deteta concentração por posição/setor, holdings comuns entre ETFs e ações detidas diretamente que também aparecem dentro de ETFs.
- Alternativas exigem score pelo menos 8 pontos superior, confiança >=60, mesmo setor e ausência de Risk Gate alto/severo.
- Layout visual global permanece congelado.
- PWA cache: `vestra-cache-v40`.

## Vestra v4.6 — Intelligent Scanner

- Novo Scanner Vestra em Mais ferramentas, sem alterar a navegação principal congelada.
- Estratégias: QARP, Fallen Angels, Mínimos 52s com fundamentos intactos, Revisões positivas, Insider Accumulation, Turnarounds e Dividend Growers.
- Cada estratégia tem score próprio 0–100 e razões auditáveis; não altera o core Score Vestra.
- Confidence Engine e Risk Gate são filtros obrigatórios onde aplicável, reduzindo falling knives e falsos positivos de valuation.
- O botão Mínimos 52s continua como pesquisa ampla; “Mínimos intactos” é a versão filtrada por qualidade, confiança, diluição e risco.
- Layout visual global permanece congelado.
- Dataset schema: 516. PWA cache: `vestra-cache-v39`.

## Vestra v4.5 — Earnings & Estimate Intelligence

- Novo overlay quantitativo de expectativas, separado do Score Vestra por causa da cobertura desigual entre mercados.
- Combina revisões de EPS 30d, breadth de revisões, surpresa média/mais recente, sequência de beats e crescimento esperado.
- Produz `estimate_momentum_score` 0–100 e sinal Improving / Neutral / Deteriorating / Insufficient.
- A aba Resultados passa a mostrar momentum, breadth, revisão, surpresa, confiança e proximidade dos earnings.
- Alterações rápidas de expectativas entram nos catalisadores e pontos a vigiar do Investment Case.
- O cabeçalho do dossier sinaliza expectativas a melhorar/piorar sem alterar o core score.
- Layout visual permanece congelado.
- PWA cache: `vestra-cache-v38`.

## Vestra v4.4 — Valuation Engine & Sector Models

- Novo fair value Vestra em faixa, nunca como target pontual: mínimo, centro, máximo, upside/downside e margem de segurança.
- Âncoras explicáveis: P/E, forward P/E, P/B, FCF yield e dividend yield comparados com pares do mesmo setor.
- O fair value é independente dos price targets dos analistas e pode ser marcado como não acionável pelo Risk Gate.
- Novos score packs: Utilities, Energy, Biotech e Growth Tech, além de General, Banks, Insurance e REITs.
- Biotech pre-profit deixa de ser forçada para P/E: cash runway, net cash e diluição passam a dominar; sem dados adequados o valuation diz explicitamente “insuficiente”.
- “Sinal forte” no dossier passa a exigir score elevado + confiança de evidência suficiente + ausência de Risk Gate alto/severo.
- Layout visual permanece congelado.
- PWA cache: `vestra-cache-v37`.

## Vestra v4.3 — Confidence Engine

- “Confiança” deixa de ser sinónimo de quantidade de campos preenchidos.
- Novo Confidence Score 0–100 combina cobertura, autoridade/diversidade das fontes, frescura das contas, concordância entre fontes e robustez da identidade.
- SEC EDGAR expõe a data do período mais recente e cross-checks like-for-like de caixa, dívida, current ratio, ativos e equity quando Yahoo também tem esses valores.
- Divergência relevante entre fontes impede confiança alta; contas muito antigas também limitam a confiança.
- A confiança da tese passa a usar o Confidence Engine e pode ser alta tanto para uma boa tese como para um risco estrutural bem confirmado.
- `metric_confidence` preserva a antiga leitura baseada apenas em cobertura para auditoria.
- Layout visual permanece congelado.
- PWA cache: `vestra-cache-v36`.

## Vestra v4.2 — Capital Structure & Corporate Actions Risk

- SEC filings recentes passam a ser analisados para reverse splits, ATMs, ofertas de capital, convertíveis, warrants e risco de delisting.
- Reverse splits repetidos e convertíveis com preço variável/desconto ao mercado tornam-se red flags estruturais.
- O Risk Gate aplica caps não compensáveis: watch 64, high 49, severe 35.
- A tese passa a usar “Capital Structure Risk” quando estes sinais dominam o caso de investimento.
- O dossier recebe os eventos traduzidos em “O que pode quebrar a tese” através da taxonomia existente.
- A recolha SEC é seletiva (micro/small caps, preços baixos, diluição/anomalias e posições prioritárias) para manter o pipeline rápido.
- Sem blacklist por ticker ou país; regras auditáveis a partir dos filings.
- Layout visual permanece congelado.
- PWA cache: `vestra-cache-v35`.

## Vestra v4.1 — Risk Gate

- O score quantitativo passa por um Risk Gate antes de gerar o sinal final.
- FCF yield extremo (>30%) deixa de receber automaticamente um percentil favorável sem confirmação independente.
- Zombie por interest coverage, qualidade muito fraca, contração relevante de receita e diluição material passam a limitar o score.
- Dois ou mais red flags impedem um “Sinal forte”; red flags severos limitam o score a 45.
- A confiança é reduzida quando existem anomalias materiais, mesmo com elevada cobertura de campos.
- Nenhuma empresa é bloqueada por ticker/país: as regras são genéricas e auditáveis.
- Layout visual permanece congelado.

## Vestra v4.0 — European Source Fusion

- Layout visual permanece congelado.
- Cadeia europeia estrita: `ticker → ISIN → GLEIF/ANNA LEI → ESEF/UKSEF`.
- Sem fuzzy matching por nome de empresa: qualquer identidade ambígua é ignorada.
- xBRL-JSON oficial preenche apenas fundamentais em falta deixados pelo Yahoo.
- Dossiers podem expor ISIN/LEI e provenance da identidade quando o enriquecimento ESEF é usado.
- SEC EDGAR fica ativo por defeito com User-Agent identificável e pode ser sobrescrito por `SEC_USER_AGENT`.
- Alemanha e Irlanda ficam deliberadamente fora do enrichment automático enquanto persistirem lacunas documentadas de discovery no índice público.
- PWA cache: `vestra-cache-v33`.

## Vestra v3.9 — Earnings Quality & Capital Allocation

- Layout visual permanece congelado.
- Score geral v3 separa **Execução**, **Qualidade dos lucros** e **Alocação de capital**.
- Qualidade dos lucros usa conversão de lucro em cash flow operacional, accrual ratio e margem de FCF.
- Alocação de capital usa diluição, buybacks efetivamente reportados, ROCE proxy e cobertura de dividendos por FCF.
- Ausência de quatro trimestres comparáveis mantém a métrica ausente; nunca é convertida em zero.
- Dossier → Financeiro passa a explicar e mostrar estes diagnósticos.
- PWA cache: `vestra-cache-v32`.

## Vestra v3.8 — Source Fusion / Score v2

- Layout congelado: esta versão altera apenas dados/análise.
- Score geral passa a incluir **Execução / alocação de capital**: aceleração de receita, evolução de margem, diluição e ROCE proxy.
- Cobertura de dados inclui estas métricas adicionais; ausência continua a ser `null`, nunca zero.
- Suporte opcional a **SEC EDGAR Company Facts** no pipeline para ações US. Para ativar, definir o secret/env `SEC_USER_AGENT` com identificação adequada; não requer API key. O enriquecimento só preenche buracos deixados pelo Yahoo.
- Dossier Financeiro passa a mostrar cobertura, confiança, modelo e fontes efetivamente usadas.
- Arquitetura preparada para mais providers sem tornar qualquer um deles fonte única.

## Vestra v3.7 — 52-week lows — Fast Quote Sync

- Layout visual congelado; sem alterações estruturais de UI.
- Atualização automática de cotações convertida para batches (`/quotes`, 20 símbolos por pedido) em vez de centenas de requests individuais.
- Resolução por rondas: só tenta bolsa/ticker alternativo nos ativos que falham na ronda anterior.
- Refresh concorrente protegido: regressar à app durante uma atualização reutiliza a mesma operação.
- Estado `A atualizar` é sempre limpo em `finally`, mesmo perante erro de rede/JavaScript.
- Auto-refresh começa durante o splash e continua a respeitar a janela de 30 minutos.
- A duração da última atualização fica registada no painel de Preferências.
- Hero de Dividendos alinhado com a paleta Vestra teal/navy/dourado; removido o roxo isolado.
- PWA cache: `vestra-cache-v28`.

## Vestra v3.4 — Search Assist & Portfolio Dossiers

- Autocomplete instantâneo no Mercado, com ticker, nome e tipo antes de carregar Enter.
- Dossier reforçado contra overflow horizontal no iPhone; botão fechar persistente e sempre acessível.
- Ações/ETFs reconhecidos na Carteira podem abrir diretamente o mesmo dossier de Mercado; a edição da posição mantém-se disponível ao tocar fora do atalho de research.
- Layout visual global permanece congelado.
- PWA cache: `vestra-cache-v27`.

## Vestra v3.3 — Broker Identity Audit & Congress Live

- Quote identities audited against the original Trading 212 2023–2026 and XTB exports.
- 664 broker security-name identities are used only to repair ticker/ISIN/venue metadata; no quantities, values or account identifiers are embedded.
- Corrects recent ticker changes (including BK→BNY, IINN→QTEX, HOTH→RKTO) and UCITS ETF venue mappings derived from the actual trade currency (including ARXK.DE and QWTM.L).
- Broker rebuild schema bumped so existing imported positions are reconciled automatically.
- If an identity repair occurs, the next automatic quote refresh is forced to replace contaminated values.
- Congress live feed now tries Bargo directly from the browser (open CORS) and only then the Worker, with a 15-minute local cache and visible attribution.
- Smart Money now reports Congress-feed failure explicitly instead of silently appearing empty.
- Layout remains frozen.
- PWA cache: `vestra-cache-v26`.

## Vestra v3.2 — Safe Quotes & Settings Cleanup
- Layout visual mantido/congelado.
- Remove atalhos legacy sem styling no topo de Mais.
- Estado/refresh de cotações movido da Carteira para Mais → Preferências.
- Auto-refresh deixa de inferir tickers a partir da primeira palavra de nomes descritivos (ex.: WTI Crude Oil → WTI; ARK Innovation → ARK).
- Validação de moeda e saltos de preço; cotações suspeitas são rejeitadas e o último valor é mantido.
- Snapshot de rollback criado antes de cada refresh futuro.

## Vestra v2.6 — Mobile containment

- Mercado sem carrosséis infinitos: 8 controlos de setor (Todos + 6 setores + Mais).
- Dossier com 8 tabs em grelha: Resumo, Perspetiva, Growth, Valuation, Resultados, Financeiro, Smart e Notícias.
- Novas vistas Resultados e Financeiro.
- Correção de overflow de títulos, subtítulos e cards no iPhone.
- Cards de resultados fecham visualmente dentro das margens.
- Cache PWA v19.


## Vestra v2.4 — iPhone interaction repair

- Dossier de mercado passa a modal determinístico de ecrã inteiro; topbar/bottomnav não competem com o conteúdo.
- Cada dossier abre sempre no topo. Trocar de tab reposiciona o conteúdo no início da área de detalhe, sem saltos para o meio.
- Enriquecimento live preserva a posição de scroll em vez de reconstruir e saltar o viewport.
- Tabs do dossier e setores usam rail horizontal táctil com fallback JS para Safari/iOS.
- A antiga barra de rendimento passivo fica explicitamente desativada mesmo perante HTML/cache antigo.
- Cache PWA: vestra-cache-v18.
## Vestra v2.3 — Full-screen Dossier Fix

- Dossier de mercado abre sempre no topo; o scroll anterior deixa de ser reutilizado pelo Safari.
- Em iPhone/mobile, o dossier ocupa o viewport completo (`100dvh`) em vez de abrir como bottom sheet a 90%.
- Header do dossier fica fixo; conteúdo tem scroll próprio e safe-area inferior reforçada.
- `Ver pilares e detalhe quantitativo` e os últimos controlos deixam de poder ficar escondidos no fundo.
- Scroll da página por baixo fica bloqueado enquanto o dossier está aberto.

## Vestra v2.2 — Live Market + Sector Fix

- Worker v4.0 passa a expor `/market?ticker=` com detalhe live por ativo: valuation, margens, crescimento, balanço, consenso, earnings e histórico de preço 1 ano quando disponível.
- Dossiers do Mercado enriquecem silenciosamente os dados do dataset com informação live do Worker configurado; o dataset local continua como fallback.
- Badge `Live` identifica dossiers enriquecidos pelo Worker.
- Filtro de setores corrigido: filtra primeiro o universo completo e só depois ordena os melhores sinais.
- Todos os setores são renderizados, com carrossel horizontal real no iPhone e recentragem automática do setor selecionado.
- Empty states passam a respeitar a largura do card e deixam de sair da box.
- Cache PWA: `vestra-cache-v16`.

## Vestra v2.1 — Quote Sync

- Estado das cotações visível na Carteira, com atualização manual num toque.
- Auto-refresh explícito: ao abrir/regressar à app se os preços tiverem mais de 30 minutos.
- Preferência para ativar/desativar atualização automática.
- Estado de última atualização e erros junto das posições.

# Vestra

## Vestra v2.0 — Warm Dusk / Portfolio Intelligence

- Paleta ajustada para um dusk mais quente: porcelana, slate/teal, coral e dourado suaves.
- Contraste reforçado em texto secundário e, sobretudo, no hero de património.
- Removida a barra flutuante de rendimento passivo; o rendimento passa a ter um cartão central no Dashboard e mantém-se no resumo da Carteira.
- Splash simplificado: símbolo Vestra + `Finance, made simple.`; sem barra de progresso visível.
- “As minhas posições” em Mercado deixa de ser uma lista indiferenciada: agrega posições por ticker, prioriza as maiores, separa criptoativos e outros ativos e mostra cobertura do research.
- Criptoativos nunca são tratados como empresas apenas por coincidência de símbolo (ex.: ATOM).
- Removido um bloco CSS legado da v1.4 que continha `\n` literais e podia causar inconsistências de renderização.
- Cache PWA: `vestra-cache-v14`.


## Vestra v1.9 — Memory Layer

- Watchlist e posições passam a destacar apenas mudanças materiais: score, direção da tese, revisões de EPS, valuation, insiders e earnings próximos.
- A Vestra guarda snapshots locais por geração do dataset e compara a atualização atual com a anterior.
- Na primeira utilização, usa os deltas de 7/30 dias já produzidos pelo scanner como referência.
- Novo bloco **O que mudou** no dossier, antes do Investment Case; quando não há alteração material mostra **Estável**.
- A comparação temporal é local-first e não cria histórico falso em simples refreshes da página.


## Vestra v1.8 — Decision Bridge

- Tema global ligeiramente mais escuro, entre o visual original e o mist claro da v1.5.
- Superfícies slate/teal, barras translúcidas mais profundas e menos branco puro.
- Acentos coral/dourado usados apenas como energia visual pontual.
- Microinterações e estados ativos mais expressivos, mantendo linguagem premium.
- Dossier de Mercado passa a abrir com “Leitura Vestra”: score, sinal, forças, alertas, direção da tese e smart-money relevante.
- Cache PWA atualizado para `vestra-cache-v11`.

# Vestra

**Gestão de património + pesquisa de mercado numa única PWA.**

A Vestra junta a base funcional do Património Familiar ao motor de investigação do Finscanner, com uma regra de produto: **a complexidade existe, mas não aparece toda ao mesmo tempo**.

## v1.1 — Convergência Património + Mercado

### Património
- Multi-classe de activos
- Import de corretoras e bancos
- Balanço e cashflow
- Dividendos, FIRE, previsão, simuladores e fiscalidade
- IndexedDB / local-first e backup JSON

### Mercado
A antiga área placeholder foi substituída por um módulo funcional e lazy-loaded:
- Pesquisa global de empresas e ETFs
- Descoberta por score e sector
- Dossier por ticker com Overview, Growth, Valuation, Smart Money e Notícias
- Insiders (SEC Form 4) e Congresso dos EUA
- Teses de investimento e direcção da tese
- Comparação rápida de empresas
- Leitura das posições da carteira contra o universo do scanner
- Dataset e pipelines do Finscanner integrados em `data/`, `scripts/` e `.github/workflows/`

`data/stocks.json` só é carregado quando o utilizador entra em Mercado, para não tornar a abertura da PWA mais lenta.

## Design

O sistema visual foi clareado para um **mist/light premium**: superfícies claras, navy suave, turquesa Vestra e dourado discreto, mantendo tipografia e comportamento iOS/macOS.

## Stack

Vanilla HTML/CSS/JS · IndexedDB · Chart.js · Service Worker · PWA · pipelines Python/GitHub Actions para dados de mercado.

## Vestra v1.5 — Product finish

- Dashboard reorganizado em torno de património líquido, sinais rápidos, carteira, distribuição e evolução.
- Atalhos principais: Carteira, Mercado e Adicionar ativo.
- Objetivos, fontes, snapshots, manutenção, saúde financeira, risco, fiscalidade e ferramentas avançadas preservados atrás de “Explorar património”.
- Navegação principal simplificada para Início · Carteira · Mercado · Fluxos · Mais.
- Visual global mais claro e luminoso, mantendo turquesa/dourado e linguagem premium Vestra.
- Mercado mantém carga lazy do dataset Finscanner.


## v1.3 — Carteira + Mercado simplificados (2026-08-21)
- Carteira com leitura imediata: total, posições, maior classe e rendimento anual.
- Pesquisa, filtros, cotações e P&L movidos para disclosure progressivo.
- Mercado com pesquisa como ação dominante e modos compactos: Ideias, ETFs e Smart Money.
- Funcionalidades avançadas preservadas em Explorar mercado.


### v1.5 — Product finish
- Chrome móvel reduzido: `Mais` deixa de ser duplicado no topo do iPhone.
- Barra de rendimento persistente apenas em Início e Carteira.
- Pesquisa global alinhada com o tema balanced mist.
- Mercado com retry explícito em falha de dados, `Esc` para fechar dossiers e Enter em ticker exato.
- FAB em Mercado passa a focar a pesquisa em vez de mostrar texto legado.
- Toasts/snackbars acessíveis (`aria-live`) e compatíveis com safe areas.
- Diagnóstico de cache atualizado de `pf-cache-*` para `vestra-cache-*`.


### v1.8 — Decision bridge
- Watchlist local persistente, separada da carteira.
- Badges “Carteira” nos ativos já detidos.
- Nova aba Perspetiva com consenso, price targets, revisões de EPS e earnings.
- Dossier e listas permitem guardar/remover ativos com ☆/★.
- Mercado aproxima pesquisa, acompanhamento e património sem expor complexidade no primeiro nível.

### v2.6 — Dossier reliability lock
- Layout visual congelado a partir da v2.5; esta versão altera apenas robustez/comportamento.
- O dossier deixa de reconstruir todo o DOM quando chegam dados Live, evitando saltos/cortes no Safari.
- Modal passa a usar viewport fixo determinístico e um único scroll vertical.
- Abertura de cada ticker reinicia completamente o estado/scroll do modal.
- Mudança de tab já não força scroll programático.
- Removida a interceção táctil custom das tabs, agora que a navegação é uma grelha limitada.
- Fallback seguro quando um instrumento contém dados num formato inesperado.


## Vestra v2.9 — Fundamental Coverage
- Corrige `null`/campo ausente apresentado como zero nas tabs do dossier.
- Worker Market Proxy v4.1 com fallback Yahoo `fundamentals-timeseries` para empresas com `quoteSummary` incompleto.
- Enriquecimento de receita, lucro, EPS, margens, OCF, FCF, EBITDA, dívida, equity e caixa quando disponíveis.
- Valuation usa também os campos do endpoint Yahoo quote quando quoteSummary não fornece P/E/PB.
- Campos genuinamente indisponíveis passam a aparecer como `—`, nunca como `0` fictício.


### v2.9 — Portfolio clarity
- Carteira: rendimento anual, mensal estimado e yield médio ponderado no resumo.
- Mais: grupos expansíveis redesenhados como cards premium, mantendo o layout global congelado.


### v2.9 — Contrast & Settings Hub
- Hero variation chips now use theme-safe contrast classes.
- Dashboard shortcuts are fully contained on iPhone.
- Settings groups are presented as a 2×2 navigation hub and expand full width.


### v3.0 — Congress resilience + splash identity
- Restores and guarantees visible splash tagline: `Finance, made simple.`
- Minimum identity splash dwell so the tagline is actually readable on fast devices.
- Congress pipeline updated to use the current Bargo global `/trades?ticker=` query form, with legacy per-ticker fallback.
- Removes the old global 403 probe bailout that could disable all Congress data.
- Worker v4.2 adds `/congress?ticker=` and `/congress?limit=` live endpoints.
- Smart Money now falls back to the Worker when static Congress data is empty.
- Company Smart tab fetches recent Congress disclosures live when needed.
- PWA cache: `vestra-cache-v23`.


### v3.1 — Silent Quote Refresh
- Auto-refresh de cotações continua ativo ao abrir/regressar à app quando os preços têm mais de 30 minutos.
- Falhas isoladas deixam de abrir automaticamente o modal de erros.
- Atualização automática corre em background e mantém o último valor conhecido nos ativos que falham.
- Atualização manual também não bloqueia: mostra apenas um toast; detalhes só abrem por ação explícita do utilizador.
- Indicador de erros continua disponível na Carteira.
- PWA cache: `vestra-cache-v24`.


### v3.7 — Mínimos 52s
- Novo modo **Mínimos 52s** no Mercado.
- Calcula o mínimo dos últimos 12 meses a partir do histórico local de cada empresa.
- Mostra empresas até 5% acima do mínimo, ordenadas pela proximidade.
- Cada resultado indica distância ao mínimo e o valor do mínimo de 52 semanas.


### v3.7 — Dossier single-scroll repair
- Dossier passa a ter um único scroll vertical no modal.
- Remove scroll aninhado do painel interno no Safari iOS.
- Botão fechar movido para fora do painel e fixo ao viewport.
- Bloqueio explícito de overflow horizontal.
