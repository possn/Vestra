from pathlib import Path
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'app-runtime-bridge.js'
UPDATE = ROOT / 'app-update-manager.js'
BOOTSTRAP = ROOT / 'market-company-brief.js'
GLOBAL = ROOT / 'market-global-search.js'
LEARNED = ROOT / 'market-learned-universe.js'


class MarketRuntimeBridgeAndUpdateTests(unittest.TestCase):
    def test_new_modules_are_valid_javascript(self):
        for path in (BRIDGE, UPDATE, BOOTSTRAP, GLOBAL, LEARNED):
            subprocess.run(['node', '--check', str(path)], check=True, cwd=ROOT)

    def test_runtime_bridge_exposes_lexical_state_read_only(self):
        script = textwrap.dedent(f"""
            const fs=require('fs');
            global.window=global;
            let state={{settings:{{workerUrl:'https://worker.example'}}}};
            eval(fs.readFileSync({str(BRIDGE)!r},'utf8'));
            if(window.state.settings.workerUrl!=='https://worker.example') process.exit(11);
            state={{settings:{{workerUrl:'https://worker2.example'}}}};
            if(window.state.settings.workerUrl!=='https://worker2.example') process.exit(12);
            const d=Object.getOwnPropertyDescriptor(window,'state');
            if(!d || typeof d.get!=='function' || d.set) process.exit(13);
        """)
        subprocess.run(['node', '-e', script], check=True, cwd=ROOT)

    def test_global_search_can_use_runtime_worker_state(self):
        text = GLOBAL.read_text(encoding='utf-8')
        self.assertIn('window.state?.settings?.workerUrl', text)
        bridge = BRIDGE.read_text(encoding='utf-8')
        self.assertIn('https://delicate-bar-cc80.pedrossnunes.workers.dev', bridge)
        boot = BOOTSTRAP.read_text(encoding='utf-8')
        self.assertIn("app-runtime-bridge.js?v=1.1", boot)
        self.assertIn('loadRuntimeBridge()', boot)
        self.assertIn('loadLearnedUniverse();loadAppUpdateManager();', boot)
        self.assertIn('window.VestraLearnedUniverse,loadGlobalMarketSearch', boot)
        self.assertLess(boot.index('loadLearnedUniverse();'), boot.index('loadAppUpdateManager();'))

    def test_force_update_does_not_unregister_sw_or_wipe_caches(self):
        text = UPDATE.read_text(encoding='utf-8')
        self.assertIn('reg?.update?.()', text)
        self.assertIn('window.location.replace', text)
        self.assertIn("document.addEventListener('click', captureForceUpdate, true)", text)
        self.assertIn('event.stopImmediatePropagation()', text)
        self.assertNotIn('appLoadingOverlay', text)
        self.assertNotIn('.unregister()', text)
        self.assertNotIn('caches.delete', text)
        self.assertNotIn('getRegistrations()', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
