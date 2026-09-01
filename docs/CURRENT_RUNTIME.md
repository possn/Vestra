# Vestra — Estado operacional atual

Atualizado em 1 de setembro de 2026.

Este documento descreve a arquitetura efetivamente em produção e os contratos operacionais que devem ser preservados. O `README.md` mantém o histórico de versões; este ficheiro é a referência para o estado corrente.

## PWA e runtime

- A Vestra é uma SPA/PWA estática servida por GitHub Pages.
- O Service Worker é `Vestra Service Worker v10.11` com cache `vestra-cache-v125`.
- Documentos, scripts, estilos, manifest e ficheiros `data/*.json|txt` usam estratégia network-first com fallback offline.
- Imagens usam cache-first.
- Payloads grandes de mercado não pertencem ao `APP_SHELL`.
- `app.js` e `market.js` continuam grandes, mas responsabilidades de baixo risco são extraídas incrementalmente para módulos canónicos com contrato runtime próprio.

Módulos de Mercado já isolados no ciclo pós-auditoria incluem:

- `market-live-overlay.js`;
- `market-congress-live.js`;
- `market-portfolio-context.js`;
- `market-watch-snapshots.js`;
- `market-static-universe.js`;
- `market-dossier-signals.js`;
- `market-search-suggestions.js`;
- `market-row-ui.js`.

## Mercado e cotações

- O browser parte do snapshot estático publicado (`stocks-index.json` + shards de dossiers) e aplica dados live de forma não destrutiva.
- O dossier aberto recebe overlay de campos live; não deve ser reconstruído integralmente durante refresh de cotações.
- O Worker canónico é `https://delicate-bar-cc80.pedrossnunes.workers.dev`.
- O transporte live usa `/quote`, `/quotes` e `/market` com semântica null-safe e freshness alinhada entre browser e Worker.
- A app deve degradar para o último valor/snapshot disponível quando uma fonte live falha, sem transformar falta de dados em zero.

## Cloudflare Worker

O deployment source of truth é `wrangler.toml`, com entrada `worker-router.js`. A integração nativa Cloudflare Workers Builds publica `main` automaticamente.

Responsabilidades atuais:

- `worker.js`: quote/market transport Yahoo Finance;
- `worker-router.js`: routing adicional, health enriquecido e learned universe;
- `worker-ai-brief.js`: boundary server-side do AI Brief;
- Durable Object `LEARNED_UNIVERSE`: persistência central do universo aprendido;
- binding `AI`: Cloudflare Workers AI;
- binding `AI_BRIEF_RATE_LIMITER`: rate limiting do AI Brief por sessão da PWA.

O workflow `Verify Cloudflare Worker` valida produção depois de alterações ao Worker/configuração. O contrato inclui `/health`, quotes/market, learned universe e preflight do `/ai-brief`.

## AI Brief

O dossier tem sempre um brief determinístico local. A camada opcional `POST /ai-brief` interpreta exclusivamente o evidence layer já calculado pela Vestra.

Contratos:

- o browser não recebe chave de provider;
- produção usa Cloudflare Workers AI;
- modelo atual: `@cf/meta/llama-3.3-70b-instruct-fp8-fast`;
- resposta pedida em JSON Schema e normalizada novamente no Worker;
- missing numerics permanecem `null`;
- sem criação de novo score;
- sem instruções automáticas de comprar/vender/alocar/dimensionar posição;
- cache por ticker + SHA-256 da evidência normalizada;
- timeout curto e fallback para o brief local;
- rate limit de 12 pedidos/60 s por identificador aleatório local da sessão PWA;
- CORS limitado à origem Vestra e localhost de desenvolvimento.

O AI Brief não altera Score Vestra, Confidence, Risk Gate, valuation, Low52, Opportunity Rank, scanner, holdings ou ações da carteira.

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
- indisponibilidade do Worker preserva o snapshot aprendido anterior;
- o pipeline promove learned tickers antes dos restantes extras/portfolio names.

## Mínimos 52 semanas

Existem dois níveis intencionais:

- **Low52 intelligence:** universo de análise até aproximadamente 10% acima do mínimo de 52 semanas;
- **Mínimos 52S na UI:** shortlist visual mais estrita, até aproximadamente 5% acima do mínimo.

O motor é exclusivo de ações e exclui ETFs/fundos. O Low52 Opportunity Rank é uma camada de research e não altera o Score Vestra.

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

Workflows que escrevem dados em `main` devem preservar a estratégia de publicação/serialização para evitar perder o publish por avanço concorrente do branch remoto.

## Observabilidade

`market-data-health.js` apresenta no topo de Mercado uma faixa operacional expansível usando apenas dados já publicados: timestamp/idade do `coverage_guard`, linhas verificadas, violações, tickers aprendidos e origem do universo.

Semântica atual:

- `Operacional`: guard saudável e dados com idade <= 4 h;
- `Dados antigos`: guard saudável mas dados com idade > 4 h;
- `Atenção`: `coverage_guard.ok === false` ou existem violações;
- `Sem diagnóstico`: o guard não pôde ser carregado.

## Gates de regressão

### Architecture invariants

Protege sintaxe, reachability, identidade/cotações, storage, overlay live, learned universe, observabilidade, módulos extraídos, Worker AI Brief e a regressão histórica completa.

### Browser E2E — WebKit/iPhone

Jornadas críticas obrigatórias incluem:

- pesquisa MSFT -> dossier -> métricas -> tabs -> fechar -> reabrir;
- ETF discovery -> dossier de fundo utilizável;
- pesquisa global sintética -> dossier live -> persistência learned -> reload;
- Portfolio Intelligence: estrela separada do clique de card e alternativa -> dossier;
- dossier -> AI Brief -> handoff POST estruturado -> UI atualizada sem page errors.

### Smoke de produção

Após publicação, o GitHub Pages é testado contra um pequeno conjunto de tickers sentinela. O Worker tem verificação de produção própria e tolera a janela de propagação do deploy Cloudflare.

## Regras de evolução

1. Estabilidade e contratos de produção têm prioridade sobre novas features.
2. Não fazer refactor massivo de `app.js`/`market.js`; extrair módulos pequenos apenas quando existe fronteira clara.
3. Uma nova fonte não pode degradar proveniência nem converter ausência de dados em evidência falsa.
4. Alterações ao Score exigem evidência prospetiva madura e explicabilidade.
5. Funcionalidades críticas de iPhone/PWA precisam de cobertura WebKit quando verificáveis em browser.
6. Módulos dinâmicos devem permanecer alcançáveis pelo runtime audit e ser syntax-checked no CI.
7. Expansões do Worker devem preservar o isolamento entre quote transport, learned universe e AI Brief.
