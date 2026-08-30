from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


loader_path = Path("market-data-loader.js")
loader = loader_path.read_text(encoding="utf-8")
loader = replace_once(
    loader,
    "/* Vestra Market Data Loader v2.3 — instant dossier/portfolio opening + background hydration. */",
    "/* Vestra Market Data Loader v2.4 — instant navigation + bounded background hydration. */",
    "loader header",
)
old = """    await Promise.allSettled(tickers.map(hydrateTicker));
  }"""
new = """    // Keep background enrichment gentle on Safari/iPhone. Shards are large and
    // launching the whole portfolio at once can create a burst of network + JSON work.
    const queue=[...tickers];
    const workerCount=Math.min(2,queue.length);
    const workers=Array.from({length:workerCount},async()=>{
      while(queue.length){
        const ticker=queue.shift();
        if(!ticker) break;
        try{ await hydrateTicker(ticker); }catch(_){}
      }
    });
    await Promise.allSettled(workers);
  }"""
loader = replace_once(loader, old, new, "portfolio hydration fan-out")
loader = replace_once(loader, "version:'2.3'", "version:'2.4'", "loader version")
loader_path.write_text(loader, encoding="utf-8")

index_path = Path("index.html")
index = index_path.read_text(encoding="utf-8")
index = replace_once(index, "market-data-loader.js?v=2.3", "market-data-loader.js?v=2.4", "index cache buster")
index_path.write_text(index, encoding="utf-8")

test_path = Path("tests/test_market_loader_invariants.py")
test = test_path.read_text(encoding="utf-8")
test = replace_once(test, "market-data-loader.js?v=2.3", "market-data-loader.js?v=2.4", "test cache buster")
test = replace_once(test, "version:'2.3'", "version:'2.4'", "test loader version")
anchor = "    def test_dossier_opening_delegates_to_canonical_navigation(self):\n"
new_test = '''    def test_portfolio_background_hydration_is_bounded(self):
        loader = read("market-data-loader.js")
        start = loader.index("async function hydratePortfolio()")
        end = loader.index("\\n  function installApiWrapper", start)
        block = loader[start:end]
        self.assertIn("const workerCount=Math.min(2,queue.length)", block)
        self.assertIn("await hydrateTicker(ticker)", block)
        self.assertNotIn("tickers.map(hydrateTicker)", block)

'''
if new_test not in test:
    if anchor not in test:
        raise SystemExit("test anchor missing")
    test = test.replace(anchor, new_test + anchor, 1)
test_path.write_text(test, encoding="utf-8")

native_path = Path("tests/test_native_market_loading.py")
native = native_path.read_text(encoding="utf-8")
native = replace_once(native, "version:'2.3'", "version:'2.4'", "native loader version")
native_path.write_text(native, encoding="utf-8")
