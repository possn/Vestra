from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def one(path, old, new):
    p=ROOT/path; s=p.read_text(encoding='utf-8')
    if new in s: return
    if old not in s: raise RuntimeError(f'anchor missing: {path}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')

one('index.html','<div class="sidebar__sub">v3.9</div>','<div class="sidebar__sub">v4.0</div>')
one('index.html','Vestra <b>v3.9</b>','Vestra <b>v4.0</b>')

p=ROOT/'market.js'; s=p.read_text(encoding='utf-8')
a="${Array.isArray(s.data_sources)&&s.data_sources.length?`<p class=\"market-case-note\" style=\"margin-top:8px\">Fontes: ${s.data_sources.map(esc).join(' · ')}</p>`:''}</div>`;"
b="${Array.isArray(s.data_sources)&&s.data_sources.length?`<p class=\"market-case-note\" style=\"margin-top:8px\">Fontes: ${s.data_sources.map(esc).join(' · ')}</p>`:''}${s.identity_source?`<p class=\"market-case-note\" style=\"margin-top:6px\">Identidade: ${esc(s.identity_source)}${s.isin?' · ISIN '+esc(s.isin):''}${s.lei?' · LEI '+esc(s.lei):''}</p>`:''}</div>`;"
if b not in s:
    if a not in s: raise RuntimeError('market provenance anchor missing')
    p.write_text(s.replace(a,b,1),encoding='utf-8')

one('scripts/run.py','from sec_enrich import enrich as enrich_sec\n','from sec_enrich import enrich as enrich_sec\nfrom esef_enrich import enrich as enrich_esef\n')
one('scripts/run.py','"fundamentals", "sec_enrich", "analyst"','"fundamentals", "sec_enrich", "esef_enrich", "analyst"')
one('scripts/run.py','    raw = enrich_sec(raw, priority=portfolio_set)\n    scored = score_universe(raw)\n','    raw = enrich_sec(raw, priority=portfolio_set)\n    raw = enrich_esef(raw, priority=portfolio_set)\n    scored = score_universe(raw)\n')
one('scripts/run.py','        if rm is not None and getattr(rm, "sec_edgar_enriched", False): row["data_sources"].append("SEC EDGAR")\n        if analyst:','        if rm is not None and getattr(rm, "sec_edgar_enriched", False): row["data_sources"].append("SEC EDGAR")\n        if rm is not None and getattr(rm, "esef_enriched", False):\n            row["data_sources"].append("ESEF / filings.xbrl.org")\n            row["identity_source"] = "GLEIF/ANNA ISIN→LEI"\n            row["isin"] = getattr(rm, "isin", None)\n            row["lei"] = getattr(rm, "lei", None)\n            row["esef_period_end"] = getattr(rm, "esef_period_end", None)\n        if analyst:')

one('.github/workflows/update-market-data.yml','      - name: Run pipeline\n        working-directory: scripts\n        run: python run.py\n','      - name: Run pipeline\n        working-directory: scripts\n        env:\n          SEC_USER_AGENT: "Vestra/4.0 (+https://github.com/possn/Vestra)"\n        run: python run.py\n')

p=ROOT/'README.md'; s=p.read_text(encoding='utf-8')
head='''## Vestra v4.0 — European Source Fusion\n\n- Layout visual permanece congelado.\n- Cadeia europeia estrita: `ticker → ISIN → GLEIF/ANNA LEI → ESEF/UKSEF`.\n- Sem fuzzy matching por nome de empresa: qualquer identidade ambígua é ignorada.\n- xBRL-JSON oficial preenche apenas fundamentais em falta deixados pelo Yahoo.\n- Dossiers podem expor ISIN/LEI e provenance da identidade quando o enriquecimento ESEF é usado.\n- SEC EDGAR passa a estar efetivamente ativo no pipeline automático com User-Agent identificável.\n- Alemanha e Irlanda ficam deliberadamente fora do enrichment automático enquanto persistirem lacunas documentadas de discovery no índice público.\n- PWA cache: `vestra-cache-v33`.\n\n'''
if not s.startswith('## Vestra v4.0'): p.write_text(head+s,encoding='utf-8')

p=ROOT/'DATA_SOURCES.md'; s=p.read_text(encoding='utf-8')
append='''\n\n## v4.0 — European Source Fusion\n- **GLEIF / ANNA ISIN→LEI**: resolução certificada de identidade jurídica a partir do ISIN.\n- **filings.xbrl.org**: filings ESEF/UKSEF e xBRL-JSON, usados apenas após resolução exata para LEI.\n- Hierarquia: preço/consenso continuam no feed de mercado; filings oficiais têm prioridade apenas para preencher contas históricas ausentes.\n- Alemanha/Irlanda: sem enrichment automático por lacunas conhecidas do índice público; a Vestra mantém o dado como ausente em vez de adivinhar.\n'''
if '## v4.0 — European Source Fusion' not in s: p.write_text(s+append,encoding='utf-8')

one('sw.js','/* Vestra — Service Worker v3.9 */','/* Vestra — Service Worker v4.0 */')
one('sw.js','const CACHE_NAME = "vestra-cache-v32";','const CACHE_NAME = "vestra-cache-v33";')
