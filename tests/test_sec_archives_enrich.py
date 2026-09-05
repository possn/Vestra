import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Architecture's historical suite deliberately runs without the heavy pipeline
# requirements installed. These modules are only needed at runtime network
# boundaries; the parser/enrichment tests below inject FakeClient and never use
# them, so keep the test isolated instead of requiring yfinance/requests.
if "yfinance" not in sys.modules:
    sys.modules["yfinance"] = types.ModuleType("yfinance")

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    adapters_stub = types.ModuleType("requests.adapters")
    adapters_stub.HTTPAdapter = object
    sys.modules["requests"] = requests_stub
    sys.modules["requests.adapters"] = adapters_stub

if "urllib3" not in sys.modules:
    urllib3_stub = types.ModuleType("urllib3")
    util_stub = types.ModuleType("urllib3.util")
    retry_stub = types.ModuleType("urllib3.util.retry")

    class Retry:
        def __init__(self, *args, **kwargs):
            pass

    retry_stub.Retry = Retry
    sys.modules["urllib3"] = urllib3_stub
    sys.modules["urllib3.util"] = util_stub
    sys.modules["urllib3.util.retry"] = retry_stub

from fundamentals import RawMetrics
import sec_archives_enrich as archives


MASTER = """Description:           Master Index of EDGAR Dissemination Feed
CIK|Company Name|Form Type|Date Filed|Filename
320193|Apple Inc.|10-Q|2026-08-01|edgar/data/320193/0000320193-26-000079.txt
320193|Apple Inc.|8-K|2026-08-02|edgar/data/320193/0000320193-26-000080.txt
789019|Microsoft Corp|10-K|2026-07-30|edgar/data/789019/0000950170-26-100001.txt
1045810|NVIDIA Corp|10-Q/A|2026-08-20|edgar/data/1045810/0001045810-26-000099.txt
"""

INDEX_HTML = """
<table><tr><td>1</td><td><a href="aapl-20260627_htm.xml">aapl-20260627_htm.xml</a></td>
<td>EXTRACTED XBRL INSTANCE DOCUMENT</td><td>XML</td><td>40518</td></tr>
<tr><td><a href="aapl-20260627_cal.xml">calculation</a></td></tr></table>
"""

XBRL = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2026" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <context id="I2026"><entity><identifier scheme="x">320193</identifier></entity><period><instant>2026-06-27</instant></period></context>
  <context id="Q2026"><entity><identifier scheme="x">320193</identifier></entity><period><startDate>2026-03-29</startDate><endDate>2026-06-27</endDate></period></context>
  <context id="Q2025"><entity><identifier scheme="x">320193</identifier></entity><period><startDate>2025-03-30</startDate><endDate>2025-06-28</endDate></period></context>
  <context id="YTD2026"><entity><identifier scheme="x">320193</identifier></entity><period><startDate>2025-09-28</startDate><endDate>2026-06-27</endDate></period></context>
  <dei:DocumentPeriodEndDate contextRef="I2026">2026-06-27</dei:DocumentPeriodEndDate>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="Q2026" unitRef="USD" decimals="-6">100000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="Q2025" unitRef="USD" decimals="-6">90000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:NetIncomeLoss contextRef="Q2026" unitRef="USD">25000000000</us-gaap:NetIncomeLoss>
  <us-gaap:NetIncomeLoss contextRef="Q2025" unitRef="USD">20000000000</us-gaap:NetIncomeLoss>
  <us-gaap:GrossProfit contextRef="Q2026" unitRef="USD">46000000000</us-gaap:GrossProfit>
  <us-gaap:OperatingIncomeLoss contextRef="Q2026" unitRef="USD">30000000000</us-gaap:OperatingIncomeLoss>
  <us-gaap:Assets contextRef="I2026" unitRef="USD">350000000000</us-gaap:Assets>
  <us-gaap:AssetsCurrent contextRef="I2026" unitRef="USD">150000000000</us-gaap:AssetsCurrent>
  <us-gaap:InventoryNet contextRef="I2026" unitRef="USD">5000000000</us-gaap:InventoryNet>
  <us-gaap:LiabilitiesCurrent contextRef="I2026" unitRef="USD">120000000000</us-gaap:LiabilitiesCurrent>
  <us-gaap:StockholdersEquity contextRef="I2026" unitRef="USD">70000000000</us-gaap:StockholdersEquity>
  <us-gaap:CashAndCashEquivalentsAtCarryingValue contextRef="I2026" unitRef="USD">40000000000</us-gaap:CashAndCashEquivalentsAtCarryingValue>
  <us-gaap:LongTermDebtCurrent contextRef="I2026" unitRef="USD">10000000000</us-gaap:LongTermDebtCurrent>
  <us-gaap:LongTermDebtNoncurrent contextRef="I2026" unitRef="USD">80000000000</us-gaap:LongTermDebtNoncurrent>
  <us-gaap:NetCashProvidedByUsedInOperatingActivities contextRef="YTD2026" unitRef="USD">90000000000</us-gaap:NetCashProvidedByUsedInOperatingActivities>
  <us-gaap:PaymentsToAcquirePropertyPlantAndEquipment contextRef="YTD2026" unitRef="USD">10000000000</us-gaap:PaymentsToAcquirePropertyPlantAndEquipment>
  <us-gaap:InterestExpenseNonOperating contextRef="Q2026" unitRef="USD">1000000000</us-gaap:InterestExpenseNonOperating>
