# Vestra

Personal Finance · Market Screener · Portfolio — tudo num só lugar. PWA offline-first, dados guardados apenas no dispositivo (IndexedDB).

## Estado actual — v1.0

Chamou-se "Finva" nas primeiras horas; o nome e a identidade visual final ficaram definidos como **Vestra** — navy profundo, turquesa e dourado.

Herda toda a base funcional validada do [Património Familiar](https://github.com/possn/patrimonio-familiar) (v64za):

- Multi-classe de activos (acções/ETFs, imobiliário, metais, depósitos, fundos, cripto, obrigações, PPR)
- Balanço (entradas/saídas, categorização, granularidade diária/semanal/mensal/anual)
- Dividendos (histórico, projecção, calendário)
- FIRE, Previsão, Simulador "E se?", Juro Composto
- IRS estimado
- Import de corretoras (Trading 212, XTB) e bancos (Santander, BPI, Millennium, CGD)
- Modo Simples/Avançado
- Backup local (export/import JSON)

## Próximas fases

Integração progressiva das funcionalidades de investigação de acções, ETFs e "smart money" (insiders, Congresso dos EUA) de um segundo projecto (Finscanner). O objectivo é um "all-in-one" mais enxuto do que a análise extensa do Património Familiar — a decidir, painel a painel, o que faz sentido manter, simplificar ou não trazer.

## Stack

Vanilla HTML/CSS/JS, IndexedDB, Chart.js, Service Worker (PWA offline). Sem build step, sem dependências de servidor para as funcionalidades actuais.
