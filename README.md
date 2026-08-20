# Finva

Net worth, investimentos e — em breve — investigação financeira, num só lugar. PWA offline-first, dados guardados apenas no dispositivo (IndexedDB).

## Estado actual — v1.0 (Fase 1)

A Finva nasce a partir do [Património Familiar](https://github.com/possn/patrimonio-familiar) (v64za), com toda a base funcional já validada:

- Multi-classe de activos (acções/ETFs, imobiliário, metais, depósitos, fundos, cripto, obrigações, PPR)
- Balanço (entradas/saídas, categorização, granularidade diária/semanal/mensal/anual)
- Dividendos (histórico, projecção, calendário)
- FIRE, Previsão, Simulador "E se?", Juro Composto
- IRS estimado
- Import de corretoras (Trading 212, XTB) e bancos (Santander, BPI, Millennium, CGD)
- Modo Simples/Avançado
- Backup local (export/import JSON)

Identidade visual nova (paleta creme + coral + sálvia, inspirada na app "Lume"), mesma base técnica sólida por baixo.

## Próximas fases

Este repositório vai integrar progressivamente as funcionalidades de investigação de acções, ETFs e "smart money" (insiders, Congresso dos EUA) de um segundo projecto, mantendo o net worth tracking como base. Cada fase é entregue e testada separadamente.

## Stack

Vanilla HTML/CSS/JS, IndexedDB, Chart.js, Service Worker (PWA offline). Sem build step, sem dependências de servidor para as funcionalidades actuais.
