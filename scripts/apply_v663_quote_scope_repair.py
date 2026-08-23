from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
p=root/'app.js'
s=p.read_text()

start=s.find('function hasStrongQuoteIdentitySafe(asset) {')
end=s.find('function quoteSanityCheck(asset, q, priceEur, rawTicker) {', start)
assert start>=0 and end>start, 'quote identity helper block not found'
helper=r'''function hasStrongQuoteIdentitySafe(asset) {
  // Deliberately self-contained. This function is called from top-level quote
  // refresh/sanity paths, so it must never depend on helpers declared inside
  // another lexical scope.
  if (!asset) return false;

  const norm = (v) => String(v || "")
    .trim()
    .toUpperCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  const plausibleTicker = (v) => {
    const t = norm(v);
    if (!t || t.length > 24 || /\s/.test(t)) return false;
    if (!/^[A-Z0-9.^=\-]+$/.test(t)) return false;
    // A structured ticker may be one letter (e.g. Realty Income = O), but
    // never accept punctuation-only or numeric-only strings as an identity.
    return /[A-Z]/.test(t);
  };

  const cls = norm(asset.class);
  if (cls === "CRIPTO" || cls === "CRYPTO" || cls.includes("CRIPTO")) return true;

  const isin = norm(asset.isin);
  if (/^[A-Z]{2}[A-Z0-9]{9}\d$/.test(isin)) return true;

  // An explicit Yahoo/Ticker tag in notes is a strong user/broker identity.
  if (/\b(?:Ticker|Yahoo)=([A-Z0-9.\-=^]{1,24})\b/i.test(String(asset.notes || ""))) return true;

  // yahooTicker is a structured field produced by broker identity repair or
  // explicit user configuration, so a plausible value is strong evidence.
  if (plausibleTicker(asset.yahooTicker)) return true;

  // ticker/symbol is accepted only as a compact market symbol; descriptive
  // broker product names contain spaces and are rejected here.
  if (plausibleTicker(asset.ticker || asset.symbol)) return true;

  return false;
}

'''
s=s[:start]+helper+s[end:]

# Make sure this top-level helper no longer references lexical quote utilities.
block=s[s.find('function hasStrongQuoteIdentitySafe'):s.find('function quoteSanityCheck')]
for forbidden in ('normalizeTickerLookupKey','hasExplicitTickerTag','isPlausibleMarketTicker'):
    assert forbidden not in block, f'unsafe dependency remains: {forbidden}'

s=s.replace('sw.js?v=20260509v65','sw.js?v=20260509v66')
p.write_text(s)

# README + service-worker cache
p=root/'README.md'; r=p.read_text()
if not r.startswith('## Vestra v6.6.3'):
    r='''## Vestra v6.6.3 — Quote Refresh Scope Repair\n\n- Revisto o caminho completo de atualização manual e automática de cotações após o erro Safari `normalizeTickerLookupKey is not defined`.\n- O validador de identidade usado pelo refresh é agora totalmente autocontido e não depende de helpers em scopes internos.\n- Mantém validação conservadora: ISIN, yahooTicker/ticker estruturado, tags explícitas e rejeição de nomes descritivos de produtos como tickers.\n- Manual e automático continuam a usar o mesmo `refreshLiveQuotesCore()`.\n- Adicionado smoke test de execução do helper, além de `node --check`.\n- PWA cache: `vestra-cache-v66`.\n\n'''+r
p.write_text(r)

p=root/'sw.js'; sw=p.read_text().replace('vestra-cache-v65','vestra-cache-v66'); p.write_text(sw)
