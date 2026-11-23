"""Regression: provider-wide NaN responses are not genuine negative setups."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prebreakout_empty_batch", ROOT / "scripts" / "refresh_prebreakout_scanner.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


def frame(closes):
    return pd.DataFrame({"Close": closes, "High": closes, "Low": closes, "Volume": [100] * len(closes)})


def test_all_nan_return_is_retried_then_marked_unobserved():
    provider = Mock()
    provider.download.return_value = frame([float("nan"), float("nan")])
    with pytest.raises(RuntimeError, match="provider_batch_without_usable_close"):
        scanner.fetch_ohlcv_batch(provider, ["AAA"])
    assert provider.download.call_count == 2


def test_empty_return_is_retried_and_valid_second_attempt_accepted():
    provider = Mock()
    valid = frame([10.0, 11.0])
    provider.download.side_effect = [pd.DataFrame(), valid]
    result, retries = scanner.fetch_ohlcv_batch(provider, ["AAA"])
    assert result is valid
    assert retries == 1
    assert provider.download.call_count == 2


def test_partial_nan_history_not_silently_repaired_or_rejected_at_batch_level():
    provider = Mock()
    partial = frame([10.0, float("nan"), 11.0])
    provider.download.return_value = partial
    result, retries = scanner.fetch_ohlcv_batch(provider, ["AAA"])
    assert result is partial
    assert retries == 0
    assert provider.download.call_count == 1
    assert scanner.dataframe_bars(result)[1]["close"] is None


def test_multiticker_one_valid_other_nan_not_entire_batch_failure():
    columns = pd.MultiIndex.from_tuples([
        ("AAA", "Close"), ("AAA", "High"), ("AAA", "Low"), ("AAA", "Volume"),
        ("BBB", "Close"), ("BBB", "High"), ("BBB", "Low"), ("BBB", "Volume"),
    ])
    mixed = pd.DataFrame([[float("nan")] * 4 + [13.0, 14.0, 12.0, 100.0]], columns=columns)
    assert not scanner.batch_has_no_usable_close(mixed, ["AAA", "BBB"])
    assert scanner.batch_has_no_usable_close(mixed, ["AAA"])
