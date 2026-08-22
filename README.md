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