</xbrl>
"""


class FakeResponse:
    def __init__(self, text="", content=None, status=200):
        self.text = text
        self.content = content if content is not None else text.encode()
        self.status_code = status

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, mapping):
        self.mapping = dict(mapping)
        self.requests = 0

    def text(self, url, timeout=25):
        self.requests += 1
        value = self.mapping[url]
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, str) else value.decode()

    def content(self, url, timeout=25):
        self.requests += 1
        value = self.mapping[url]
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, bytes) else value.encode()


class SecArchivesEnrichTests(unittest.TestCase):
    def test_recent_quarters_crosses_year_boundary(self):
        self.assertEqual(
            archives.recent_quarters(today=__import__("datetime").date(2026, 1, 2), count=4),
            [(2026, 1), (2025, 4), (2025, 3), (2025, 2)],
        )

    def test_master_index_uses_exact_supported_forms(self):
        rows = archives.parse_master_index(MASTER)
        self.assertEqual([(r["cik"], r["form"]) for r in rows], [(320193, "10-Q"), (789019, "10-K")])
        latest = archives.latest_filings_by_cik([MASTER])
        self.assertEqual(latest[320193]["accession"], "0000320193-26-000079")
        self.assertNotIn(1045810, latest)

    def test_filing_index_prefers_extracted_instance_not_calculation(self):
        index_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019326000079/0000320193-26-000079-index.htm"
        self.assertEqual(
            archives.find_xbrl_instance_url(INDEX_HTML, index_url),
            "https://www.sec.gov/Archives/edgar/data/320193/000032019326000079/aapl-20260627_htm.xml",
        )

    def test_xbrl_parser_preserves_periods_and_extracts_metrics(self):
        parsed = archives.parse_xbrl_instance(XBRL)
        self.assertEqual(parsed["period_end"], "2026-06-27")
        values = archives.extract_metrics(parsed, "10-Q")
        self.assertEqual(values["revenue"], 100000000000.0)
        self.assertEqual(values["net_income"], 25000000000.0)
        self.assertAlmostEqual(values["profit_margin"], .25)
        self.assertAlmostEqual(values["gross_margin"], .46)
        self.assertAlmostEqual(values["current_ratio"], 1.25)
        self.assertEqual(values["debt"], 90000000000.0)
        self.assertEqual(values["free_cash_flow"], 80000000000.0)
        self.assertAlmostEqual(values["revenue_growth"], 100/90 - 1)
        self.assertAlmostEqual(values["earnings_growth"], .25)

    def test_apply_metrics_never_overwrites_observed_yahoo_values(self):
        raw = RawMetrics(ticker="AAPL", quote_type="EQUITY", profit_margin=.20, total_cash=39_000_000_000)
        values = archives.extract_metrics(archives.parse_xbrl_instance(XBRL), "10-Q")
        self.assertTrue(archives.apply_metrics(raw, values))
        self.assertEqual(raw.profit_margin, .20)
        self.assertEqual(raw.total_cash, 39_000_000_000)
        self.assertAlmostEqual(raw.operating_margin, .30)
        self.assertTrue(raw.sec_edgar_enriched)
        self.assertEqual(raw.sec_edgar_transport, "archives_xbrl")
        self.assertGreaterEqual(raw.source_agreement_checks, 1)

    def test_enrich_uses_exact_cik_cache_and_skips_non_equity(self):
        # Patch the module's validated snapshot reader so no repository data is required.
        original = archives._read_ticker_snapshot
        archives._read_ticker_snapshot = lambda path: ({"AAPL": 320193, "SPY": 884394}, {"count": 2})
        try:
            q = [(2026, 3)]
            master_url = archives.master_index_url(2026, 3)
            filing = archives.parse_master_index(MASTER)[0]
            index_url = archives.filing_index_url(filing)
            instance_url = archives.find_xbrl_instance_url(INDEX_HTML, index_url)
            client = FakeClient({master_url: MASTER, index_url: INDEX_HTML, instance_url: XBRL})
            raw = [
                RawMetrics(ticker="AAPL", quote_type="EQUITY"),
                RawMetrics(ticker="SPY", quote_type="ETF"),
                RawMetrics(ticker="MSFT.DE", quote_type="EQUITY"),
            ]
            with tempfile.TemporaryDirectory() as tmp:
                cache_path = Path(tmp) / "cache.json"
                result = archives.enrich(raw, priority={"AAPL"}, client=client, cache_path=cache_path, quarters=q)
                self.assertTrue(result[0].sec_edgar_enriched)
                self.assertFalse(getattr(result[1], "sec_edgar_enriched", False))
                payload = json.loads(cache_path.read_text())
                self.assertIn("0000320193-26-000079", payload["entries"])
                first_requests = client.requests

                # Same immutable accession should use cache; only master.idx is fetched.
                client2 = FakeClient({master_url: MASTER})
                raw2 = [RawMetrics(ticker="AAPL", quote_type="EQUITY")]
                archives.enrich(raw2, priority={"AAPL"}, client=client2, cache_path=cache_path, quarters=q)
                self.assertTrue(raw2[0].sec_edgar_enriched)
                self.assertEqual(client2.requests, 1)
                self.assertGreater(first_requests, client2.requests)
        finally:
            archives._read_ticker_snapshot = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
