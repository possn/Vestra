from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import capital_risk


class DummyMetrics:
    ticker = "TEST"


class FakeArchiveClient:
    def __init__(self, text):
        self.payload = text
        self.urls = []

    def text(self, url, timeout=30):
        self.urls.append(url)
        return self.payload


def sample_rows():
    return [
        {"accession": "0002", "date": "2026-08-02", "form": "8-K", "doc": "b.htm"},
        {"accession": "0001", "date": "2026-07-01", "form": "10-K", "doc": "a.htm"},
    ]


def test_fingerprint_is_order_independent_and_input_sensitive():
    rows = sample_rows()
    fp = capital_risk._filings_fingerprint(rows)
    assert fp == capital_risk._filings_fingerprint(list(reversed(rows)))

    changed = [dict(row) for row in rows]
    changed[0]["accession"] = "0003"
    assert capital_risk._filings_fingerprint(changed) != fp


def test_archives_discovery_uses_exact_cik_and_full_submission_url():
    master = "\n".join([
        "CIK|Company Name|Form Type|Date Filed|Filename",
        "320193|Apple Inc.|8-K|2026-08-07|edgar/data/320193/0000320193-26-000090.txt",
        "320193|Apple Inc.|10-K|2025-10-31|edgar/data/320193/0000320193-25-000079.txt",
        "789019|Microsoft Corp.|8-K|2026-07-30|edgar/data/789019/0000789019-26-000088.txt",
        "320193|Apple Inc.|4|2026-08-08|edgar/data/320193/0000320193-26-000091.txt",
    ])
    client = FakeArchiveClient(master)
    grouped = capital_risk._archive_rows_by_cik(client=client, quarter_count=1)

    assert set(grouped) == {320193, 789019}
    assert len(grouped[320193]) == 2
    assert grouped[320193][0]["form"] == "8-K"
    assert grouped[320193][0]["archive_url"] == (
        "https://www.sec.gov/Archives/edgar/data/320193/0000320193-26-000090.txt"
    )
    assert grouped[789019][0]["accession"] == "0000789019-26-000088"
    assert len(client.urls) == 1


def test_archive_url_participates_in_fingerprint():
    row = {
        "accession": "0000320193-26-000090",
        "date": "2026-08-07",
        "form": "8-K",
        "doc": "",
        "archive_url": "https://www.sec.gov/Archives/edgar/data/320193/a.txt",
    }
    changed = dict(row, archive_url="https://www.sec.gov/Archives/edgar/data/320193/b.txt")
    assert capital_risk._filings_fingerprint([row]) != capital_risk._filings_fingerprint([changed])


def test_previous_result_reused_only_for_exact_version_and_fingerprint():
    fp = capital_risk._filings_fingerprint(sample_rows())
    previous = {
        "scanner_version": capital_risk.CAPITAL_RISK_SCANNER_VERSION,
        "filings_fingerprint": fp,
        "capital_structure_flags": ["atm_offering"],
        "capital_structure_risk": "watch",
        "reverse_split_count_24m": 0,
        "reverse_split_latest_date": None,
        "capital_risk_filings_checked": 4,
    }
    metrics = DummyMetrics()
    assert capital_risk._apply_previous_if_unchanged(metrics, previous, fp) is True
    assert metrics.capital_structure_flags == ["atm_offering"]
    assert metrics.capital_structure_risk == "watch"
    assert metrics.capital_risk_checked is True
    assert metrics.capital_risk_reused is True

    wrong_fp = DummyMetrics()
    assert capital_risk._apply_previous_if_unchanged(wrong_fp, previous, "different") is False

    wrong_version = dict(previous, scanner_version="old-rules")
    assert capital_risk._apply_previous_if_unchanged(DummyMetrics(), wrong_version, fp) is False


def test_cache_round_trip_is_version_gated():
    fp = capital_risk._filings_fingerprint(sample_rows())
    record = capital_risk._cache_record({
        "capital_structure_flags": [],
        "capital_structure_risk": "clear",
        "reverse_split_count_24m": 0,
        "reverse_split_latest_date": None,
        "capital_risk_filings_checked": 3,
    }, fp)

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "capital_risk_cache.json")
        capital_risk._write_cache({"TEST": record}, path=path)
        loaded = capital_risk._load_previous(path=path)
        assert loaded["TEST"]["filings_fingerprint"] == fp
        assert loaded["TEST"]["scanner_version"] == capital_risk.CAPITAL_RISK_SCANNER_VERSION

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload["scanner_version"] = "different-rules"
        Path(path).write_text(json.dumps(payload), encoding="utf-8")
        assert capital_risk._load_previous(path=path) == {}


if __name__ == "__main__":
    test_fingerprint_is_order_independent_and_input_sensitive()
    test_archives_discovery_uses_exact_cik_and_full_submission_url()
    test_archive_url_participates_in_fingerprint()
    test_previous_result_reused_only_for_exact_version_and_fingerprint()
    test_cache_round_trip_is_version_gated()
