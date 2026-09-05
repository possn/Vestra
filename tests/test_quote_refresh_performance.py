from pathlib import Path
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAST = ROOT / "quote-refresh-performance.js"
BOOTSTRAP = ROOT / "market-company-brief.js"


class QuoteRefreshPerformanceTests(unittest.TestCase):
    def test_runtime_module_is_valid_javascript(self):
        subprocess.run(["node", "--check", str(FAST)], check=True, cwd=ROOT)

    def test_fast_lane_uses_worker_batches_and_preserves_fallback(self):
        script = textwrap.dedent(f"""
            const fs = require('fs');
            (async () => {{
              global.window = global;
              global.document = {{
                getElementById: id => id === 'settingsWorkerUrl' ? {{value:'https://worker.example'}} : null,
                addEventListener: () => {{}}
              }};
              global.performance = {{ now: (() => {{ let n=0; return () => ++n; }})() }};
              const calls = [];
              global.fetch = async (url) => {{
                calls.push(String(url));
                const u = new URL(url);
                if (u.pathname !== '/quotes') throw new Error('unexpected endpoint');
                const tickers = u.searchParams.get('tickers').split(',');
                const body = {{}};
                for (const t of tickers) {{
                  if (t === 'MISS') body[t] = {{ticker:t,error:'Sem cotação exata disponível'}};
                  else body[t] = {{ticker:t,price:100,currency:'USD'}};
                }}
                return {{ok:true,status:200,json:async()=>body}};
              }};
              window.mapWithConcurrency = async (items, limit, worker) => {{
                const out=[];
                for (const item of items) {{
                  try {{ out.push({{status:'fulfilled',value:await worker(item)}}); }}
                  catch (reason) {{ out.push({{status:'rejected',reason}}); }}
                }}
                return out;
              }};
              eval(fs.readFileSync({str(FAST)!r}, 'utf8'));
              if (!window.mapWithConcurrency.__vestraQuoteFastLane) process.exit(10);

              const items = Array.from({{length:41}}, (_,i) => ({{asset:{{ticker:'T'+i}},candidates:[i===40?'MISS':'T'+i]}}));
              let fallbackCalls = 0;
              const fallback = async item => {{
                fallbackCalls++;
                if (item.candidates[0] !== 'MISS') throw new Error('unexpected fallback');
                return {{yahoo:'MISS',quote:{{ticker:'MISS',price:55,currency:'USD'}},attempts:2,durationMs:5}};
              }};
              const result = await window.mapWithConcurrency(items,8,fallback);
              if (result.length !== 41) process.exit(11);
              if (calls.length !== 3) process.exit(12);
              if (!calls.every(x => x.includes('/quotes?tickers='))) process.exit(13);
              if (fallbackCalls !== 1) process.exit(14);
              if (result[0].status !== 'fulfilled' || !result[0].value.fastBatch) process.exit(15);
              if (result[40].status !== 'fulfilled' || result[40].value.quote.price !== 55) process.exit(16);
            }})().catch(err => {{ console.error(err); process.exit(99); }});
        """)
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_contract_keeps_batch_shape_small_and_parallel(self):
        text = FAST.read_text(encoding="utf-8")
        self.assertIn("const BATCH_SIZE = 20", text)
        self.assertIn("const BATCH_CONCURRENCY = 10", text)
        self.assertIn("/quotes?tickers=", text)
        self.assertIn("fallbackItems", text)
        self.assertNotIn("Promise.all(items.map", text)

    def test_bootstrap_loads_fast_lane_after_app_runtime_exists(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("loadQuoteRefreshPerformance();", text)
        self.assertIn("quote-refresh-performance.js?v=1.0", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
