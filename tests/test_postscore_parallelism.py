from pathlib import Path


RUN = Path(__file__).resolve().parents[1] / "scripts" / "run.py"


def test_independent_postscore_enrichments_run_in_parallel():
    source = RUN.read_text(encoding="utf-8")
    assert 'ThreadPoolExecutor(max_workers=3, thread_name_prefix="postscore")' in source
    assert "pool.submit(fetch_analyst_many" in source
    assert "pool.submit(annotate_insiders, us_tickers)" in source
    assert "pool.submit(fetch_congress_for_universe, us_tickers)" in source


def test_price_history_fetch_remains_after_postscore_parallel_block():
    source = RUN.read_text(encoding="utf-8")
    parallel = source.index('ThreadPoolExecutor(max_workers=3, thread_name_prefix="postscore")')
    price_history = source.index("insider_price_map = fetch_insider_prices(price_history_tickers)")
    assert parallel < price_history
