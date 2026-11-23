# Protocolo de validação do score de inversões (fundo/topo)

Estado: **proposta** (23/11/2026). Fixa definições *antes* de ver resultados, para que uma probabilidade só chegue à UI se passar critérios definidos à partida. Não altera o motor nem a pontuação em produção.

## 1. Problemas que o protocolo resolve
1. A pontuação live (5 votos binários, pesos 25/20/20/20/15) nunca foi avaliada com o protocolo do laboratório (`market_turning_*`).
2. O rótulo atual (queda ≥7% e ressalto ≥5% em 20 sessões, extremo nas 5 sessões seguintes) mede "ressalto tático", não fundo cíclico. A prevalência condicional é ~43%.
3. O ganho de Brier do modelo incondicional (~0,23 a 10 sessões) mistura-se com a elegibilidade: `drawdown_126_pct` é feature e condição do rótulo. Com elegibilidade igual, o ganho cai para ~0,04 e o IC inclui zero para fundos.
4. Votos correlacionados (RSI 5/14 r=0,87; CNN Fear & Greed incorpora volatilidade, breadth e crédito) contam como confluência independente.

## 2. Alvos (dois, declarados e distintos)
| Alvo | Definição (só informação posterior ao sinal, usada apenas como rótulo) |
|---|---|
| **Ressalto tático** | Elegível (drawdown 126s ≥7%). Positivo se o SPY subir ≥5% desde o fecho do sinal em ≤20 sessões **sem** fechar >3% abaixo do fecho do sinal antes. |
| **Fundo cíclico** | Elegível (drawdown 126s ≥10%). Positivo se nenhum fecho dos 60 dias seguintes ficar >3% abaixo do fecho do sinal **e** o SPY recuperar ≥8% em ≤60 sessões. |
| **Topo (reversão)** | Elegível (alta 126s ≥7%). Positivo se o SPY cair ≥5% em ≤20 sessões sem fechar >3% acima do fecho do sinal. |

A UI só poderá falar de "fundo" com o alvo cíclico; o tático deve chamar-se "ressalto".

## 3. Variáveis
- Uma família por conceito, contínuas e como percentis *as-of*: volatilidade (VIX pct126, razão VIX 1m/3m), momentum (RSI semanal 14), volume (MFI14), crédito (variação 5d HYG/LQD), breadth (A−D NYSE, se houver série ≥10 anos), drawdown.
- **Excluídas** do modelo: Fear & Greed (redundante com as famílias acima; mostrar só como contexto) e COR1M (0% de cobertura histórica).
- Sem ajuste de limiares nos dados de teste. Hiperparâmetros fixados antes do primeiro teste (regressão logística L2, C fixo).

## 4. Validação
- Walk-forward expansivo, purga ≥ horizonte+20 sessões, dobras anuais.
- Âncoras de teste não sobrepostas (≥ horizonte entre âncoras).
- Unidade de inferência: **episódio de stress** (cluster de sessões elegíveis separadas por <20 sessões), não a sessão. Bootstrap por episódio e por ano.
- Comparação emparelhada com a prevalência de treino (baseline) e com o modelo só de drawdown.
- Séries históricas ajustadas retroativamente: os resultados são "consistência histórica", nunca prova point-in-time.

## 5. Critérios de promoção a probabilidade na UI (todos)
1. ≥ 12 episódios independentes e ≥ 30 rótulos positivos por lado.
2. Ganho de Brier vs baseline > 0 com IC a 95% (por episódio **e** por ano) que exclua zero, e vs modelo só de drawdown.
3. Calibração: ≥ 3 caixas com ≥ 20 observações e |previsto − observado| ≤ 0,10.
4. Resultados prospetivos independentes maduros ≥ 8 episódios, com sinal do ganho concordante.
5. Vintages point-in-time dos dados de entrada verificados (ou limitação declarada no texto da UI).
Até cumprir **todos**: a UI mostra apenas contexto (stress, estrutura de preço) e a prevalência histórica condicional com intervalo, nunca uma percentagem de "probabilidade de fundo".

## 6. Saída mostrada ao utilizador (quando promovido)
`P(alvo | elegível)` com intervalo, prevalência-base e *n* de episódios; mais risco adverso: percentil 90 do mínimo adicional após o sinal. Nunca 0–100 sem unidade.

## 7. Registo prospetivo
Manter `market-turning-prospective` (modelo congelado, resultados a 10/20/60 sessões, apenas acrescentar). Acrescentar os alvos cíclico e tático da secção 2 ao registo antes do primeiro resultado maduro (primeiro: ~5/12/2026), para não os escolher depois.
