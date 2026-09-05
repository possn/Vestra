"""Current filings.xbrl.org enrichment adapter for Vestra v4.20.

Uses documented /api/filings plus a public entity-page fallback. Identity is
strict: ticker -> exact ISIN -> GLEIF LEI. Yahoo remains the first ISIN source;
London-listed equities gain an official LSE TIDM->ISIN fallback. Only standard
IFRS concepts are used and no fuzzy issuer matching is permitted.
"""
from __future__ import annotations
import datetime as dt, gzip, json, logging, math, re, time
from urllib.parse import urljoin
import requests, yfinance as yf
from lse_identity import resolve_isin as resolve_lse_isin
from asset_types import is_equity_candidate

log=logging.getLogger('esef_enrich')
BASE='https://filings.xbrl.org'; GLEIF='https://api.gleif.org/api/v1/lei-records'
UA='Vestra/4.20 (+https://github.com/possn/Vestra)'
ISIN_RE=re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
COUNTRY={'.L':'GB','.PA':'FR','.AS':'NL','.BR':'BE','.MC':'ES','.MI':'IT','.ST':'SE','.HE':'FI','.CO':'DK','.OL':'NO','.LS':'PT','.VI':'AT','.WA':'PL','.PR':'CZ','.AT':'GR','.SW':'CH','.DE':'DE'}
ALLOWED={'concept','entity','period','unit','language'}
C={
'revenue':('Revenue','RevenueFromContractsWithCustomers','RevenueFromContractsWithCustomersExcludingAssessedTax'),
'net_income':('ProfitLoss','ProfitLossAttributableToOwnersOfParent'),
'operating_income':('ProfitLossFromOperatingActivities','OperatingProfitLoss'),
'gross_profit':('GrossProfit',),'assets':('Assets',),'current_assets':('CurrentAssets',),'current_liab':('CurrentLiabilities',),
'equity':('Equity','EquityAttributableToOwnersOfParent'),'cash':('CashAndCashEquivalents','CashAndCashEquivalentsAtCarryingValue'),
'inventory':('Inventories',),'cfo':('CashFlowsFromUsedInOperatingActivities','CashFlowsFromUsedInOperations'),
'capex':('PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities','PaymentsToAcquirePropertyPlantAndEquipment','PurchaseOfPropertyPlantAndEquipment'),
'debt_cur':('CurrentBorrowings','CurrentPortionOfNoncurrentBorrowings'),'debt_non':('NoncurrentBorrowings','LongtermBorrowings'),
'interest':('InterestExpense','FinanceCosts')}

# Temporary observation carried only through run.py's existing annual-quality
# passthrough. normalize_market_provenance.py consumes and removes it before the
# validated snapshot can be published. The metrics are deliberately restricted to
# definitions that match Yahoo's annual statement-derived history closely enough
# for a same-period diagnostic comparison. ROCE is excluded because the two
# adapters currently use different capital-employed definitions.
ESEF_AGREEMENT_OBSERVATION_KEY='_esef_same_period_observation'
AGREEMENT_METRICS=('gross_margin','operating_margin','net_margin','roe')

def session():
    s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept':'application/vnd.api+json, application/json, text/html;q=0.8'}); return s

def country_for(t):
    u=str(t or '').upper(); return next((v for k,v in COUNTRY.items() if u.endswith(k)),None)

