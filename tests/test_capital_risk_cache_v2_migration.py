import json
from types import SimpleNamespace

from scripts import capital_risk_cache_runtime as runtime


def _rows(doc="a.htm"):
    return [
        {"accession": "0000000000-26-000001", "date": "2026-09-01", "form": "8-K", "doc": doc},
        {"accession": "0000000000-26-000002", "date": "2026-08-20", "form": "S-3", "doc": "s3.htm"},
    ]


def _module(cache_path):
    module = SimpleNamespace()
    module.CACHE_PATH = str(cache_path)
    module.CACHE_FIELDS = (
        "capital_structure_flags",
        "capital_structure_risk",
        "reverse_split_count_24m",
        "reverse_split_latest_date",
        "capital_risk_filings_checked",
    )
    module.CAPITAL_RISK_SCANNER_VERSION = runtime.LEGACY_CACHE_VERSION
    module._filings_fingerprint = runtime.legacy_fingerprint
    module._load_previous = lambda path=None: {}

    def original_apply(obj, previous, fingerprint):
        if previous.get("scanner_version") != module.CAPITAL_RISK_SCANNER_VERSION:
            return False
        if previous.get("filings_fingerprint") != fingerprint:
            return False
        return True

    module._apply_previous_if_unchanged = original_apply
    return module


def _legacy_record(rows):
    return {
        "scanner_version": runtime.LEGACY_CACHE_VERSION,
        "filings_fingerprint": runtime.legacy_fingerprint(rows),
        "capital_structure_flags": ["atm_offering"],
        "capital_structure_risk": "watch",
        "reverse_split_count_24m": 0,
        "reverse_split_latest_date": None,
        "capital_risk_filings_checked": 2,
    }


def test_stable_fingerprint_ignores_transport_specific_document_location():
    api_rows = _rows(doc="primary.htm")
    archive_rows = [
        {"accession": row["accession"], "date": row["date"], "form": row["form"], "archive_url": f"https://www.sec.gov/Archives/{row['accession']}.txt"}
        for row in api_rows
    ]
    assert runtime.stable_fingerprint(api_rows) == runtime.stable_fingerprint(archive_rows)
    assert runtime.legacy_fingerprint(api_rows) != runtime.legacy_fingerprint(archive_rows)


def test_unchanged_v2_cache_migrates_without_rescan(tmp_path):
    rows = _rows()
    cache = tmp_path / "capital_risk_cache.json"
    cache.write_text(json.dumps({
        "scanner_version": runtime.LEGACY_CACHE_VERSION,
        "rows": {"MSFT": _legacy_record(rows)},
    }), encoding="utf-8")

    module = _module(cache)
    runtime.install(module)
    previous = module._load_previous()["MSFT"]
    fingerprint = module._filings_fingerprint(rows)
    obj = SimpleNamespace()

    assert module._apply_previous_if_unchanged(obj, previous, fingerprint) is True
    assert obj.capital_risk_checked is True
    assert obj.capital_risk_reused is True
    assert obj.capital_structure_flags == ["atm_offering"]
    assert obj.capital_structure_risk == "watch"


def test_v2_migration_fails_closed_when_transport_or_filings_changed(tmp_path):
    old_rows = _rows(doc="primary.htm")
    cache = tmp_path / "capital_risk_cache.json"
    cache.write_text(json.dumps({
        "scanner_version": runtime.LEGACY_CACHE_VERSION,
        "rows": {"MSFT": _legacy_record(old_rows)},
    }), encoding="utf-8")

    module = _module(cache)
    runtime.install(module)
    previous = module._load_previous()["MSFT"]

    transport_changed = _rows(doc="different-primary.htm")
    fp_transport = module._filings_fingerprint(transport_changed)
    assert module._apply_previous_if_unchanged(SimpleNamespace(), previous, fp_transport) is False

    filings_changed = _rows() + [
        {"accession": "0000000000-26-000003", "date": "2026-09-05", "form": "8-K", "doc": "new.htm"}
    ]
    fp_new = module._filings_fingerprint(filings_changed)
    assert module._apply_previous_if_unchanged(SimpleNamespace(), previous, fp_new) is False
