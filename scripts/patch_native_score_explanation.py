from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
market=ROOT/'market.js'
test=ROOT/'tests'/'test_market_score_explanation.py'
text=market.read_text(encoding='utf-8')

old="""  function scoreDims(s){\n    const mapped=[\n      ['Qualidade',s.quality_pct],['Crescimento',s.growth_pct],['Balanço',s.balance_pct],['Cash flow',s.cashflow_pct],\n      ['Valuation',s.value_pct],['Execução',s.execution_pct],['Qualidade dos lucros',s.earnings_quality_pct],\n      ['Alocação de capital',s.capital_allocation_pct],['Estabilidade',s.stability_pct]\n    ];\n    return mapped.filter(([,v])=>v!=null);\n  }\n"""
new="""  function scoreDimensionLabel(label){\n    const labels={\n      'Quality':'Qualidade','Growth':'Crescimento','Balance':'Balanço','Cash Flow':'Cash flow','Valuation':'Valuation',\n      'Execution':'Execução','Earnings Quality':'Qualidade dos lucros','Capital Allocation':'Alocação de capital','Stability':'Estabilidade',\n      'Bank Quality':'Qualidade bancária','Efficiency':'Eficiência','Asset Quality':'Qualidade do crédito','Capital Proxy':'Capitalização',\n      'Income':'Rendimento','REIT Quality':'Qualidade REIT','Leverage':'Alavancagem','P/FFO Value':'P/FFO','Distribution':'Distribuição',\n      'Insurance Quality':'Qualidade seguradora','Underwriting Proxy':'Subscrição','Utility Quality':'Qualidade utility',\n      'Energy Quality':'Qualidade energia','Cash Runway':'Runway de caixa','Net Cash':'Caixa líquida',\n      'Dilution Discipline':'Disciplina de diluição','Operating Quality':'Qualidade operacional'\n    };\n    return labels[label]||label;\n  }\n\n  function scoreDims(s){\n    const native=s?.score_dimensions;\n    if(native && typeof native==='object' && !Array.isArray(native)){\n      const rows=Object.entries(native).map(([label,value])=>[scoreDimensionLabel(label),n(value)]).filter(([,value])=>value!=null);\n      if(rows.length) return rows;\n    }\n    const mapped=[\n      ['Qualidade',s.quality_pct],['Crescimento',s.growth_pct],['Balanço',s.balance_pct],['Cash flow',s.cashflow_pct],\n      ['Valuation',s.value_pct],['Execução',s.execution_pct],['Qualidade dos lucros',s.earnings_quality_pct],\n      ['Alocação de capital',s.capital_allocation_pct],['Estabilidade',s.stability_pct]\n    ];\n    return mapped.filter(([,v])=>v!=null);\n  }\n"""
if old not in text:
    raise SystemExit('scoreDims anchor not found')
text=text.replace(old,new,1)

anchor="""      'Estabilidade':[['Beta','beta','num']]\n    };\n"""
replacement="""      'Estabilidade':[['Beta','beta','num']],\n      'Qualidade bancária':[['ROE','roe'],['ROA','roa'],['Margem líquida','profit_margin']],\n      'Eficiência':[['Efficiency ratio','efficiency_ratio_proxy']],\n      'Qualidade do crédito':[['Provisões / receitas','provision_to_revenue']],\n      'Capitalização':[['Equity / assets','equity_to_assets']],\n      'Rendimento':[['Dividend yield','dividend_yield']],\n      'Qualidade REIT':[['FFO / ação proxy','reit_ffo_per_share_proxy','num'],['ROE','roe'],['Margem líquida','profit_margin']],\n      'Alavancagem':[['Net debt / EBITDA','reit_net_debt_to_ebitda','multiple'],['Cobertura juros','interest_coverage','multiple']],\n      'P/FFO':[['P/FFO proxy','reit_p_ffo_proxy','multiple']],\n      'Distribuição':[['Dividend yield','dividend_yield'],['Payout FFO proxy','reit_ffo_payout_proxy']],\n      'Qualidade seguradora':[['ROE','roe'],['ROA','roa'],['Margem líquida','profit_margin']],\n      'Subscrição':[['Claims / receitas','insurance_claims_to_revenue'],['Operating ratio proxy','insurance_operating_ratio_proxy']],\n      'Qualidade utility':[['ROE','roe'],['Margem operacional','operating_margin'],['Margem líquida','profit_margin']],\n      'Qualidade energia':[['ROE','roe'],['ROCE proxy','roce_proxy'],['Margem operacional','operating_margin']],\n      'Runway de caixa':[['Cash total','total_cash','compact'],['Free cash flow','free_cash_flow','compact']],\n      'Caixa líquida':[['Net cash','net_cash','compact']],\n      'Disciplina de diluição':[['Diluição YoY','diluted_shares_yoy']],\n      'Qualidade operacional':[['ROA','roa'],['Margem operacional','operating_margin']]\n    };\n"""
if anchor not in text:
    raise SystemExit('pillar defs anchor not found')
