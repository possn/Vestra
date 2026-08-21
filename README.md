
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