def _finite(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None

def attach_same_period_observation(m,period_end,esef_values):
    """Attach ESEF values only when Yahoo has the exact same annual period.

    The observation is diagnostic-only and intentionally temporary. It does not
    replace canonical metrics and is removed by provenance normalization before
    publication. Returns True when at least one comparable metric is attached.
    """
    period_text=str(period_end or '').strip()[:10]
    history=getattr(m,'annual_quality_history',None)
    if not period_text or not isinstance(history,list): return False
    clean={k:_finite((esef_values or {}).get(k)) for k in AGREEMENT_METRICS}
    clean={k:v for k,v in clean.items() if v is not None}
    if not clean: return False
    for item in history:
        if not isinstance(item,dict) or str(item.get('date') or '').strip()[:10]!=period_text: continue
        comparable={k:v for k,v in clean.items() if _finite(item.get(k)) is not None}
        if not comparable: return False
        item[ESEF_AGREEMENT_OBSERVATION_KEY]={
            'period_end':period_text,
            'source_family':'esef',
            'metrics':comparable,
        }
        return True
    return False

def _yahoo_isin(t):
    try: x=str(yf.Ticker(t).isin or '').strip().upper()
    except Exception: return None
    return x if ISIN_RE.match(x) else None

def resolve_isin_with_source(t,s=None):
    x=_yahoo_isin(t)
    if x: return x,'Yahoo Finance'
    if str(t or '').upper().endswith('.L'):
        try: x=resolve_lse_isin(t,s)
        except Exception: x=None
        if x and ISIN_RE.match(str(x).upper()): return str(x).upper(),'London Stock Exchange official instrument API'
    return None,None

def resolve_isin(t,s=None):
    return resolve_isin_with_source(t,s)[0]

def resolve_lei(s,isin):
    try:
        r=s.get(GLEIF,params={'filter[isin]':isin,'page[size]':5},timeout=18); r.raise_for_status()
        ids={str(x.get('id') or '').strip() for x in (r.json().get('data') or []) if x.get('id')}
        return next(iter(ids)) if len(ids)==1 else None
    except Exception: return None

def json_link(s,fid):
    try:
        r=s.get(f'{BASE}/filing/{fid}',timeout=20); r.raise_for_status()
        links=re.findall(r'href=["\']([^"\']+\.json(?:\.gz)?(?:\?[^"\']*)?)["\']',r.text,re.I)
        if not links: return None
        links.sort(key=lambda x:("-en." not in x.lower(),x.lower().endswith('.gz')))
        return urljoin(BASE,links[0])
    except Exception: return None

def latest_filing(s,lei,country=None):
    cand=[]
    try:
        r=s.get(f'{BASE}/api/filings',params={'filter[entity.identifier]':lei,'sort':'-processed','page[size]':30,'include':'entity'},timeout=22); r.raise_for_status()
        for item in r.json().get('data') or []:
            a=item.get('attributes') or {}; c=str(a.get('country') or '').upper()
            if country and c and c!=country: continue
            fid=str(item.get('id') or ''); u=a.get('json_url') or a.get('xbrl_json_url') or (json_link(s,fid) if fid else None)
            if u: cand.append((str(a.get('period_end') or a.get('report_date') or ''),str(a.get('language') or '').lower() in ('en','eng','english'),urljoin(BASE,u),fid,'api'))
    except Exception as e: log.debug('ESEF API %s: %s',lei,e)
    if not cand:
        try:
            r=s.get(f'{BASE}/entity/{lei}',timeout=22); r.raise_for_status()
            ids=re.findall(r'/filing/([A-Z0-9]{20}-\d{4}-\d{2}-\d{2}-(?:ESEF|UKSEF)-[A-Z]{2}-\d+)',r.text,re.I)
            for fid in dict.fromkeys(ids):
                m=re.match(r'^[A-Z0-9]{20}-(\d{4}-\d{2}-\d{2})-(?:ESEF|UKSEF)-([A-Z]{2})-',fid,re.I)
                if not m or (country and m.group(2).upper()!=country): continue
                u=json_link(s,fid)
                if u: cand.append((m.group(1),False,u,fid,'html'))
        except Exception as e: log.debug('ESEF entity %s: %s',lei,e)
    if not cand: return None
    cand.sort(key=lambda x:(x[0],x[1]),reverse=True); p,_,u,fid,path=cand[0]
    return {'period_end':p,'json_url':u,'filing_id':fid,'path':path}

def report(s,f):
    try:
        r=s.get(f['json_url'],timeout=40); r.raise_for_status(); b=r.content
        if f['json_url'].lower().split('?',1)[0].endswith('.gz'): b=gzip.decompress(b)
        return json.loads(b.decode('utf-8'))
    except Exception: return None

def local(v): return str(v or '').rsplit('#',1)[-1].split(':',1)[-1]
def period(v):
    try:
        if '/' in v:
            a,b=v.split('/',1); return dt.date.fromisoformat(a[:10]),dt.date.fromisoformat(b[:10])
        return None,dt.date.fromisoformat(v[:10])
    except Exception: return None,None

def rows(rep,key,duration):
    out=[]; wanted=set(C[key])
    for f in (rep.get('facts') or {}).values():
        d=f.get('dimensions') or {}
        if local(d.get('concept')) not in wanted or set(d)-ALLOWED: continue
        try: val=float(f.get('value'))
        except Exception: continue
        st,en=period(str(d.get('period') or '')); isdur=st is not None
        if en is None or isdur!=duration or (isdur and not 250<=(en-st).days<=390): continue
        out.append((en,val))
    by={}
    for d,v in out: by.setdefault(d,set()).add(v)
    z=[(d,next(iter(vs))) for d,vs in by.items() if len(vs)==1]; z.sort(key=lambda x:x[0],reverse=True); return z

def latest(rep,key,duration):
    x=rows(rep,key,duration); return x[0][1] if x else None

def growth(rep,key):
    x=rows(rep,key,True)
    if len(x)<2 or x[1][1] in (0,None): return None
    g=abs((x[0][0]-x[1][0]).days); return x[0][1]/x[1][1]-1 if 300<=g<=430 else None

def set_missing(m,k,v):
    if v is not None and getattr(m,k,None) is None: setattr(m,k,v); return True
    return False

def enrich(raw,priority=None,max_nonpriority=220):
    priority=set(priority or []); s=session(); non=0; done=0; lse_identity_hits=0
    diag={
        'eligible':0,'attempted':0,'isin_resolved':0,'isin_missing':0,
        'lei_resolved':0,'lei_missing':0,'filing_found':0,'filing_missing':0,
        'report_parsed':0,'report_failed':0,'enriched':0,'same_period_observations':0,
    }
    for m in raw:
        t=str(getattr(m,'ticker','') or '').upper(); c=country_for(t)
        if not c or not is_equity_candidate(getattr(m,'quote_type',None)): continue
        diag['eligible']+=1
        miss=sum(getattr(m,k,None) is None for k in ('roe','roa','profit_margin','operating_margin','gross_margin','revenue_growth','free_cash_flow','current_ratio','quick_ratio','debt_to_equity','operating_cash_flow'))
        if miss<2 and t not in priority: continue
        if t not in priority:
            non+=1
            if non>max_nonpriority: continue
        diag['attempted']+=1
        isin,isin_source=resolve_isin_with_source(t,s)
        if not isin:
            diag['isin_missing']+=1
            continue
        diag['isin_resolved']+=1
        lei=resolve_lei(s,isin)
        if not lei:
            diag['lei_missing']+=1
            continue
        diag['lei_resolved']+=1
        f=latest_filing(s,lei,c)
        if not f:
            diag['filing_missing']+=1
            continue
        diag['filing_found']+=1
        rep=report(s,f)
        if not rep:
            diag['report_failed']+=1
            continue
        diag['report_parsed']+=1
        rev=latest(rep,'revenue',True); ni=latest(rep,'net_income',True); op=latest(rep,'operating_income',True); gp=latest(rep,'gross_profit',True)
        a=latest(rep,'assets',False); e=latest(rep,'equity',False); ca=latest(rep,'current_assets',False); cl=latest(rep,'current_liab',False); inv=latest(rep,'inventory',False); cash=latest(rep,'cash',False)
        cfo=latest(rep,'cfo',True); capex=latest(rep,'capex',True); dc=latest(rep,'debt_cur',False); dn=latest(rep,'debt_non',False); interest=latest(rep,'interest',True)
        debt=(dc or 0)+(dn or 0) if dc is not None or dn is not None else None

        # Observe same-period agreement before fill-missing changes canonical fields.
        # Yahoo values come from annual_quality_history (annual statements), never
        # from the current/TTM quoteSummary ratios.
        esef_quality={}
        if rev not in (None,0):
            if gp is not None: esef_quality['gross_margin']=gp/rev
            if op is not None: esef_quality['operating_margin']=op/rev
            if ni is not None: esef_quality['net_margin']=ni/rev
        if ni is not None and e not in (None,0): esef_quality['roe']=ni/e
        if attach_same_period_observation(m,f.get('period_end'),esef_quality):
            diag['same_period_observations']+=1

        if rev not in (None,0):
            set_missing(m,'profit_margin',ni/rev if ni is not None else None); set_missing(m,'operating_margin',op/rev if op is not None else None); set_missing(m,'gross_margin',gp/rev if gp is not None else None)
        set_missing(m,'roe',ni/e if ni is not None and e not in (None,0) else None); set_missing(m,'roa',ni/a if ni is not None and a not in (None,0) else None)
        set_missing(m,'current_ratio',ca/cl if ca is not None and cl not in (None,0) else None); set_missing(m,'quick_ratio',(ca-inv)/cl if ca is not None and inv is not None and cl not in (None,0) else None)
        set_missing(m,'debt_to_equity',debt/e if debt is not None and e not in (None,0) else None); set_missing(m,'total_assets',a); set_missing(m,'stockholders_equity',e); set_missing(m,'total_cash',cash); set_missing(m,'total_debt',debt); set_missing(m,'operating_cash_flow',cfo)
        set_missing(m,'free_cash_flow',cfo-abs(capex) if cfo is not None and capex is not None else None); set_missing(m,'ebit',op); set_missing(m,'interest_expense',abs(interest) if interest is not None else None); set_missing(m,'revenue_growth',growth(rep,'revenue')); set_missing(m,'earnings_growth',growth(rep,'net_income'))
        if op is not None and e is not None and debt is not None and cash is not None and e+debt-cash>0: set_missing(m,'roce_proxy',op/(e+debt-cash))
        m.isin=isin; m.isin_source=isin_source; m.lei=lei; m.esef_period_end=f.get('period_end'); m.esef_enriched=True; m.esef_retrieval_path=f.get('path'); done+=1; diag['enriched']+=1
        if isin_source and isin_source.startswith('London Stock Exchange'): lse_identity_hits+=1
        time.sleep(.05)
    log.info('ESEF v4.20 enriched %d rows (%d via LSE identity fallback)',done,lse_identity_hits)
    log.info('ESEF funnel %s',json.dumps(diag,sort_keys=True,separators=(',',':')))
    return raw
