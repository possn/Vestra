from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
market=ROOT/'market.js'
test=ROOT/'tests'/'test_market_score_explanation.py'
text=market.read_text(encoding='utf-8')

anchor="""  function scoreExplanation(s){\n    const score=n(s.score), coverage=n(s.data_coverage_pct);\n"""
helper="""  function peerScoreContext(s){\n    const peerCount=n(s?.peer_count);\n    const lines=[];\n    const rel=(label,value)=>{\n      const v=n(value);\n      if(v==null) return;\n      const direction=v<0?'desconto':'prémio';\n      lines.push(`${label}: ${Math.abs(v).toFixed(0)}% de ${direction} vs mediana`);\n    };\n    rel('Forward P/E',s?.forward_pe_vs_sector_pct);\n    rel('Trailing P/E',s?.trailing_pe_vs_sector_pct);\n    rel('P/B',s?.pb_vs_sector_pct);\n    rel('EV/EBITDA',s?.ev_ebitda_vs_sector_pct);\n\n    const compare=(label,value,median,kind='pct')=>{\n      const v=n(value), m=n(median);\n      if(v==null||m==null) return;\n      const fv=kind==='num'?num(v):pct(v);\n      const fm=kind==='num'?num(m):pct(m);\n      const delta=v-m;\n      const word=Math.abs(delta)<1e-12?'em linha com':delta>0?'acima de':'abaixo de';\n      lines.push(`${label}: ${fv} vs ${fm} · ${word} mediana`);\n    };\n    compare('ROE',s?.roe,s?.sector_roe_median);\n    compare('Margem operacional',s?.operating_margin,s?.sector_operating_margin_median);\n    compare('Margem bruta',s?.gross_margin,s?.sector_gross_margin_median);\n    compare('ROCE proxy',s?.roce_proxy,s?.sector_roce_proxy_median);\n    compare('Dividend yield',s?.dividend_yield,s?.sector_dividend_yield_median);\n    compare('FCF yield',s?.fcf_yield,s?.sector_fcf_yield_median);\n\n    if(!lines.length) return '';\n    const peerLabel=peerCount!=null&&peerCount>0?` · ${Math.round(peerCount)} peers`:'';\n    return `<p class=\"market-case-note\"><strong>Face aos peers${peerLabel}.</strong> ${lines.slice(0,6).map(esc).join(' · ')}. <span class=\"market-data-age\">Contexto relativo; não é recomendação.</span></p>`;\n  }\n\n  function scoreExplanation(s){\n    const score=n(s.score), coverage=n(s.data_coverage_pct);\n"""
if anchor not in text:
    raise SystemExit('scoreExplanation anchor not found')
text=text.replace(anchor,helper,1)

needle="""${scoreModelRationale(s)?`<p class=\"market-case-note\"><strong>Modelo usado.</strong> ${esc(scoreModelRationale(s))}</p>`:''}<div class=\"market-score-layers\">"""
repl="""${scoreModelRationale(s)?`<p class=\"market-case-note\"><strong>Modelo usado.</strong> ${esc(scoreModelRationale(s))}</p>`:''}${peerScoreContext(s)}<div class=\"market-score-layers\">"""
if needle not in text:
    raise SystemExit('score model rationale anchor not found')
text=text.replace(needle,repl,1)
market.write_text(text,encoding='utf-8')

base=test.read_text(encoding='utf-8')
if 'test_peer_context_explains_relative_evidence' not in base:
    marker='if __name__ == "__main__":\n'
    addition='''    def test_peer_context_explains_relative_evidence(self):\n        text = MARKET.read_text(encoding="utf-8")\n        self.assertIn("peerScoreContext", text)\n        self.assertIn("Face aos peers", text)\n        self.assertIn("forward_pe_vs_sector_pct", text)\n        self.assertIn("sector_roe_median", text)\n        self.assertIn("sector_operating_margin_median", text)\n        self.assertIn("sector_fcf_yield_median", text)\n        self.assertIn("Contexto relativo; não é recomendação.", text)\n        self.assertNotIn("s.score =", text)\n\n'''
    if marker in base:
        base=base.replace(marker,addition+marker,1)
    else:
        base+='\n'+addition
    test.write_text(base,encoding='utf-8')
