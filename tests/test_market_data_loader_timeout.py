import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MarketDataLoaderTimeoutTests(unittest.TestCase):
    def run_node(self, body: str):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({str(ROOT / 'market-data-loader.js')!r}, 'utf8');
            {body}
            """
        )
        return subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

    def test_manifest_timeout_converges_and_next_hydration_retries(self):
        result = self.run_node(
            """
            const stock = { ticker: 'AAPL' };
            let fetchCalls = 0;
            const context = {
              window: {
                fetch: async (url) => {
                  fetchCalls += 1;
                  if (fetchCalls === 1) return await new Promise(() => {});
                  if (String(url).includes('dossiers-manifest')) {
                    return { ok: true, status: 200, json: async () => ({ tickers: { AAPL: 'A' } }) };
                  }
                  return { ok: true, status: 200, json: async () => ({ stocks: { AAPL: { ticker: 'AAPL', name: 'Apple' } } }) };
                },
                VestraMarket: {
                  resolvePortfolioStock() { return stock; },
                },
              },
              document: {
                addEventListener() {},
                getElementById() { return null; },
              },
              performance: { now: () => Date.now() },
              requestAnimationFrame(fn) { fn(); },
              setInterval,
              clearInterval,
              setTimeout(fn, ms) { return setTimeout(fn, ms === 5000 ? 5 : ms); },
              clearTimeout,
              Promise,
              Map,
              Set,
              Object,
              String,
              Number,
              Date,
              Math,
              console,
              encodeURIComponent,
            };
            vm.createContext(context);
            vm.runInContext(source, context, { filename: 'market-data-loader.js' });
            (async () => {
              const started = Date.now();
              const first = await context.window.VestraMarketData.hydrateTicker('AAPL');
              const elapsed = Date.now() - started;
              if (first !== stock) throw new Error('timeout must preserve startup index stock');
              if (!String(stock._dossierHydrationError || '').includes('timeout')) {
                throw new Error(`timeout error was not surfaced: ${stock._dossierHydrationError}`);
              }
              if (elapsed > 500) throw new Error(`hung manifest did not converge promptly: ${elapsed}ms`);

              const second = await context.window.VestraMarketData.hydrateTicker('AAPL');
              if (second !== stock || !stock._dossierHydrated || stock.name !== 'Apple') {
                throw new Error('second hydration did not retry and complete');
              }
              if (fetchCalls !== 3) throw new Error(`expected manifest timeout + manifest retry + shard fetch, got ${fetchCalls}`);
            })().catch(error => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_shard_timeout_converges_and_cache_does_not_poison_retry(self):
        result = self.run_node(
            """
            const stock = { ticker: 'MSFT', dossier_shard: 'M' };
            let fetchCalls = 0;
            const context = {
              window: {
                fetch: async () => {
                  fetchCalls += 1;
                  if (fetchCalls === 1) return await new Promise(() => {});
                  return { ok: true, status: 200, json: async () => ({ stocks: { MSFT: { ticker: 'MSFT', name: 'Microsoft' } } }) };
                },
                VestraMarket: {
                  resolvePortfolioStock() { return stock; },
                },
              },
              document: {
                addEventListener() {},
                getElementById() { return null; },
              },
              performance: { now: () => Date.now() },
              requestAnimationFrame(fn) { fn(); },
              setInterval,
              clearInterval,
              setTimeout(fn, ms) { return setTimeout(fn, ms === 5000 ? 5 : ms); },
              clearTimeout,
              Promise,
              Map,
              Set,
              Object,
              String,
              Number,
              Date,
              Math,
              console,
              encodeURIComponent,
            };
            vm.createContext(context);
            vm.runInContext(source, context, { filename: 'market-data-loader.js' });
            (async () => {
              await context.window.VestraMarketData.hydrateTicker('MSFT');
              if (!String(stock._dossierHydrationError || '').includes('timeout')) {
                throw new Error(`shard timeout was not surfaced: ${stock._dossierHydrationError}`);
              }
              await context.window.VestraMarketData.hydrateTicker('MSFT');
              if (!stock._dossierHydrated || stock.name !== 'Microsoft') {
                throw new Error('timed-out shard remained poisoned in cache');
              }
              if (fetchCalls !== 2) throw new Error(`expected shard timeout + retry, got ${fetchCalls}`);
            })().catch(error => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_timeout_contract_is_centralized(self):
        source = (ROOT / "market-data-loader.js").read_text(encoding="utf-8")
        self.assertIn("const MARKET_DATA_FETCH_TIMEOUT_MS = 5000", source)
        self.assertIn("async function fetchWithTimeout", source)
        self.assertGreaterEqual(source.count("await fetchWithTimeout("), 2)
        self.assertNotIn("await originalFetch('data/dossiers-manifest.json'", source)


if __name__ == "__main__":
    unittest.main()
