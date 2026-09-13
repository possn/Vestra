import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StorageClearResilienceTests(unittest.TestCase):
    def test_local_storage_is_cleared_when_indexeddb_open_fails(self):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({str(ROOT / 'app-storage.js')!r}, 'utf8');
            let removed = null;
            const context = {{
              window: {{}},
              navigator: {{}},
              localStorage: {{
                removeItem(key) {{ removed = key; }}
              }},
              indexedDB: {{
                open() {{ throw new Error('IndexedDB unavailable'); }}
              }},
              Promise,
              Object,
              console,
            }};
            vm.createContext(context);
            vm.runInContext(source, context);
            (async () => {{
              await context.window.VestraStorage.storageClear();
              if (removed !== 'PF_STATE_V6') {{
                throw new Error(`localStorage fallback was not cleared: ${{removed}}`);
              }}
            }})().catch((error) => {{
              console.error(error);
              process.exit(1);
            }});
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
