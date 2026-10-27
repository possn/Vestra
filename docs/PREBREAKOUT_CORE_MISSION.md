# Vestra Core — missão Pre-Breakout (contrato de engenharia)

> **Objetivo:** detetar **ANTES** da confirmação, com dados fechados e verificáveis, ações em bases de acumulação com contração genuína e possível expansão iminente. O scanner não prevê certezas, não é um sinal de compra e não atribui probabilidades sem calibração prospectiva.

## Princípios não negociáveis
1. **Verdade > cobertura aparente > scores.** Sem OHLCV completo, sessão fechada, moeda/liquidez confirmada, base válida e pivot ainda intacto = abster. Rejeitar look-ahead, revisões retroativas e duplicados.
2. **Estados distintos:** `compressão` (observação), `pré-breakout` (configuração verificada ANTES do pivot), `breakout confirmado` (evento posterior distinto), `falhado/invalidação` e `desconhecido` (sem nova observação). Não deduzir transições a partir da ausência num scan rotativo.
3. **Uma tese por candidato.** Mostrar pivot, distância, 3 contrações não sobrepostas, redução do volume, estrutura das médias, preço/ATR, liquidez USD, data da vela e confiança na **evidência**, não probabilidade fabricada.
4. **Pesquisa cega a resultados futuros.** Persistir sinal, timestamp, universo elegível, preço e resistências **antes** de observar desfechos. Comparar a benchmarks de base-rate e controlos por liquidez/tendência e evitar survivorship/selection bias.
5. **Fiabilidade simples.** Medir scanners com **arquivos publicados + barras observadas**; sucesso de workflow com scan ignorado não conta como cobertura. Um scanner canónico, um mecanismo de recuperação bem definido; não aumentar indefinidamente cron, jobs e triggers.

## Invariantes atuais / limites conhecidos
- `scan_bars`: MM50 > MM150 > MM200 crescentes; VCP em janelas não sobrepostas 20/20/20, largura da base <= 22%, contração comparada com a anterior, distância do fecho ao pivot de 0% a 8%, rejeição de máximos intradiários acima do pivot +0,5%; filtro estrito de posição na base >=65% e volume financeiro >=USD 5M após FX verificado. `pré-breakout` exige distância <=4% e secagem de volume.
- O score atual é **heurístico**, não uma probabilidade de sucesso. `daily_focus` dá preferência a estrutura verificada e pode abster-se.
- Quatro slots UTC/dia × **150 tickers por slot = teto aritmético de 600 observações únicas/dia**, antes de falhas, watchlists e repetições. Para universo de 1.173, cobertura diária **total é impossível** sob o orçamento atual. Mesmo o teto aritmético é apenas ~51,15%. Não afirmar cobertura total com o agendamento existente.
- A coleção histórica só contém slots **efetivamente publicados**. Não preencher artificialmente intervalos vazios. Dados Yahoo auto-adjusted são informação útil de pesquisa, mas ajustes posteriores podem alterar séries históricas e requerem sensibilidade à versão de preços.

## Plano de produto e condições de aceitação
### P0 · Integridade e transparência
- Verificar a cada publicação: slots realmente publicados; OHLCV válido por símbolo; frescura da barra; universo elegível; cobertura rolling 24 h; oportunidades exclusivas de cada data.
- Purgar contaminação temporal: nenhuma vela futura/aberta nem candlestick posterior ao timestamp; igualdade do pivot e respetiva janela com data do sinal.
- Separar **estado do scanner** (`actualizado`, `parcial`, `degradado`, `indisponível`) do **estado do setup**; falha de dados não significa rejeição técnica.
- Gate de serviço: sinal público não pode ser vendido como abrangente enquanto a cobertura for parcial.

### P1 · Detecção antecipada (investigação, não otimização oportunista)
- Criar coortes de setups por dia/sessão, não por cada re-scan do mesmo sinal.
- Construir features **as-of**: contrações sequenciais, ATR14/ATR60, tendência, pivots/fracassos anteriores, suporte, RS vs benchmark e força setorial *apenas quando fontes e timestamps forem auditados*. Características em falta não pontuam.
- Identificar falsos positivos: ruturas antecipadas intradiárias, suportes repetidamente violados, notícias/eventos sem cobertura verificável, liquidez perto do limite, base excessivamente extensa.
- Validar qualquer novo filtro em modo `shadow`; só promover para produção após evidência OOS, teste de regressão e análise de trade-offs de recall.

### P2 · Medição prospectiva, impossível de simular com retroajustes
- Congelar feed, código/modelo, universe snapshot, candle date, signal-time e candidate ID em arquivos imutáveis.
- Avaliar horizontes de **5, 10 e 20 sessões**: evento breakout confirmado (fecho > pivot +0,5%, volume >=1,5×20 e fecho no quartil superior), tempo até confirmação, máximos adversos, retornos ajustados e invalidadores. Não usar velas do dia do alerta se não fechadas.
- Mostrar precisão (PPV), recall quando denominador observável, taxa de falso positivo, comparação com base-rate, intervalo de confiança, amostra, maturidade do desfecho e cobertura. Sem numerador/denominador suficientes: `insufficient_evidence`.
- Fazer walk-forward cronológico com `purge/embargo` das janelas sobrepostas, sem ajustar thresholds com os mesmos eventos usados para validação.

### P3 · Experiência premium
- Home: **1 conclusão** («há um setup investigável» / «nenhum setup suficientemente verificado»), 1 métrica de cobertura e uma ação clara. Nada de mosaicos técnicos redundantes.
- Dossier: gráfico preço + resistência + base, features auditadas, data do scan, risco/invalidação, explicação do que ainda falta para confirmar. Nunca «breakout iminente garantido».
- Diagnóstico/cron/logs ficam em observabilidade interna e não dominam a interface.

## Instruções / prompts de execução para agentes de desenvolvimento
**Auditor de dados:** «Parte do último main. Para cada estágio do scan identifica a fonte, timestamp, valores ausentes e condições fail-closed. Demonstra cobertura observada com arquivos reais; proíbe OHLCV inventado e dados incompletos. Produz testes determinísticos.»

**Quant pesquisador:** «Formula uma hipótese falsificável sobre pre-breakout VCP. Separa features anteriores ao pivot de outcomes futuros. Desenha coortes as-of, negativos comparáveis e walk-forward sem leakage. Não mexas no ranking live até existir evidência prospectiva suficiente.»

**Engenheiro core:** «Mantém um único scanner canónico e dependências mínimas. Identifica estrangulamentos reais de cobertura/duração antes de alterar orçamento. Faz commits pequenos, testes de invariantes e regressões. Não alteres motor de cotações nem MutationObservers.»

**Responsável de produto/UI:** «Entrega conclusão → evidências → ação → detalhe. Explicita sinal ainda não confirmado, risco, data de observação, cobertura e motivo de abstenção. Preserva funcionalidades da Vestra 2.0 sem novos dashboards redundantes.»

**Revisor de release:** «No exato PR head SHA exige Runtime JS, Architecture invariants e ambos Browser E2E WebKit verdes. Confirma PR aberto, mergeable, behind=0, main estável e merge com expected_head_sha. Sem exceções para CI intermitente ou pendente.»

## Critério de “produto final”
O produto só merece o título **scanner pre-breakout validado** quando (a) a cobertura efetiva é observada e adequada ao universo-alvo, (b) a deteção acontece antes da ruptura em dados imutáveis, (c) resultados OOS e falsos positivos são auditáveis, (d) degradação e abstenção são honestas, (e) a UI mostra decisão com evidência. Antes disso: **motor de pesquisa em validação**, independentemente do número de funcionalidades.
