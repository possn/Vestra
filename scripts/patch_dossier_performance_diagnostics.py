from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
loader=ROOT/'market-data-loader.js'
test=ROOT/'tests'/'test_market_loader_invariants.py'
text=loader.read_text(encoding='utf-8')

old="""  const tickerHydrationCache = new Map();\n  let manifestPromise = null;\n  let bypassClick = false;\n"""
new="""  const tickerHydrationCache = new Map();\n  const dossierPerf = [];\n  const dossierOpenMarks = new Map();\n  let manifestPromise = null;\n  let bypassClick = false;\n\n  function recordDossierPerf(entry){\n    const row={ts:new Date().toISOString(),...entry};\n    dossierPerf.push(row);\n    if(dossierPerf.length>20) dossierPerf.splice(0,dossierPerf.length-20);\n    return row;\n  }\n\n  function markDossierOpen(ticker){\n    const key=tickerKey(ticker); if(!key) return;\n    dossierOpenMarks.set(key,{startedAt:performance.now(),sheetMs:null});\n    requestAnimationFrame(()=>{\n      const mark=dossierOpenMarks.get(key); if(!mark||mark.sheetMs!=null) return;\n      const sh=dossierSheetFor(key);\n      if(sh) mark.sheetMs=Math.round(performance.now()-mark.startedAt);\n    });\n  }\n"""
if old not in text: raise SystemExit('loader state anchor missing')
text=text.replace(old,new,1)

old="""  function hydrateOpenDossier(ticker){\n    const key=tickerKey(ticker);\n    if(!key) return Promise.resolve(null);\n    setHydrationBadge(key,'loading');\n    return hydrateTicker(key).then(stock=>{\n      refreshOpenDossier(key,stock);\n      return stock;\n    }).catch(()=>{\n      setHydrationBadge(key,'partial');\n      return resolveIndexStock(key);\n    });\n  }\n"""
new="""  function hydrateOpenDossier(ticker){\n    const key=tickerKey(ticker);\n    if(!key) return Promise.resolve(null);\n    const hydrationStartedAt=performance.now();\n    setHydrationBadge(key,'loading');\n    return hydrateTicker(key).then(stock=>{\n      refreshOpenDossier(key,stock);\n      const mark=dossierOpenMarks.get(key)||{};\n      recordDossierPerf({\n        ticker:key,\n        sheetMs:mark.sheetMs,\n        hydrationMs:Math.round(performance.now()-hydrationStartedAt),\n        complete:!!stock?._dossierHydrated,\n        error:txt(stock?._dossierHydrationError)\n      });\n      dossierOpenMarks.delete(key);\n      return stock;\n    }).catch(err=>{\n      setHydrationBadge(key,'partial');\n      const mark=dossierOpenMarks.get(key)||{};\n      recordDossierPerf({\n        ticker:key,\n        sheetMs:mark.sheetMs,\n        hydrationMs:Math.round(performance.now()-hydrationStartedAt),\n        complete:false,\n        error:txt(err?.message)||'hydration failed'\n      });\n      dossierOpenMarks.delete(key);\n      return resolveIndexStock(key);\n    });\n  }\n"""
if old not in text: raise SystemExit('hydrateOpenDossier anchor missing')
text=text.replace(old,new,1)

old="""  function openDossier(ticker,options={}){\n    const tk=tickerKey(ticker);\n    if(!tk) return Promise.resolve(false);\n"""
new="""  function openDossier(ticker,options={}){\n    const tk=tickerKey(ticker);\n    if(!tk) return Promise.resolve(false);\n    markDossierOpen(tk);\n"""
if old not in text: raise SystemExit('openDossier anchor missing')
text=text.replace(old,new,1)

old="""  window.VestraMarketData={hydrateTicker,hydratePortfolio,loadManifest,openDossier,refreshOpenDossier,hydrateOpenDossier,version:'2.4'};\n"""
new="""  window.VestraMarketData={\n    hydrateTicker,hydratePortfolio,loadManifest,openDossier,refreshOpenDossier,hydrateOpenDossier,\n    performance:()=>dossierPerf.map(x=>({...x})),\n    version:'2.5'\n  };\n"""
if old not in text: raise SystemExit('public API anchor missing')
text=text.replace(old,new,1)
loader.write_text(text,encoding='utf-8')

base=test.read_text(encoding='utf-8')
base=base.replace("self.assertIn('market-data-loader.js?v=2.4', index)","self.assertIn('market-data-loader.js?v=2.5', index)")
base=base.replace('self.assertIn("version:\'2.4\'", loader)','self.assertIn("version:\'2.5\'", loader)')
marker='    def test_politicians_loader_matches_canonical_module_version(self):\n'
addition='''    def test_dossier_performance_is_local_read_only_diagnostics(self):\n        loader = read("market-data-loader.js")\n        self.assertIn("dossierPerf", loader)\n        self.assertIn("markDossierOpen", loader)\n        self.assertIn("sheetMs", loader)\n        self.assertIn("hydrationMs", loader)\n        self.assertIn("performance:()=>dossierPerf.map", loader)\n        self.assertIn("if(dossierPerf.length>20)", loader)\n        self.assertNotIn("sendBeacon", loader)\n        self.assertNotIn("/telemetry", loader)\n\n'''
if 'test_dossier_performance_is_local_read_only_diagnostics' not in base:
    if marker not in base: raise SystemExit('test anchor missing')
    base=base.replace(marker,addition+marker,1)
test.write_text(base,encoding='utf-8')

index=ROOT/'index.html'
idx=index.read_text(encoding='utf-8')
if 'market-data-loader.js?v=2.4' not in idx: raise SystemExit('index cachebuster anchor missing')
idx=idx.replace('market-data-loader.js?v=2.4','market-data-loader.js?v=2.5',1)
index.write_text(idx,encoding='utf-8')
