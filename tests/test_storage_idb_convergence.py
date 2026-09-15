import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StorageIndexedDbConvergenceTests(unittest.TestCase):
    def run_node(self, body: str):
        script = textwrap.dedent(
            f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({str(ROOT / 'app-storage.js')!r}, 'utf8');
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

    def test_hung_indexeddb_open_times_out_and_reads_local_storage(self):
        result = self.run_node(
            """
            const context = {
              window: {},
              navigator: {},
              localStorage: {
                getItem(key) { return key === 'PF_STATE_V6' ? '{"fallback":true}' : null; }
              },
              indexedDB: {
                open() { return {}; }
              },
              Promise,
              Object,
              Error,
              setTimeout,
              clearTimeout,
              console,
            };
            vm.createContext(context);
            vm.runInContext(source, context);
            (async () => {
              const started = Date.now();
              const value = await context.window.VestraStorage.storageGet();
              const elapsed = Date.now() - started;
              if (value !== '{"fallback":true}') {
                throw new Error(`localStorage fallback was not read: ${value}`);
              }
              if (elapsed > 3000) {
                throw new Error(`IndexedDB timeout did not converge promptly: ${elapsed}ms`);
              }
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_blocked_indexeddb_open_falls_back_without_waiting_for_timeout(self):
        result = self.run_node(
            """
            let request;
            const context = {
              window: {},
              navigator: {},
              localStorage: {
                getItem() { return 'blocked-fallback'; }
              },
              indexedDB: {
                open() {
                  request = {};
                  setTimeout(() => request.onblocked && request.onblocked(), 0);
                  return request;
                }
              },
              Promise,
              Object,
              Error,
              setTimeout,
              clearTimeout,
              console,
            };
            vm.createContext(context);
            vm.runInContext(source, context);
            (async () => {
              const started = Date.now();
              const value = await context.window.VestraStorage.storageGet();
              const elapsed = Date.now() - started;
              if (value !== 'blocked-fallback') {
                throw new Error(`blocked fallback was not read: ${value}`);
              }
              if (elapsed > 500) {
                throw new Error(`blocked IndexedDB waited too long: ${elapsed}ms`);
              }
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_hung_read_transaction_times_out_and_reads_local_storage(self):
        result = self.run_node(
            """
            let openRequest;
            let aborts = 0;
            const db = {
              objectStoreNames: { contains() { return true; } },
              close() {},
              transaction() {
                const tx = {
                  error: null,
                  abort() { aborts += 1; if (tx.onabort) tx.onabort(); },
                  objectStore() { return { get() { return {}; } }; },
                };
                return tx;
              },
            };
            const fastTimeout = (fn, ms) => setTimeout(fn, ms === 1500 ? 5 : ms);
            const context = {
              window: {},
              navigator: {},
              localStorage: { getItem() { return 'transaction-fallback'; } },
              indexedDB: {
                open() {
                  openRequest = { result: db };
                  Promise.resolve().then(() => openRequest.onsuccess && openRequest.onsuccess());
                  return openRequest;
                }
              },
              Promise,
              Object,
              Error,
              setTimeout: fastTimeout,
              clearTimeout,
              console,
            };
            vm.createContext(context);
            vm.runInContext(source, context);
            (async () => {
              const value = await context.window.VestraStorage.storageGet();
              if (value !== 'transaction-fallback') {
                throw new Error(`hung read transaction did not fall back: ${value}`);
              }
              if (aborts !== 1) throw new Error(`hung transaction was not aborted exactly once: ${aborts}`);
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_hung_write_transaction_times_out_and_writes_local_storage(self):
        result = self.run_node(
            """
            let openRequest;
            let fallbackValue = null;
            let aborts = 0;
            const db = {
              objectStoreNames: { contains() { return true; } },
              close() {},
              transaction() {
                const tx = {
                  error: null,
                  abort() { aborts += 1; if (tx.onabort) tx.onabort(); },
                  objectStore() { return { put() {} }; },
                };
                return tx;
              },
            };
            const fastTimeout = (fn, ms) => setTimeout(fn, ms === 1500 ? 5 : ms);
            const context = {
              window: {},
              navigator: {},
              localStorage: { setItem(key, value) { fallbackValue = `${key}:${value}`; } },
              indexedDB: {
                open() {
                  openRequest = { result: db };
                  Promise.resolve().then(() => openRequest.onsuccess && openRequest.onsuccess());
                  return openRequest;
                }
              },
              Promise,
              Object,
              Error,
              setTimeout: fastTimeout,
              clearTimeout,
              console,
            };
            vm.createContext(context);
            vm.runInContext(source, context);
            (async () => {
              await context.window.VestraStorage.storageSet('payload');
              if (fallbackValue !== 'PF_STATE_V6:payload') {
                throw new Error(`hung write transaction did not fall back: ${fallbackValue}`);
              }
              if (aborts !== 1) throw new Error(`hung transaction was not aborted exactly once: ${aborts}`);
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_all_transaction_modes_handle_abort_and_timeout(self):
        source = (ROOT / "app-storage.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("tx.onabort"), 3)
        self.assertIn("db.onversionchange", source)
        self.assertIn("const IDB_TRANSACTION_TIMEOUT_MS = 1500", source)
        self.assertIn("armTransactionTimeout", source)


if __name__ == "__main__":
    unittest.main()
