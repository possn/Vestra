from pathlib import Path
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "market-learned-universe.js"


class LearnedUniverseLastSeenTests(unittest.TestCase):
    def test_persisted_last_seen_survives_reload_but_live_upsert_refreshes_it(self):
        script = textwrap.dedent(f"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync({str(MODULE)!r}, 'utf8');
            const persistedLastSeen = '2025-01-02T03:04:05.000Z';
            let persistedPayload = null;
            const context = {{
              window: {{
                VestraStorage: {{
                  idbGet: async () => ({{
                    schema_version: 3,
                    rows: [{{
                      ticker: 'OLD',
                      provider_symbol: 'OLD',
                      identity_verified: true,
                      name: 'Old Corp',
                      exchange: 'NMS',
                      currency: 'USD',
                      quote_type: 'EQUITY',
                      first_seen: '2024-01-01T00:00:00.000Z',
                      last_seen: persistedLastSeen,
                      validation_count: 3,
                      promotion_status: 'pending',
                      source: 'worker-market'
                    }}]
                  }}),
                  idbSet: async (_key, value) => {{ persistedPayload = value; }}
                }},
                dispatchEvent: () => true,
              }},
              CustomEvent: function(type, init) {{ this.type = type; this.detail = init?.detail; }},
              console,
              Date,
              Promise,
              Object,
              Array,
              String,
              Number,
              Math,
            }};
            context.globalThis = context;
            vm.createContext(context);
            vm.runInContext(source, context, {{filename:'market-learned-universe.js'}});

            (async () => {{
              const api = context.window.VestraLearnedUniverse;
              const loaded = await api.list();
              if (loaded.length !== 1) throw new Error('expected one persisted row');
              if (loaded[0].last_seen !== persistedLastSeen) {{
                throw new Error(`load rewrote last_seen: ${{loaded[0].last_seen}}`);
              }}

              const before = loaded[0].last_seen;
              const updated = await api.upsert({{
                ticker: 'OLD',
                provider_symbol: 'OLD',
                identity_verified: true,
                name: 'Old Corp',
                last_seen: '2000-01-01T00:00:00.000Z'
              }}, 'worker-market');
              if (!updated) throw new Error('upsert returned no row');
              if (updated.last_seen === before || updated.last_seen === '2000-01-01T00:00:00.000Z') {{
                throw new Error(`live upsert did not refresh last_seen: ${{updated.last_seen}}`);
              }}
              if (!persistedPayload || persistedPayload.rows[0].last_seen !== updated.last_seen) {{
                throw new Error('refreshed last_seen was not persisted');
              }}
            }})().catch(err => {{ console.error(err); process.exit(1); }});
        """)
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