text=text.replace(anchor,replacement,1)

score_anchor="""  function scoreExplanation(s){\n    const score=n(s.score), coverage=n(s.data_coverage_pct);\n"""
score_new="""  function scoreModelRationale(s){\n    const model=txt(s?.score_model||'general');\n    const notes={\n      general:'Modelo geral: qualidade, crescimento, balanço, valuation, execução, qualidade dos lucros, alocação de capital e estabilidade.',\n      growth_tech:'Growth Tech: dá mais peso a crescimento, execução, margens, qualidade do cash flow e valuation compatível com empresas de crescimento.',\n      bank:'Bancos: rentabilidade, eficiência, qualidade do crédito, capitalização, crescimento do net interest income, P/B-P/E e rendimento.',\n      reit:'REIT: FFO/P-FFO proxy, alavancagem, payout/distribuição, crescimento e estabilidade. AFFO, NAV e ocupação não são inventados quando faltam.',\n      insurance:'Seguros: rentabilidade, underwriting proxy, capitalização, crescimento, valuation e rendimento; não fabrica combined ratio regulatório.',\n      utility:'Utilities: resiliência do balanço, rendimento, qualidade operacional, valuation e estabilidade pesam mais do que crescimento headline.',\n      energy:'Energia: geração de caixa, eficiência de capital, balanço e valuation têm maior peso; crescimento cíclico pesa menos.',\n      biotech:'Biotech: runway de caixa, caixa líquida, disciplina de diluição e progresso operacional; P/E genérico é excluído quando não é economicamente útil.'\n    };\n    return notes[model]||txt(s?.score_model_note)||'';\n  }\n\n  function scoreExplanation(s){\n    const score=n(s.score), coverage=n(s.data_coverage_pct);\n"""
if score_anchor not in text:
    raise SystemExit('scoreExplanation anchor not found')
text=text.replace(score_anchor,score_new,1)

needle="""<div class=\"market-action-context\"><span>Cobertura ${coverage==null?'—':Math.round(coverage)+'%'}</span><span>Confiança ${esc(confidence)}</span><span>${dims.length} pilares disponíveis</span></div><div class=\"market-score-layers\">"""
repl="""<div class=\"market-action-context\"><span>Cobertura ${coverage==null?'—':Math.round(coverage)+'%'}</span><span>Confiança ${esc(confidence)}</span><span>${dims.length} pilares disponíveis</span></div>${scoreModelRationale(s)?`<p class=\"market-case-note\"><strong>Modelo usado.</strong> ${esc(scoreModelRationale(s))}</p>`:''}<div class=\"market-score-layers\">"""
if needle not in text:
    raise SystemExit('score rationale insertion anchor not found')
text=text.replace(needle,repl,1)
market.write_text(text,encoding='utf-8')

base=test.read_text(encoding='utf-8') if test.exists() else ''
if 'test_specialist_models_use_native_score_dimensions' not in base:
    marker='if __name__ == "__main__":\n'
    addition='''    def test_specialist_models_use_native_score_dimensions(self):\n        text = MARKET.read_text(encoding="utf-8")\n        self.assertIn("score_dimensions", text)\n        self.assertIn("scoreDimensionLabel", text)\n        self.assertIn("Qualidade bancária", text)\n        self.assertIn("Qualidade REIT", text)\n        self.assertIn("Subscrição", text)\n        self.assertIn("Runway de caixa", text)\n\n    def test_model_rationale_is_visible_and_read_only(self):\n        text = MARKET.read_text(encoding="utf-8")\n        self.assertIn("scoreModelRationale", text)\n        self.assertIn("Modelo usado.", text)\n        self.assertIn("Bancos: rentabilidade", text)\n        self.assertIn("Biotech: runway de caixa", text)\n        self.assertNotIn("s.score =", text)\n\n'''
    if marker in base:
        base=base.replace(marker,addition+marker,1)
    else:
        base+='\n'+addition
    test.write_text(base,encoding='utf-8')
