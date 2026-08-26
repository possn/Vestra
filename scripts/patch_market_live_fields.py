from pathlib import Path

p=Path('market.js')
s=p.read_text()

anchor="""  function compactLiveBadge(s){
    return s?._liveUpdated ? `<span class=\"market-live-badge\">● Live · ${esc(new Intl.DateTimeFormat('pt-PT',{hour:'2-digit',minute:'2-digit'}).format(new Date(s._liveUpdated)))}</span>` : '';
  }
"""
if anchor not in s:
    raise SystemExit('live badge anchor missing')
helper=anchor+"""  function refreshOpenDossierLiveFields(s){
    const sh=$m('marketSheet');
    if(!sh || sh.hidden || txt(sh.dataset.ticker).toUpperCase()!==txt(s?.ticker).toUpperCase()) return;
    const values={
      current_price: money(s.current_price,s.currency),
      forward_pe: num(s.forward_pe),
      roe: pct(s.roe),
      revenue_growth: pct(s.revenue_growth),
      fcf_yield: pct(s.fcf_yield),
    };
    for(const [field,value] of Object.entries(values)){
      const el=sh.querySelector(`[data-live-field=\"${field}\"]`);
      if(el && value!=='—') el.textContent=value;
    }
  }
"""
s=s.replace(anchor,helper,1)

old="""          sh.dataset.liveReady='1';
"""
new="""          refreshOpenDossierLiveFields(s);
          sh.dataset.liveReady='1';
"""
if old not in s:
    raise SystemExit('live-ready anchor missing')
s=s.replace(old,new,1)

repls={
    '<small>Preço</small><strong>${money(s.current_price,s.currency)}</strong>':'<small>Preço</small><strong data-live-field="current_price">${money(s.current_price,s.currency)}</strong>',
    '<small>Forward P/E</small><strong>${num(s.forward_pe)}</strong>':'<small>Forward P/E</small><strong data-live-field="forward_pe">${num(s.forward_pe)}</strong>',
    '<small>ROE</small><strong>${pct(s.roe)}</strong>':'<small>ROE</small><strong data-live-field="roe">${pct(s.roe)}</strong>',
    '<small>Receita YoY</small><strong>${pct(s.revenue_growth)}</strong>':'<small>Receita YoY</small><strong data-live-field="revenue_growth">${pct(s.revenue_growth)}</strong>',
    '<small>FCF yield</small><strong>${pct(s.fcf_yield)}</strong>':'<small>FCF yield</small><strong data-live-field="fcf_yield">${pct(s.fcf_yield)}</strong>',
}
for old,new in repls.items():
    if old not in s:
        raise SystemExit(f'detail metric anchor missing: {old[:40]}')
    s=s.replace(old,new,1)

if s.count('refreshOpenDossierLiveFields(s)') != 1:
    raise SystemExit('live field refresh call count unexpected')
for field in ['current_price','forward_pe','roe','revenue_growth','fcf_yield']:
    if f'data-live-field="{field}"' not in s:
        raise SystemExit(f'missing live field {field}')
p.write_text(s)
print('open dossier now refreshes safe live metrics in place')
