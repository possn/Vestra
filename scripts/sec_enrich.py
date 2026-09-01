"""Official SEC EDGAR enrichment for US-listed equities.

Uses official SEC ticker/CIK catalogues plus CompanyFacts JSON, no API key. The
catalogue lookup is deliberately exact and resilient: two official SEC schemas
are tried with bounded retries, and the last validated mapping is persisted as a
local snapshot so a transient HTML/error response cannot disable all SEC
fundamental enrichment for a daily run.

The enricher fills only metrics Yahoo left empty and derives a broader set of
statement-backed quality/liquidity/cash-flow fields plus multi-year history.
Missing values remain missing; no zero-filling or issuer-name fuzzy matching is
used.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
from pathlib import Path
import time

import requests

log=logging.getLogger('sec_enrich')
BASE='https://data.sec.gov'
TICKERS='https://www.sec.gov/files/company_tickers.json'
TICKERS_EXCHANGE='https://www.sec.gov/files/company_tickers_exchange.json'
ROOT=Path(__file__).resolve().parents[1]
TICKER_MAP_SNAPSHOT=ROOT/'data'/'sec_ticker_map.json'
TICKER_MAP_SCHEMA_VERSION=1

_TAGS={
 'revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','Revenues','SalesRevenueNet'),
 'net_income': ('NetIncomeLoss','ProfitLoss'),
 'gross_profit': ('GrossProfit',),
 'assets': ('Assets',),
 'assets_current': ('AssetsCurrent',),
 'inventory': ('InventoryNet','InventoryFinishedGoodsNetOfAllowancesCustomerAdvancesAndProgressBillings'),
 'liabilities_current': ('LiabilitiesCurrent',),
 'equity': ('StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'),
 'cash': ('CashAndCashEquivalentsAtCarryingValue','CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'),
 'debt': ('LongTermDebtAndFinanceLeaseObligationsCurrent','LongTermDebtCurrent','LongTermDebtNoncurrent','LongTermDebtAndFinanceLeaseObligationsNoncurrent','ShortTermBorrowings'),
 'cfo': ('NetCashProvidedByUsedInOperatingActivities','NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'),
 'capex': ('PaymentsToAcquirePropertyPlantAndEquipment','PaymentsForAdditionsToPropertyPlantAndEquipment'),
 'operating_income': ('OperatingIncomeLoss',),
 'interest_expense': ('InterestExpenseNonOperating','InterestAndDebtExpense','InterestExpense'),
 'shares': ('WeightedAverageNumberOfDilutedSharesOutstanding','WeightedAverageNumberOfSharesOutstandingBasic'),
 'dividends': ('PaymentsOfDividends','PaymentsOfDividendsCommonStock'),
}


def _normal_ticker(value):
    ticker=str(value or '').strip().upper()
    if not ticker or len(ticker)>15:
        return None
    allowed=set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-')
    return ticker if all(ch in allowed for ch in ticker) else None


def _normal_cik(value):
    try:
        cik=int(value)
    except (TypeError,ValueError):
        return None
    return cik if 0<cik<10_000_000_000 else None


def _parse_company_tickers(payload):
    """Parse the official company_tickers.json object schema."""
    if not isinstance(payload,dict):
        return {}
    out={}
    for row in payload.values():
        if not isinstance(row,dict):
            continue
        ticker=_normal_ticker(row.get('ticker'))
        cik=_normal_cik(row.get('cik_str'))
        if ticker and cik is not None:
            out[ticker]=cik
    return out


def _parse_company_tickers_exchange(payload):
    """Parse the official company_tickers_exchange.json fields/data schema."""
    if not isinstance(payload,dict):
        return {}
    fields=payload.get('fields')
    rows=payload.get('data')
    if not isinstance(fields,list) or not isinstance(rows,list):
        return {}
    positions={str(name).strip().lower():i for i,name in enumerate(fields)}
    ticker_i=positions.get('ticker')
    cik_i=positions.get('cik')
    if ticker_i is None or cik_i is None:
        return {}
    out={}
    for row in rows:
        if not isinstance(row,(list,tuple)):
            continue
        if ticker_i>=len(row) or cik_i>=len(row):
            continue
        ticker=_normal_ticker(row[ticker_i])
        cik=_normal_cik(row[cik_i])
        if ticker and cik is not None:
            out[ticker]=cik
    return out


def _parse_ticker_payload(payload,source):
    if source==TICKERS_EXCHANGE:
        return _parse_company_tickers_exchange(payload)
    return _parse_company_tickers(payload)


def _validated_map(mapping):
    if not isinstance(mapping,dict) or not mapping:
        return None
    out={}
    for ticker,cik in mapping.items():
        tk=_normal_ticker(ticker)
        ci=_normal_cik(cik)
        if not tk or ci is None:
            return None
        out[tk]=ci
    return out or None


def _read_ticker_snapshot(path=TICKER_MAP_SNAPSHOT):
    try:
        payload=json.loads(Path(path).read_text(encoding='utf-8'))
        if payload.get('schema_version')!=TICKER_MAP_SCHEMA_VERSION:
            return None
        mapping=_validated_map(payload.get('map'))
        if not mapping or int(payload.get('count') or 0)!=len(mapping):
            return None
        return mapping,payload
    except Exception:
        return None


def _write_ticker_snapshot(mapping,source,path=TICKER_MAP_SNAPSHOT):
    mapping=_validated_map(mapping)
    if not mapping:
        raise ValueError('invalid SEC ticker map')
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    payload={
        'schema_version':TICKER_MAP_SCHEMA_VERSION,
        'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'source':source,
        'count':len(mapping),
        'map':dict(sorted(mapping.items())),
    }
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=False)+'\n',encoding='utf-8')
    tmp.replace(path)
    return payload


def _remote_ticker_map(sess,retries=2,sleep=time.sleep):
    errors=[]
    for source in (TICKERS,TICKERS_EXCHANGE):
        for attempt in range(1,max(1,int(retries))+1):
            try:
                response=sess.get(source,timeout=20)
                if not response.ok:
                    raise RuntimeError(f'HTTP {response.status_code}')
                payload=response.json()
                mapping=_validated_map(_parse_ticker_payload(payload,source))
                if not mapping:
                    raise ValueError('valid JSON but no ticker/CIK rows')
                log.info('SEC ticker map loaded from %s: %d exact ticker(s)',source,len(mapping))
                return mapping,source
            except Exception as exc:
                errors.append(f'{source} attempt {attempt}: {exc}')
                if attempt<max(1,int(retries)):
                    sleep(0.75*attempt)
    raise RuntimeError('; '.join(errors[-4:]) or 'all SEC ticker-map sources failed')


def _load_ticker_map(sess,snapshot_path=TICKER_MAP_SNAPSHOT,retries=2,sleep=time.sleep):
    """Remote-first exact ticker map with validated persisted fallback."""
    try:
        mapping,source=_remote_ticker_map(sess,retries=retries,sleep=sleep)
        try:
            _write_ticker_snapshot(mapping,source,snapshot_path)
        except Exception as exc:
            log.warning('SEC ticker map loaded but snapshot could not be persisted: %s',exc)
        return mapping
    except Exception as remote_error:
        cached=_read_ticker_snapshot(snapshot_path)
        if cached:
            mapping,payload=cached
            log.warning(
                'SEC ticker map remote lookup failed; using validated snapshot (%d tickers, generated_at=%s): %s',
                len(mapping),payload.get('generated_at') or 'unknown',remote_error,
            )
            return mapping
        raise RuntimeError(f'SEC ticker map unavailable and no valid snapshot: {remote_error}') from remote_error


def _rows(facts,tags,annual=False):
    us=facts.get('us-gaap',{}); vals=[]
    for tag in tags:
        node=us.get(tag,{})
        for unit_rows in (node.get('units') or {}).values():
            for r in unit_rows:
                if r.get('val') is None: continue
                form=r.get('form','')
                if form not in ('10-K','10-Q','20-F','40-F','6-K'): continue
                if annual and form not in ('10-K','20-F','40-F'): continue
                vals.append(r)
    return vals


def _latest(facts,tags,annual=False):
    vals=_rows(facts,tags,annual)
    if not vals: return None
    vals.sort(key=lambda r:(r.get('filed',''),r.get('end','')),reverse=True)
    try: return float(vals[0]['val'])
    except Exception: return None


def _annual(facts,tags,limit=4):
    vals=[]
    for r in _rows(facts,tags,True):
        if r.get('fp')=='FY' and r.get('end'): vals.append(r)
    by_end={}
    for r in vals:
        # Prefer the most recently filed observation for a fiscal year.
        end=r.get('end'); old=by_end.get(end)
        if old is None or str(r.get('filed',''))>str(old.get('filed','')): by_end[end]=r
    rows=sorted(by_end.values(),key=lambda r:r.get('end',''),reverse=True)
    out=[]
    for r in rows[:limit]:
        try: out.append((str(r.get('end')),float(r['val'])))
        except Exception: pass
    return out


def _annual_two(facts,tags):
    return [v for _,v in _annual(facts,tags,2)]


def _latest_period_end(facts):
    ends=[]
    for tags in _TAGS.values():
        for r in _rows(facts,tags,False):
            if r.get('end'): ends.append(str(r.get('end')))
    return max(ends) if ends else None


def _agreement(old,new,tolerance=0.25):
    try:
        if old is None or new is None: return None
        a=float(old); b=float(new); scale=max(abs(a),abs(b),1.0)
        return abs(a-b)/scale<=tolerance
    except Exception: return None


def _annual_quality_history(facts):
    series={k:dict(_annual(facts,_TAGS[k],4)) for k in ('revenue','net_income','gross_profit','operating_income','assets','equity','cfo','capex')}
    dates=sorted(set(series['revenue'])|set(series['net_income'])|set(series['operating_income']),reverse=True)
    out=[]
    for d in dates[:4]:
        rev=series['revenue'].get(d); ni=series['net_income'].get(d); gp=series['gross_profit'].get(d); op=series['operating_income'].get(d)
        assets=series['assets'].get(d); eq=series['equity'].get(d); cfo=series['cfo'].get(d); capex=series['capex'].get(d)
        row={'date':d}
        if rev not in (None,0):
            if ni is not None: row['net_margin']=ni/rev
            if gp is not None: row['gross_margin']=gp/rev
            if op is not None: row['operating_margin']=op/rev
            if cfo is not None and capex is not None: row['fcf_margin']=(cfo-abs(capex))/rev
        if eq not in (None,0) and ni is not None: row['roe']=ni/eq
        if assets not in (None,0) and ni is not None: row['roa']=ni/assets
        if len(row)>1: out.append(row)
    return out


def enrich(raw,priority=None,max_nonpriority=500):
    ua=os.getenv('SEC_USER_AGENT','Vestra/4.0 (+https://github.com/possn/Vestra)').strip()
    if not ua:
        log.info('SEC enrichment disabled: set SEC_USER_AGENT to enable official EDGAR fallback'); return raw
    sess=requests.Session(); sess.headers.update({'User-Agent':ua,'Accept-Encoding':'gzip, deflate','Accept':'application/json'})
    try:
        cmap=_load_ticker_map(sess)
    except Exception as e:
        log.warning('SEC ticker map unavailable: %s',e); return raw
    priority=set(priority or []); non=0; filled=0
    for m in raw:
        t=str(getattr(m,'ticker','')).upper()
        if '.' in t or getattr(m,'quote_type',None) in ('ETF','CRYPTO') or t not in cmap: continue
        missing=sum(getattr(m,k,None) is None for k in ('roe','roa','profit_margin','operating_margin','gross_margin','revenue_growth','free_cash_flow','current_ratio','quick_ratio','debt_to_equity','interest_expense'))
        if missing<2 and t not in priority: continue
        if t not in priority:
            non+=1
            if non>max_nonpriority: continue
        try:
            cik=f"{cmap[t]:010d}"
            response=sess.get(f'{BASE}/api/xbrl/companyfacts/CIK{cik}.json',timeout=20)
            response.raise_for_status()
            data=response.json(); facts=data.get('facts') or {}
            rev=_latest(facts,_TAGS['revenue']); ni=_latest(facts,_TAGS['net_income']); gp=_latest(facts,_TAGS['gross_profit']); op=_latest(facts,_TAGS['operating_income'])
            assets=_latest(facts,_TAGS['assets']); eq=_latest(facts,_TAGS['equity']); ac=_latest(facts,_TAGS['assets_current']); inv=_latest(facts,_TAGS['inventory']); lc=_latest(facts,_TAGS['liabilities_current'])
            cash=_latest(facts,_TAGS['cash']); cfo=_latest(facts,_TAGS['cfo']); capex=_latest(facts,_TAGS['capex']); interest=_latest(facts,_TAGS['interest_expense'])
            debt=sum(x or 0 for x in (_latest(facts,(tag,)) for tag in _TAGS['debt'])) or None
            setattr(m,'sec_period_end',_latest_period_end(facts))
            sec_current_ratio=(ac/lc) if ac is not None and lc not in (None,0) else None
            checks=[]
            for old,new,tol in ((getattr(m,'total_cash',None),cash,.30),(getattr(m,'total_debt',None),debt,.30),(getattr(m,'current_ratio',None),sec_current_ratio,.20),(getattr(m,'total_assets',None),assets,.20),(getattr(m,'stockholders_equity',None),eq,.20)):
                ok=_agreement(old,new,tol)
                if ok is not None: checks.append(ok)
            setattr(m,'source_agreement_checks',len(checks)); setattr(m,'source_agreement_pct',round(sum(bool(x) for x in checks)/len(checks)*100,1) if checks else None)

            if getattr(m,'profit_margin',None) is None and rev not in (None,0) and ni is not None: m.profit_margin=ni/rev
            if getattr(m,'operating_margin',None) is None and rev not in (None,0) and op is not None: m.operating_margin=op/rev
            if getattr(m,'gross_margin',None) is None and rev not in (None,0) and gp is not None: m.gross_margin=gp/rev
            if getattr(m,'roe',None) is None and eq not in (None,0) and ni is not None: m.roe=ni/eq
            if getattr(m,'roa',None) is None and assets not in (None,0) and ni is not None: m.roa=ni/assets
            if getattr(m,'current_ratio',None) is None and lc not in (None,0) and ac is not None: m.current_ratio=ac/lc
            if getattr(m,'quick_ratio',None) is None and lc not in (None,0) and ac is not None: m.quick_ratio=(ac-(inv or 0))/lc
            if getattr(m,'total_cash',None) is None: m.total_cash=cash
            if getattr(m,'total_debt',None) is None: m.total_debt=debt
            if getattr(m,'total_assets',None) is None: m.total_assets=assets
            if getattr(m,'stockholders_equity',None) is None: m.stockholders_equity=eq
            if getattr(m,'debt_to_equity',None) is None and eq not in (None,0) and debt is not None: m.debt_to_equity=debt/eq
            if getattr(m,'operating_cash_flow',None) is None: m.operating_cash_flow=cfo
            if getattr(m,'free_cash_flow',None) is None and cfo is not None and capex is not None: m.free_cash_flow=cfo-abs(capex)
            if getattr(m,'ebit',None) is None and op is not None: m.ebit=op
            if getattr(m,'interest_expense',None) is None and interest is not None: m.interest_expense=abs(interest)
            arr=_annual_two(facts,_TAGS['revenue'])
            if getattr(m,'revenue_growth',None) is None and len(arr)>=2 and arr[1] not in (0,None): m.revenue_growth=arr[0]/arr[1]-1
            arr=_annual_two(facts,_TAGS['net_income'])
            if getattr(m,'earnings_growth',None) is None and len(arr)>=2 and arr[1] not in (0,None): m.earnings_growth=arr[0]/arr[1]-1
            if not getattr(m,'annual_quality_history',None): m.annual_quality_history=_annual_quality_history(facts)
            if not getattr(m,'annual_dividend_history',None): m.annual_dividend_history=[{'date':d,'value':v} for d,v in _annual(facts,_TAGS['dividends'],4)]
            if getattr(m,'roce_proxy',None) is None and op is not None:
                invested=(eq or 0)+(debt or 0)-(cash or 0) if any(v is not None for v in (eq,debt,cash)) else None
                if invested is not None and invested>0: m.roce_proxy=op/invested
            setattr(m,'sec_edgar_enriched',True); filled+=1; time.sleep(.08)
        except Exception as e:
            log.debug('SEC %s: %s',t,e)
    log.info('SEC EDGAR enriched %d rows',filled)
    return raw
