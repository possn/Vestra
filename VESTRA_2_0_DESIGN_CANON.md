# VESTRA 2.0 — DESIGN CANÓNICO APROVADO

## Referência inequívoca
O utilizador aprovou explicitamente a **segunda imagem dark premium** gerada no chat de 9 outubro 2026 como direção do Dashboard. A experiência final deve seguir **esta imagem**, não apenas adoptar as suas cores. Apple × Claude editorial, rigor financeiro, simplicidade funcional.

## Princípios visuais
- Uma **única Home**, não uma Home Intelligence sobreposta ao Dashboard clássico.
- Fundo quase preto com subtom verde-carvão/petróleo (#081a1a como referência aproximada); superfícies profundas ligeiramente diferenciadas, marfim quente, acentos verde-água dessaturado e dourado discreto. Vermelho apenas para risco/perda.
- Cabeçalho compacto **Vestra**, pesquisa e adicionar; serif editorial nos títulos, sans clean nos dados e controlos; contraste WCAG e grande legibilidade em iPhone; ritmo visual variado, cartões contidos com raio coerente, sem grandes áreas vazias.
- Hierarquia de topo: “O que importa hoje” → **património líquido real** (com privacidade existente) → três acessos imediatos **Barómetro / Notícias / Eventos** → barómetro com pontuação validada e AAII distinguido do proxy de preço → eventos da semana → saúde/risco da carteira → notícias do dia → detalhe/decisões.
- Card de património compacto, sem inventar gráfico, ganhos nem períodos; só mostrar valores, variações e séries se o motor existente tiver dados reais verificados.
- Informação ausente/antiga/insuficiente é declarada honestamente (fail-closed); nunca substituir dados reais por números da imagem de referência.
- Preservar módulos completos: Barómetro com evolução, AAII e metodologia; Notícias com fontes, filtros, ligações e relevância; Agenda com navegação semanal, calendário e detalhe; Carteira, Dossiers, Fluxos, Cripto, imports XTB/T212 e inteligência financeira.
- Responsive de qualidade tanto para iPhone/WebKit como desktop; reduzir duplicações, não eliminar funcionalidades.

## Regras de engenharia
Repo possn/Vestra. “Segue” significa commits, PRs, testes e merge reais. Partir do main atual; não mexer no motor de cotações sem bug. Sem novos MutationObservers. Antes de merge: mesmo head SHA com três gates verdes (Runtime JS, Architecture invariants, Browser E2E/WebKit); confirmar PR aberto, mergeable true, behind 0, base/main inalterados e expected_head_sha. Qualquer alteração depois do verde obriga a repetir.
O Dashboard clássico poderá permanecer como fallback temporário via ?vestra2=0 durante migração, mas **não deve aparecer empilhado nem duplicado**. A experiência final tem de ser uma Home única.

## Estado inicial desta implementação
PR #1058 inicia a migração: layout dark compacto, indicadores de património lidos dos hosts existentes, privacidade delegada no controlo atual, três acessos úteis reais. É apenas a primeira fase, **não se deve declarar pixel-perfect até validação visual real**.
