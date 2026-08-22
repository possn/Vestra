"""Optional SEC EDGAR enrichment for US-listed equities.

Enabled when SEC_USER_AGENT is set in the environment. Uses official SEC
company_tickers + companyfacts JSON; fills only fields that Yahoo left empty.
No API key is required. SEC asks automated clients to identify themselves via
User-Agent, so we deliberately do nothing until a proper value is configured.
"""
from __future__ import annotations
import logging, os, time
import requests

log=logging.getLogger('sec_enrich')
BASE='https://data.sec.gov'
TICKERS='https://www.sec.gov/files/company_tickers.json'

_TAGS={
 'revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'),
 'net_income': ('NetIncomeLoss','ProfitLoss'),
 'assets': ('Assets',), 'assets_current': ('AssetsCurrent',),
 'liabilities_current': ('LiabilitiesCurrent',),
 'equity': ('StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'),
 'cash': ('CashAndCashEquivalentsAtCarryingValue','CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'),
 'debt': ('LongTermDebtAndFinanceLeaseObligationsCurrent','LongTermDebtCurrent','LongTermDebtNoncurrent','LongTermDebtAndFinanceLeaseObligationsNoncurrent'),
 'cfo': ('NetCashProvidedByUsedInOperatingActivities',),
 'capex': ('PaymentsToAcquirePropertyPlantAndEquipment',),
 'operating_income': ('OperatingIncomeLoss',),
}

def _latest(facts, tags, annual=False):
    us=facts.get('us-gaap',{})
    vals=[]
    for tag in tags:
        node=us.get(tag,{})
        for unit_rows in (node.get('units') or {}).values():
            for r in unit_rows:
                if r.get('val') is None: continue
                form=r.get('form','')
                if form not in ('10-K','10-Q','20-F','40-F','6-K'): continue
                if annual and form not in ('10-K','20-F','40-F'): continue
                vals.append(r)
    if not vals: return None
    vals.sort(key=lambda r:(r.get('filed',''), r.get('end','')), reverse=True)
    try: return float(vals[0]['val'])
    except Exception: return None

def _annual_two(facts,tags):
    us=facts.get('us-gaap',{}); vals=[]
    for tag in tags:
        node=us.get(tag,{})
        for rows in (node.get('units') or {}).values():
            vals += [r for r in rows if r.get('val') is not None and r.get('form') in ('10-K','20-F','40-F') and r.get('fp')=='FY']
    by_end={}
    for r in vals:
        by_end[r.get('end')]=r
    rows=sorted(by_end.values(), key=lambda r:r.get('end',''), reverse=True)
    out=[]
    for r in rows[:2]:
        try: out.append(float(r['val']))
        except Exception: pass
    return out

def enrich(raw, priority=None, max_nonpriority=350):
    ua=os.getenv('SEC_USER_AGENT','').strip()
    if not ua:
        log.info('SEC enrichment disabled: set SEC_USER_AGENT to enable official EDGAR fallback')
        return raw
    sess=requests.Session(); sess.headers.update({'User-Agent':ua,'Accept-Encoding':'gzip, deflate'})
    try:
        j=sess.get(TICKERS,timeout=20).json()
        cmap={str(v.get('ticker','')).upper():int(v['cik_str']) for v in j.values() if v.get('ticker') and v.get('cik_str')}
    except Exception as e:
        log.warning('SEC ticker map unavailable: %s',e); return raw
    priority=set(priority or []); non=0; filled=0
    for m in raw:
        t=str(getattr(m,'ticker','')).upper()
        if '.' in t or getattr(m,'quote_type',None) in ('ETF','CRYPTO') or t not in cmap: continue
        missing=sum(getattr(m,k,None) is None for k in ('roe','profit_margin','revenue_growth','free_cash_flow','current_ratio','debt_to_equity'))
        if missing<2 and t not in priority: continue
        if t not in priority:
            non+=1
            if non>max_nonpriority: continue
        try:
            cik=f"{cmap[t]:010d}"
            data=sess.get(f'{BASE}/api/xbrl/companyfacts/CIK{cik}.json',timeout=20).json()
            facts=data.get('facts') or {}
            rev=_latest(facts,_TAGS['revenue']); ni=_latest(facts,_TAGS['net_income']); assets=_latest(facts,_TAGS['assets']); eq=_latest(facts,_TAGS['equity'])
            ac=_latest(facts,_TAGS['assets_current']); lc=_latest(facts,_TAGS['liabilities_current']); cash=_latest(facts,_TAGS['cash'])
            cfo=_latest(facts,_TAGS['cfo']); capex=_latest(facts,_TAGS['capex']); op=_latest(facts,_TAGS['operating_income'])
            debt=sum(x or 0 for x in [_latest(facts,(_TAGS['debt'][0],)),_latest(facts,(_TAGS['debt'][1],)),_latest(facts,(_TAGS['debt'][2],)),_latest(facts,(_TAGS['debt'][3],))]) or None
            if getattr(m,'profit_margin',None) is None and rev and ni is not None: m.profit_margin=ni/rev
            if getattr(m,'operating_margin',None) is None and rev and op is not None: m.operating_margin=op/rev
            if getattr(m,'roe',None) is None and eq and ni is not None: m.roe=ni/eq
            if getattr(m,'roa',None) is None and assets and ni is not None: m.roa=ni/assets
            if getattr(m,'current_ratio',None) is None and lc: m.current_ratio=(ac/lc) if ac is not None else None
            if getattr(m,'total_cash',None) is None: m.total_cash=cash
            if getattr(m,'total_debt',None) is None: m.total_debt=debt
            if getattr(m,'debt_to_equity',None) is None and eq and debt is not None: m.debt_to_equity=debt/eq
            if getattr(m,'operating_cash_flow',None) is None: m.operating_cash_flow=cfo
            if getattr(m,'free_cash_flow',None) is None and cfo is not None: m.free_cash_flow=cfo-(capex or 0)
            arr=_annual_two(facts,_TAGS['revenue'])
            if getattr(m,'revenue_growth',None) is None and len(arr)>=2 and arr[1]: m.revenue_growth=arr[0]/arr[1]-1
            arr=_annual_two(facts,_TAGS['net_income'])
            if getattr(m,'earnings_growth',None) is None and len(arr)>=2 and arr[1] not in (0,None): m.earnings_growth=arr[0]/arr[1]-1
            setattr(m,'sec_edgar_enriched',True); filled+=1
            time.sleep(0.11)
        except Exception as e:
            log.debug('SEC %s: %s',t,e)
    log.info('SEC EDGAR enriched %d rows',filled)
    return raw
