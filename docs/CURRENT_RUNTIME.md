# Vestra — Estado operacional atual

Atualizado em 31 de agosto de 2026.

Este documento descreve a arquitetura efetivamente em produção e os contratos operacionais que devem ser preservados. O `README.md` mantém o histórico de versões; este ficheiro é a referência para o estado corrente.

## PWA e runtime

- A Vestra é uma SPA/PWA estática servida por GitHub Pages.
- O Service Worker é `Vestra Service Worker v10.10` com cache `vestra-cache-v124`.
- Documentos, scripts, estilos, manifest e ficheiros `data/*.json|txt` usam estratégia network-first com fallback offline.
- Imagens usam cache-first.
- Payloads grandes de mercado, como o universo completo de ações, não devem ser adicionados ao `APP_SHELL`.
- `app.js` e `market.js` continuam grandes; novas funcionalidades devem preferir módulos pequenos, carregados explicitamente e protegidos por testes de reachability.

## Mercado e cotações

- O browser parte do snapshot estático publicado (`stocks-index.json` + shards de dossiers) e aplica dados live de forma não destrutiva.
- O dossier aberto recebe overlay de campos live; não deve ser reconstruído integralmente durante refresh de cotações.
- O Worker canónico é `https://delicate-bar-cc80.pedrossnunes.workers.dev`.
- O contrato de produção é verificado por workflow dedicado, incluindo `/health`, `/quote`, `/quotes`, `/market`, CORS e preflight do POST de `/learned-universe`.
- A app deve degradar para último valor/snapshot disponível quando uma fonte live falha, sem transformar falta de dados em valor zero.

## Pesquisa global e universo aprendido

Uma empresa válida encontrada fora do catálogo diário pode ser aberta imediatamente como `DOSSIER GLOBAL · LIVE`.

O fluxo canónico é:

1. pesquisa global / validação exata;
2. consulta live ao Worker;
3. persistência local em IndexedDB através de `market-learned-universe.js`;
4. POST central para `/learned-universe`;
5. sincronização do universo aprendido no próximo pipeline;
6. promoção dos tickers aprendidos para a frente da fila antes do bulk market fetch;
7. enriquecimento subsequente no universo oficial e shards de dossier.

Contratos protegidos:

- identidade persistente é o ticker normalizado; nomes podem ser enriquecidos por fontes posteriores;
- posts centrais são deduplicados por sessão;
- tickers inválidos não são enviados;
- indisponibilidade do Worker durante a sincronização preserva o snapshot aprendido anterior;
- o pipeline promove learned tickers antes dos restantes extras/portfolio names.

## Mínimos 52 semanas

Existem dois níveis intencionais:

- **Low52 intelligence:** universo de análise até aproximadamente 10% acima do mínimo de 52 semanas;
- **Mínimos 52S na UI:** shortlist visual mais estrita, até aproximadamente 5% acima do mínimo.

O motor é exclusivo de ações e exclui ETFs/fundos. Cruza proximidade ao mínimo com qualidade, balanço, cash flow, confiança, valuation, expectativas, receita/margens, diluição, estrutura de capital, Risk Gate, drawdown diagnosis e recovery confirmation.

Estados possíveis incluem oportunidade potencial, queda saudável/a acompanhar, indeterminado, risco de value trap e deterioração estrutural. O Low52 Opportunity Rank é um ranking de research e não altera o Score Vestra.

## Score Vestra

- O Score tem guards de cobertura, proveniência e consistência de escala.
- Linhas de catálogo/carried/metadata não devem ser apresentadas como oportunidades acionáveis.
- A validação de performance é prospetiva, não reconstruída retrospetivamente.
- Não recalibrar pesos com base em amostra imatura.
- Primeiros horizontes de avaliação definidos a partir da coorte inicial: 28, 84 e 168 dias.

## Pipeline de dados

O workflow principal de mercado:

- sincroniza learned universe antes da recolha pesada;
- atualiza o mercado por lotes;
- gera shards e contratos de saída;
- calcula overlays técnicos e intelligence;
- valida universo, scores e cobertura;
- publica apenas depois de os guards passarem.

Workflows que escrevem dados em `main` devem preservar a estratégia de publicação/serialização definida no CI para evitar que uma execução longa perca o publish por avanço concorrente do branch remoto.

## Observabilidade

`market-data-health.js` apresenta no topo de Mercado uma faixa operacional expansível usando apenas dados já publicados:

- timestamp e idade do último `coverage_guard`;
- número de linhas verificadas;
- violações do guard;
- número de tickers aprendidos;
- origem do universo aprendido.

Semântica atual:

- `Operacional`: guard saudável e dados com idade <= 4 h;
- `Dados antigos`: guard saudável mas dados com idade > 4 h;
- `Atenção`: `coverage_guard.ok === false` ou existem violações;
- `Sem diagnóstico`: o guard não pôde ser carregado.

O módulo usa `cache: no-store`, atualiza ao regressar ao foreground e nunca deve assumir estado saudável quando os diagnósticos faltam.

## Gates de regressão

### Architecture invariants

Protege, entre outros:

- sintaxe JavaScript/Python;
- ordem e reachability dos módulos;
- identidade de ativos e cotações;
- storage contract;
- overlay live do dossier;
- contrato central do learned universe;
- semântica da observabilidade;
- regressão histórica completa.

### Browser E2E — WebKit/iPhone

Jornadas críticas obrigatórias:

- pesquisa MSFT -> dossier -> métricas -> tabs -> fechar -> reabrir;
- ETF discovery -> dossier de fundo utilizável;
- pesquisa global sintética -> dossier live -> persistência learned -> reload;
- renderização e expansão da faixa de saúde dos dados.

### Smoke de produção

Após publicação, o GitHub Pages deve ser testado contra um pequeno conjunto de tickers sentinela para detetar regressões que apenas aparecem no artefacto publicado.

## Regras de evolução

1. Estabilidade e contratos de produção têm prioridade sobre novas features.
2. Não fazer refactor massivo de `app.js`/`market.js`; extrair módulos pequenos incrementalmente.
3. Uma nova fonte não pode degradar proveniência nem converter ausência de dados em evidência falsa.
4. Alterações ao Score exigem evidência prospetiva madura e devem manter explicabilidade.
5. Funcionalidades críticas de iPhone/PWA precisam de cobertura WebKit quando o comportamento é verificável em browser.
6. Módulos dinâmicos devem permanecer alcançáveis pelo runtime audit e ser syntax-checked no CI.
