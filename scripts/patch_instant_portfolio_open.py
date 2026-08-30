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
    "/* Vestra Market Data Loader v2.2 — instant dossier opening + background hydration. */",
    "/* Vestra Market Data Loader v2.3 — instant dossier/portfolio opening + background hydration. */",
    "loader header",
)
loader = replace_once(
    loader,
    """    if(portfolio){
      e.preventDefault(); e.stopImmediatePropagation();
      hydratePortfolio().finally(()=>{
        bypassClick=true;
        try{ portfolio.click(); } finally { bypassClick=false; }
      });
    }""",
    """    if(portfolio){
      e.preventDefault(); e.stopImmediatePropagation();
      // Portfolio navigation must never wait for every company shard. Open first,
      // then hydrate holdings opportunistically in the background.
      bypassClick=true;
      try{ portfolio.click(); } finally { bypassClick=false; }
      hydratePortfolio().catch(()=>{});
    }""",
    "portfolio click block",
)
loader = replace_once(loader, "version:'2.2'", "version:'2.3'", "loader version")
loader_path.write_text(loader, encoding="utf-8")

index_path = Path("index.html")
index = index_path.read_text(encoding="utf-8")
index = replace_once(
    index,
    "market-data-loader.js?v=2.2",
    "market-data-loader.js?v=2.3",
    "index cache buster",
)
index_path.write_text(index, encoding="utf-8")

test_path = Path("tests/test_market_loader_invariants.py")
test = test_path.read_text(encoding="utf-8")
test = replace_once(
    test,
    "market-data-loader.js?v=2.2",
    "market-data-loader.js?v=2.3",
    "test cache buster",
)
test = replace_once(test, "version:'2.2'", "version:'2.3'", "test loader version")
anchor = "    def test_dossier_opening_delegates_to_canonical_navigation(self):\n"
new_test = '''    def test_portfolio_tool_opens_before_background_hydration(self):
        loader = read("market-data-loader.js")
        start = loader.index("const portfolio=e.target.closest?.('[data-market-tool=\\\"portfolio\\\"]')")
        end = loader.index("\\n    }", start) + len("\\n    }")
        block = loader[start:end]
        self.assertIn("portfolio.click()", block)
        self.assertIn("hydratePortfolio().catch(()=>{})", block)
        self.assertLess(block.index("portfolio.click()"), block.index("hydratePortfolio().catch(()=>{})"))
        self.assertNotIn("hydratePortfolio().finally", block)

'''
if new_test not in test:
    if anchor not in test:
        raise SystemExit("test anchor missing")
    test = test.replace(anchor, new_test + anchor, 1)
test_path.write_text(test, encoding="utf-8")
