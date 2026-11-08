"""Diagnostic-only audit of persisted SEC Form 4 issuer provenance.

Does not infer fraud, alter transaction totals, or count missing data as zero buys.
Cross-CIK reuse of an accession is reviewed separately from legitimate multiple
transactions within one accession.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data"/"insider_filings_cache.json"
OUT=ROOT/"data"/"insider_identity_audit.json"


def cik(value):
    if isinstance(value,bool):
        return None
    try:
        number=int(str(value))
        return str(number) if number>0 else None
    except (TypeError,ValueError,OverflowError):
        return None


def analyze(payload):
    filings=payload.get("filings") if isinstance(payload,dict) else None
    if not isinstance(filings,dict):
        return {"state":"unavailable","reason":"filing_dictionary_missing_or_invalid",
                "cache_rows":None,"validated_rows":None}
    counters=collections.Counter()
    accession_issuers=collections.defaultdict(set)
    examples=[]
    for key,row in filings.items():
        counters["cache_rows"]+=1
        if not isinstance(row,dict):
            counters["invalid_rows"]+=1
            continue
        issuer=cik(row.get("issuer_cik"))
        expected=cik(row.get("cik"))
        accession=str(row.get("accession") or "").strip()
        tx=row.get("transactions")
        key_issuer,key_delim,key_acc=str(key).partition(":")
        key_valid=bool(key_delim and cik(key_issuer)==expected and key_acc==accession)
        if not issuer or not expected or not accession or not isinstance(tx,list):
            counters["missing_identity_or_transactions"]+=1
            continue
        if not key_valid or issuer!=expected:
            counters["issuer_or_cache_key_mismatch"]+=1
            if len(examples)<12:examples.append({"cache_key":str(key)[:120],"reason":"issuer_or_cache_key_mismatch"})
            continue
        if not tx or any(not isinstance(t,dict) or cik(t.get("issuer_cik"))!=expected for t in tx):
            counters["missing_or_mismatched_transaction_issuer"]+=1
            continue
        counters["verified_rows"]+=1
        counters["verified_transactions"]+=len(tx)
        if len(tx)>1:counters["multi_transaction_filings"]+=1
        accession_issuers[accession].add(issuer)
    cross=[x for x,issuers in accession_issuers.items() if len(issuers)>1]
    return {"state":"audit_only_not_evidence_of_external_filing_validation",
            "cache_rows":counters["cache_rows"],
            "validated_rows":counters["verified_rows"],
            "validated_transactions":counters["verified_transactions"],
            "legacy_or_missing_identity_rows":counters["missing_identity_or_transactions"],
            "issuer_or_cache_key_mismatch_rows":counters["issuer_or_cache_key_mismatch"],
            "missing_or_mismatched_transaction_issuer_rows":counters["missing_or_mismatched_transaction_issuer"],
            "multiple_transactions_in_one_filing_rows":counters["multi_transaction_filings"],
            "accessions_reused_across_multiple_issuer_ciks":len(cross),
            "cross_issuer_accession_examples":sorted(cross)[:12],
            "mismatch_examples":examples,
            "limitations":["Audits persisted cache only, not original SEC XML",
                           "A repeated accession across CIKs needs source review; not automatically a duplicate",
                           "Invalid/missing cache rows are unavailable, not confirmed zero transactions",
                           "Issuer CIK does not by itself identify a share class or beneficial owner"]}


def main():
    try:
        payload=json.loads(SRC.read_text(encoding="utf-8"))
        report=analyze(payload)
    except (OSError,json.JSONDecodeError) as exc:
        report={"state":"unavailable","reason":type(exc).__name__,
                "cache_rows":None,"validated_rows":None}
    report["schema_version"]=1
    report["generated_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
    report["source_file"]="data/insider_filings_cache.json"
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("SEC issuer-provenance diagnostic:",report["state"],"rows=",report["cache_rows"])


if __name__=="__main__":
    main()
