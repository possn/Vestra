from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# 1) Client batching: use the Worker's batch endpoint efficiently without opening
# a large number of Safari connections.
client_path = Path("app-market-client.js")
client = client_path.read_text(encoding="utf-8")
client = replace_once(client, "const BATCH_QUOTE_TIMEOUT_MS = 18000;", "const BATCH_QUOTE_TIMEOUT_MS = 12000;", "batch timeout")
client = replace_once(client, "const BATCH_CHUNK_SIZE = 4;", "const BATCH_CHUNK_SIZE = 12;", "batch size")
client_path.write_text(client, encoding="utf-8")


# 2) Worker upstream timeout: one slow Yahoo endpoint must not hold an entire batch
# open until the browser-side 12/18 second timeout.
worker_path = Path("worker.js")
worker = worker_path.read_text(encoding="utf-8")
old_fetch = '''async function fetchJsonMaybe(url, init) {
  const resp = await fetch(url, init);
  if (!resp.ok) return null;
  try { return await resp.json(); } catch (_) { return null; }
}'''
new_fetch = '''async function fetchJsonMaybe(url, init = {}, timeoutMs = 3500) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.max(1000, Number(timeoutMs) || 3500));
  try {
    const resp = await fetch(url, { ...init, signal: controller.signal });
    if (!resp.ok) return null;
    try { return await resp.json(); } catch (_) { return null; }
  } catch (_) {
    return null;
  } finally {
    clearTimeout(timer);
  }
}'''
worker = replace_once(worker, old_fetch, new_fetch, "Yahoo upstream timeout")
worker_path.write_text(worker, encoding="utf-8")


# 3) Portfolio identity: exact ISIN and broker-qualified symbols are authoritative.
# This specifically prevents AI->AI.PA (C3.ai/Air Liquide), RR->RR.L
# (Richtech/Rolls-Royce), RDW.US->RDW.L, TROX.US->TROX.L, etc.
app_path = Path("app.js")
app = app_path.read_text(encoding="utf-8")
needle = '''    const raw = getRawTickerForAsset(asset);
    const isin = String(asset.isin || "").trim().toUpperCase();
    const storedYahoo = getStoredYahooTicker(asset);'''
insert = '''    const raw = getRawTickerForAsset(asset);
    const isin = String(asset.isin || "").trim().toUpperCase();
    const storedYahoo = getStoredYahooTicker(asset);

    // Quote Engine v2: authoritative identity must win before any exchange-suffix guessing.
    // T212 exports provide ISIN; XTB exports provide exchange-qualified symbols such as
    // RDW.US / 4BRZ.DE. A guessed venue is never safer than either of those identities.
    const exactIsinYahoo = isin && ISIN_YAHOO_MAP[isin] ? String(ISIN_YAHOO_MAP[isin]).trim().toUpperCase() : "";
    if (exactIsinYahoo) {
      push(exactIsinYahoo);
      return out;
    }
    const rawBroker = String(raw || "").trim().toUpperCase();
    const usBroker = rawBroker.match(/^(.+)\\.US$/);
    if (usBroker && usBroker[1]) {
      push(usBroker[1]);
      return out;
    }
    if (/\\.(?:DE|PA|AS|MC|MI|L|LS|SW|VI|TO|ST|CO|OL|HE|AX|F|IR)$/.test(rawBroker)) {
      push(rawBroker);
      return out;
    }'''
app = replace_once(app, needle, insert, "identity guard insertion")

# 4) One-time migration away from corrupted legacy price history. Older history did
# not record which Yahoo symbol produced a price, so an old AI.PA price can live under
# the local key AI. When the new quote is backed by exact ISIN or broker venue, ignore
# that un-attributed legacy baseline once and establish a clean baseline.
old_prev = '''    const prev = [...hist].reverse().find(h => h && h.date !== today && Number.isFinite(Number(h.priceEur)) && Number(h.priceEur) > 0);
    historical = prev ? Number(prev.priceEur) : 0;
  } catch(_) {}
  const prevIdentity = String(previousYahooTicker || "").trim().toUpperCase();
  const nextIdentity = String(rawTicker || "").trim().toUpperCase();
  const identityChanged = !!(prevIdentity && nextIdentity && prevIdentity !== nextIdentity && explicit);
  // A corrected venue/ticker must not be compared to a price stored under the old identity.
  // The new quote still passed ticker/ISIN resolution and currency guards; from the next refresh
  // onward it becomes the new historical baseline.
  const ref = identityChanged ? 0 : (historical > 0 ? historical : baseline);'''
new_prev = '''    const prev = [...hist].reverse().find(h => h && h.date !== today && Number.isFinite(Number(h.priceEur)) && Number(h.priceEur) > 0);
    historical = prev ? Number(prev.priceEur) : 0;
    var legacyHistoryWithoutIdentity = !!(prev && !String(prev.quoteTicker || "").trim());
  } catch(_) {}
  const prevIdentity = String(previousYahooTicker || "").trim().toUpperCase();
  const nextIdentity = String(rawTicker || "").trim().toUpperCase();
  const identityChanged = !!(prevIdentity && nextIdentity && prevIdentity !== nextIdentity && explicit);
  const isinKey = String(asset && asset.isin || "").trim().toUpperCase();
  const exactIsinIdentity = isinKey && ISIN_YAHOO_MAP[isinKey]
    ? String(ISIN_YAHOO_MAP[isinKey]).trim().toUpperCase() : "";
  const localIdentity = String(getRawTickerForAsset(asset) || "").trim().toUpperCase();
  const brokerAuthoritative = localIdentity.endsWith(".US")
    ? nextIdentity === localIdentity.slice(0, -3)
    : (/\\.(?:DE|PA|AS|MC|MI|L|LS|SW|VI|TO|ST|CO|OL|HE|AX|F|IR)$/.test(localIdentity) && nextIdentity === localIdentity);
  const authoritativeLegacyRepair = !!(legacyHistoryWithoutIdentity && explicit &&
    ((exactIsinIdentity && nextIdentity === exactIsinIdentity) || brokerAuthoritative));
  // A corrected/authoritative identity must not be compared to an unattributed legacy price.
  // The accepted quote becomes the new baseline and subsequent history carries quoteTicker.
  const ref = (identityChanged || authoritativeLegacyRepair) ? 0 : (historical > 0 ? historical : baseline);'''
app = replace_once(app, old_prev, new_prev, "legacy price-history migration")

old_entry = '''      const entry  = { date: isoNow, priceEur: +priceEur.toFixed(6), priceLoc: +(locPrice||priceEur).toFixed(6), ccy };'''
new_entry = '''      const entry  = { date: isoNow, priceEur: +priceEur.toFixed(6), priceLoc: +(locPrice||priceEur).toFixed(6), ccy, quoteTicker: String(q.ticker || raw || "").trim().toUpperCase() };'''
app = replace_once(app, old_entry, new_entry, "price history quote identity")
app_path.write_text(app, encoding="utf-8")

print("Quote Engine v2 hotfix applied")
