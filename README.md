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

## Vestra v1.2 — Progressive disclosure

- Dashboard reorganizado em torno de património líquido, sinais rápidos, carteira, distribuição e evolução.
- Atalhos principais: Carteira, Mercado e Adicionar ativo.
- Objetivos, fontes, snapshots, manutenção, saúde financeira, risco, fiscalidade e ferramentas avançadas preservados atrás de “Explorar património”.
- Navegação principal simplificada para Início · Carteira · Mercado · Fluxos · Mais.
- Visual global mais claro e luminoso, mantendo turquesa/dourado e linguagem premium Vestra.
- Mercado mantém carga lazy do dataset Finscanner.
