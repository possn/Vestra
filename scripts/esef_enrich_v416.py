"""Current filings.xbrl.org adapter for Vestra v4.16.

Uses the documented /api/filings resource and a public entity-page fallback.
This module is intentionally conservative: exact LEI identity, standard IFRS
concepts only, and no issuer-name fuzzy matching.
"""
from __future__ import annotations
import gzip, json, logging, re
from urllib.parse import urljoin
import requests

log=logging.getLogger('esef_v416')
BASE='https://filings.xbrl.org'
UA='Vestra/4.16 (+https://github.com/possn/Vestra)'
_ALLOWED={'concept','entity','period','unit','language'}


def _session():
    s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept':'application/vnd.api+json, application/json, text/html;q=0.8'}); return s


def _json_link(sess, filing_id):
    try:
        r=sess.get(f'{BASE}/filing/{filing_id}',timeout=20); r.raise_for_status()
        links=re.findall(r'href=["\']([^"\']+\.json(?:\.gz)?(?:\?[^"\']*)?)["\']',r.text,re.I)
        if not links: return None
        links.sort(key=lambda x:("-en." not in x.lower(), x.lower().endswith('.gz')))
        return urljoin(BASE,links[0])
    except Exception as e:
        log.debug('filing page %s: %s',filing_id,e); return None


def latest_filing(lei, country=None):
    s=_session(); rows=[]
    try:
        r=s.get(f'{BASE}/api/filings',params={'filter[entity.identifier]':lei,'sort':'-processed','page[size]':30,'include':'entity'},timeout=22)
        r.raise_for_status(); rows=r.json().get('data') or []
    except Exception as e:
        log.debug('api filings %s: %s',lei,e)
    candidates=[]
    for item in rows:
        a=item.get('attributes') or {}; c=str(a.get('country') or '').upper()
        if country and c and c!=country: continue
        system=str(a.get('filing_system') or a.get('system') or '').upper()
        if system and system not in ('ESEF','UKSEF'): continue
        fid=str(item.get('id') or ''); url=a.get('json_url') or a.get('xbrl_json_url') or (_json_link(s,fid) if fid else None)
        if url: candidates.append((str(a.get('period_end') or a.get('report_date') or ''),str(a.get('language') or '').lower() in ('en','eng','english'),urljoin(BASE,url),fid))
    if not candidates:
        try:
            r=s.get(f'{BASE}/entity/{lei}',timeout=20); r.raise_for_status()
            ids=re.findall(r'/filing/([A-Z0-9]{20}-\d{4}-\d{2}-\d{2}-(?:ESEF|UKSEF)-[A-Z]{2}-\d+)',r.text,re.I)
            for fid in dict.fromkeys(ids):
                m=re.match(r'^[A-Z0-9]{20}-(\d{4}-\d{2}-\d{2})-(?:ESEF|UKSEF)-([A-Z]{2})-',fid,re.I)
                if not m or (country and m.group(2).upper()!=country): continue
                url=_json_link(s,fid)
                if url: candidates.append((m.group(1),False,url,fid))
        except Exception as e:
            log.debug('entity fallback %s: %s',lei,e)
    if not candidates: return None
    candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
    p,_,u,fid=candidates[0]; return {'period_end':p,'json_url':u,'filing_id':fid}


def fetch_report(filing):
    if not filing: return None
    try:
        r=_session().get(filing['json_url'],timeout=40); r.raise_for_status(); data=r.content
        if filing['json_url'].lower().split('?',1)[0].endswith('.gz'): data=gzip.decompress(data)
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        log.debug('xbrl-json %s: %s',filing.get('json_url'),e); return None


def local_concept(v):
    s=str(v or '').rsplit('#',1)[-1]; return s.split(':',1)[-1]


def facts(report, concepts):
    wanted=set(concepts); out=[]
    for fact in (report or {}).get('facts',{}).values():
        d=fact.get('dimensions') or {}
        if local_concept(d.get('concept')) not in wanted or set(d)-_ALLOWED: continue
        try: value=float(fact.get('value'))
        except (TypeError,ValueError): continue
        if value==value and abs(value)!=float('inf'): out.append((d.get('period'),value))
    return out
