from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

REQUESTS_AVAILABLE = importlib.util.find_spec("requests") is not None

if REQUESTS_AVAILABLE:
    import capital_risk
    import capital_risk_cache_runtime


def _api_rows():
    return [
        {"accession": "0000320193-26-000090", "date": "2026-08-07", "form": "8-K", "doc": "primary.htm"},
        {"accession": "0000320193-26-000079", "date": "2026-07-31", "form": "10-K", "doc": "annual.htm"},
    ]


def _archive_rows():
    return [
        {"accession": "0000320193-26-000090", "date": "2026-08-07", "form": "8-K", "doc": "", "archive_url": "https://www.sec.gov/Archives/edgar/data/320193/a.txt"},
        {"accession": "0000320193-26-000079", "date": "2026-07-31", "form": "10-K", "doc": "", "archive_url": "https://www.sec.gov/Archives/edgar/data/320193/b.txt"},
    ]


def test_same_filings_have_same_fingerprint_across_sec_transport():
    capital_risk_cache_runtime.install(capital_risk)
    assert capital_risk._filings_fingerprint(_api_rows()) == capital_risk._filings_fingerprint(_archive_rows())


def test_accession_date_or_form_change_invalidates_cache():
    capital_risk_cache_runtime.install(capital_risk)
    base = capital_risk._filings_fingerprint(_api_rows())
    changed = _api_rows()
    changed[0] = dict(changed[0], accession="0000320193-26-000091")
    assert capital_risk._filings_fingerprint(changed) != base


def test_runtime_versions_cache_contract_explicitly():
    capital_risk_cache_runtime.install(capital_risk)
    assert capital_risk.CAPITAL_RISK_SCANNER_VERSION == capital_risk_cache_runtime.CACHE_VERSION
    assert "transport-stable" in capital_risk.CAPITAL_RISK_SCANNER_VERSION


def test_install_is_idempotent():
    first = capital_risk_cache_runtime.install(capital_risk)
    second = capital_risk_cache_runtime.install(capital_risk)
    assert first is second


if __name__ == "__main__":
    if not REQUESTS_AVAILABLE:
        print("capital-risk transport cache tests skipped without requests")
    else:
        test_same_filings_have_same_fingerprint_across_sec_transport()
        test_accession_date_or_form_change_invalidates_cache()
        test_runtime_versions_cache_contract_explicitly()
        test_install_is_idempotent()
