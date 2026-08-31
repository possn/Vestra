from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / 'worker-router.js'
WRANGLER = ROOT / 'wrangler.toml'
GLOBAL = ROOT / 'market-global-search.js'
LEARNED = ROOT / 'market-learned-universe.js'
BOOT = ROOT / 'market-company-brief.js'
WORKFLOW = ROOT / '.github/workflows/update-market-data.yml'
SYNC = ROOT / 'scripts/sync_learned_universe.py'
SEED = ROOT / 'data/learned_tickers.json'


class LearnedUniverseTests(unittest.TestCase):
    def test_router_is_valid_and_uses_durable_object(self):
        subprocess.run(['node', '--check', str(ROUTER)], check=True, cwd=ROOT)
        router = ROUTER.read_text(encoding='utf-8')
        wrangler = WRANGLER.read_text(encoding='utf-8')
        self.assertIn("export class LearnedUniverse", router)
        self.assertIn("'/learned-universe'", router)
        self.assertIn("validateLearnedTicker", router)
        self.assertIn("marketWorker.fetch", router)
        self.assertIn("main = \"worker-router.js\"", wrangler)
        self.assertIn("name = \"LEARNED_UNIVERSE\"", wrangler)
        self.assertIn("new_sqlite_classes = [\"LearnedUniverse\"]", wrangler)

    def test_browser_learns_locally_and_centrally(self):
        subprocess.run(['node', '--check', str(GLOBAL)], check=True, cwd=ROOT)
        subprocess.run(['node', '--check', str(LEARNED)], check=True, cwd=ROOT)
        global_js = GLOBAL.read_text(encoding='utf-8')
        boot = BOOT.read_text(encoding='utf-8')
        self.assertIn("/learned-universe", global_js)
        self.assertIn("method:'POST'", global_js)
        self.assertIn("learnedApi()?.upsert", global_js)
        self.assertIn("market-learned-universe.js?v=1.0", boot)
        self.assertIn("market-global-search.js?v=1.2", boot)
        self.assertLess(boot.index('loadLearnedUniverse();'), boot.index('loadAppUpdateManager();'))

    def test_pipeline_sync_runs_before_heavy_pipeline(self):
        workflow = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('scripts/sync_learned_universe.py', workflow)
        self.assertIn('name: Sync learned search universe', workflow)
        self.assertLess(workflow.index('name: Sync learned search universe'), workflow.index('name: Run pipeline'))

    def test_sync_preserves_snapshot_and_promotes_to_extra_universe(self):
        spec = importlib.util.spec_from_file_location('sync_learned_universe', SYNC)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mod.EXTRA_PATH = tmp / 'extra_tickers.json'
            mod.SNAPSHOT_PATH = tmp / 'learned_tickers.json'
            mod.EXTRA_PATH.write_text(json.dumps({'tickers':['AAPL'],'active_positions':1}), encoding='utf-8')
            mod.SNAPSHOT_PATH.write_text(json.dumps({'rows':[{
                'ticker':'TKR','name':'The Timken Company','quote_type':'EQUITY','validation_count':1
            }]}), encoding='utf-8')
            mod.fetch_remote_rows = lambda: [{
                'ticker':'MSFT','name':'Microsoft','exchange':'NMS','currency':'USD','quote_type':'EQUITY',
                'sector':'Technology','industry':'Software','country':'United States','first_seen':'','last_seen':'',
                'validation_count':2,
            }]
            mod.main()
            extra = json.loads(mod.EXTRA_PATH.read_text(encoding='utf-8'))
            snapshot = json.loads(mod.SNAPSHOT_PATH.read_text(encoding='utf-8'))
            self.assertEqual(extra['tickers'], ['AAPL','MSFT','TKR'])
            self.assertEqual(snapshot['count'], 2)
            self.assertEqual({r['ticker'] for r in snapshot['rows']}, {'MSFT','TKR'})

    def test_tkr_seed_survives_first_central_sync(self):
        payload = json.loads(SEED.read_text(encoding='utf-8'))
        self.assertIn('TKR', {r['ticker'] for r in payload.get('rows', [])})


if __name__ == '__main__':
    unittest.main(verbosity=2)
