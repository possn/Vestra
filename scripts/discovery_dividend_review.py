"""Manual, source-attested promotion of Discovery dividend candidates.

A vendor ex-date/amount is NOT evidence that cash was paid. This module is
deliberately NOT called by any scheduled job. An authorised reviewer must
supply an issuer-domain primary document and an actual payment date.
No network search, heuristic auto-approval, yield inference or quote changes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
from urllib.parse import urlparse

try:
    from scripts.discovery_dividend_evidence import validated_events
except ModuleNotFoundError:
    from discovery_dividend_evidence import validated_events

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "dividend_event_candidates.json"
ISSUERS = ROOT / "data" / "dividend_issuer_domains.json"
VERIFIED = ROOT / "data" / "verified_dividend_events.json"


def domain_matches(url, allowed_domains):
    """Only a vetted issuer domain or subdomain may support approval."""
    parsed = urlparse(str(url or ""))
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return False
    return any(
        host == domain or host.endswith("." + domain)
        for domain in allowed_domains
        if isinstance(domain, str) and domain.strip()
    )


def prepare_review(approvals, candidate_report, issuer_registry,
                   existing_ledger, reviewed_on):
    """Return fully validated ledger, without writing it.

    Approval fields: ticker, ex_date, amount_per_share, currency,
    payment_date, issuer_source_url, reviewed_by, reviewed_at.
    Issuer registry: {"schema_version":1,"domains":{"TICKER":["issuer.com"]}}.
    """
    if not isinstance(approvals, list) or not approvals:
        raise ValueError("Manual approvals array must be nonempty")
    if not isinstance(candidate_report, dict) or candidate_report.get("schema_version") != 1:
        raise ValueError("Candidate report missing or unsupported")
    if candidate_report.get("status") != "candidates_only_unverified":
        raise ValueError("Cannot review a non-pending candidate report")
    if not isinstance(issuer_registry, dict) or issuer_registry.get("schema_version") != 1:
        raise ValueError("Issuer-domain registry missing or unsupported")
    domains = issuer_registry.get("domains")
    if not isinstance(domains, dict):
        raise ValueError("Issuer-domain registry requires domains object")
    if not isinstance(existing_ledger, dict) or existing_ledger.get("schema_version") != 1:
        raise ValueError("A valid verified dividend ledger is required")
    known = validated_events(existing_ledger)
    candidates = candidate_report.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Candidate report has no candidate list")
    candidate_keys = set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("status") != "pending_issuer_verification":
            raise ValueError("Candidate report includes non-pending record")
        try:
            key = (str(candidate["ticker"]).upper(), str(candidate["ex_date"]),
                   round(float(candidate["amount_per_share"]), 10))
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Malformed candidate identity") from exc
        candidate_keys.add(key)

    output = list(existing_ledger.get("events") or [])
    existing_keys = {
        (e["ticker"], e["ex_date"].isoformat(), round(e["amount_per_share"], 10))
        for e in known
    }
    seen_approvals = set()
    for idx, approval in enumerate(approvals, 1):
        if not isinstance(approval, dict):
            raise ValueError(f"Approval {idx}: expected object")
        try:
            ticker = str(approval["ticker"]).strip().upper()
            ex_date = dt.date.fromisoformat(str(approval["ex_date"]))
            amount = float(approval["amount_per_share"])
            payment_date = dt.date.fromisoformat(str(approval["payment_date"]))
            reviewed_at = dt.date.fromisoformat(str(approval["reviewed_at"]))
            reviewer = str(approval["reviewed_by"]).strip()
            currency = str(approval["currency"]).strip().upper()
            evidence_url = str(approval["issuer_source_url"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Approval {idx}: missing or invalid fields") from exc
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(f"Approval {idx}: invalid cash amount")
        key = (ticker, ex_date.isoformat(), round(amount, 10))
        if key not in candidate_keys:
            raise ValueError(f"Approval {idx}: no matching Yahoo candidate")
        if key in seen_approvals:
            raise ValueError(f"Approval {idx}: duplicate review")
        seen_approvals.add(key)
        if key in existing_keys:
            raise ValueError(f"Approval {idx}: already verified (manual amendment required)")
        allowed = domains.get(ticker)
        if not isinstance(allowed, list) or not allowed:
            raise ValueError(f"Approval {idx}: issuer domains not independently registered")
        if not domain_matches(evidence_url, allowed):
            raise ValueError(f"Approval {idx}: evidence URL is not on a registered issuer domain")
        if not reviewer or not (ex_date <= payment_date <= reviewed_at <= reviewed_on):
            raise ValueError(f"Approval {idx}: payment/review chronology or reviewer invalid")
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError(f"Approval {idx}: ISO currency required")
        matches = [c for c in candidates if isinstance(c, dict)
                   and str(c.get("ticker") or "").upper() == ticker
                   and str(c.get("ex_date")) == ex_date.isoformat()
                   and round(float(c.get("amount_per_share") or 0), 10) == key[2]]
        if any(c.get("currency_hint") and str(c["currency_hint"]).upper() != currency
               for c in matches):
            raise ValueError(f"Approval {idx}: currency conflicts with frozen candidate hint")
        output.append({
            "ticker": ticker, "ex_date": ex_date.isoformat(),
            "payment_date": payment_date.isoformat(),
            "amount_per_share": amount, "currency": currency,
            "source_url": evidence_url, "status": "confirmed",
            "reviewed_by": reviewer, "reviewed_at": reviewed_at.isoformat(),
            "verification_method": "manual_issuer_document",
        })
    result = {"schema_version": 1, "events": output}
    validated_events(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approvals", type=Path, required=True,
                        help="Explicit manually prepared approvals JSON file")
    parser.add_argument("--out", type=Path, default=VERIFIED,
                        help="Reviewed ledger output (dry-run by default)")
    parser.add_argument("--write", action="store_true",
                        help="Explicitly write verified ledger after full validation")
    args = parser.parse_args()
    approvals = json.loads(args.approvals.read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    issuers = json.loads(ISSUERS.read_text(encoding="utf-8"))
    existing = (json.loads(VERIFIED.read_text(encoding="utf-8"))
                if VERIFIED.exists() else {"schema_version": 1, "events": []})
    result = prepare_review(approvals, candidates, issuers,
                            existing, dt.date.today())
    summary = {"approved_new": len(result["events"]) - len(existing["events"]),
               "total_verified": len(result["events"]), "write": args.write}
    if args.write:
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                       allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
