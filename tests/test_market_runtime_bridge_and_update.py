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
APP = ROOT / 'app.js'
INDEX = ROOT / 'index.html'


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
        self.assertIn("app-update-manager.js?v=1.5", boot)
        self.assertIn('loadAppUpdateManager();loadLearnedUniverse();', boot)
        self.assertIn('window.VestraLearnedUniverse,loadGlobalMarketSearch', boot)
        self.assertLess(boot.index('loadAppUpdateManager();'), boot.index('loadLearnedUniverse();'))

    def test_force_update_is_navigation_only_and_never_wipes_runtime(self):
        text = UPDATE.read_text(encoding='utf-8')
        app = APP.read_text(encoding='utf-8')
        index = INDEX.read_text(encoding='utf-8')
        self.assertNotIn('serviceWorker', text)
        self.assertNotIn('getRegistration()', text)
        self.assertIn('window.location.replace', text)
        self.assertIn("document.getElementById('btnForceUpdate')", text)
        self.assertIn('current.cloneNode(true)', text)
        self.assertIn('current.replaceWith(button)', text)
        self.assertIn("document.addEventListener('click'", text)
        self.assertIn("}, true);", text)
        self.assertIn("version: '1.5'", text)
        self.assertIn('stopImmediatePropagation', text)
        self.assertIn("DOMContentLoaded', reclaimAfterAppSetup", text)
        self.assertIn("vestra:app-ready', reclaimAfterAppSetup", text)
        self.assertNotIn('appLoadingOverlay', text)
        self.assertNotIn('.unregister()', text)
        self.assertNotIn('caches.delete', text)
        self.assertNotIn('getRegistrations()', text)
        self.assertIn('navigator.serviceWorker.getRegistration().then(reg => { if (reg) reg.update(); });', index)
        self.assertIn("navigator.serviceWorker.addEventListener('controllerchange'", index)
        # The historical implementation remains in the monolith for now, but
        # document capture intercepts the click before its target listener and
        # DOM reclaim independently replaces any contaminated button node.
        self.assertIn('getRegistrations()', app)
        self.assertIn('caches.delete', app)
        self.assertIn('if ($("btnForceUpdate")) $("btnForceUpdate").addEventListener("click", forceAppUpdate);', app)


if __name__ == '__main__':
    unittest.main(verbosity=2)
