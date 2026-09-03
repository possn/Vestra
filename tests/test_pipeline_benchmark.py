from scripts.pipeline_benchmark import summarise


def test_summarise_counts_rate_limits_and_broad_fetch():
    log = """2026-09-03 08:00:00,000 INFO fundamentals: Fetching 27 tickers with 1 workers
2026-09-03 08:00:05,000 INFO fundamentals: fetched 27/27
2026-09-03 08:01:00,000 INFO fundamentals: Fetching 1550 tickers with 3 workers
2026-09-03 08:01:10,000 WARNING fundamentals: Yahoo rate-limit detected — pausing fetch workers for 10s (strike 1)
2026-09-03 08:01:10,020 WARNING fundamentals: Yahoo rate-limit detected — pausing fetch workers for 20s (strike 2)
2026-09-03 08:11:00,000 INFO fundamentals: fetched 1550/1550
"""
    out = summarise(log)
    assert out["rate_limit_log_events"] == 2
    assert out["max_rate_limit_strike"] == 2
    assert out["broad_fetch"] == {"tickers": 1550, "workers": 3, "duration_seconds": 600.0}


def test_incomplete_fetch_is_not_selected_as_completed_broad_fetch():
    log = """2026-09-03 08:00:00,000 INFO fundamentals: Fetching 470 tickers with 3 workers
2026-09-03 08:02:00,000 INFO fundamentals: fetched 470/470
2026-09-03 08:03:00,000 INFO fundamentals: Fetching 1550 tickers with 3 workers
2026-09-03 08:04:00,000 INFO fundamentals: fetched 100/1550
"""
    out = summarise(log)
    assert out["broad_fetch"] == {"tickers": 470, "workers": 3, "duration_seconds": 120.0}
    assert out["fetches"][-1]["duration_seconds"] is None


def test_missing_markers_stay_null_instead_of_zero():
    out = summarise("2026-09-03 08:00:00,000 INFO run: hello\n")
    assert out["broad_fetch"] is None
    assert out["analyst_duration_seconds"] is None
    assert out["insider_duration_seconds"] is None
    assert out["rate_limit_log_events"] == 0
