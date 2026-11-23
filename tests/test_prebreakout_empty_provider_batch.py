"""Provider-wide NaN responses are not negative investment signals.

Uses minimal Yahoo-shaped frames: historical architecture CI has no pandas.
"""
import importlib.util
from pathlib import Path
from unittest.mock import Mock
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prebreakout_empty_batch", ROOT / "scripts" / "refresh_prebreakout_scanner.py"
)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class Frame:
    def __init__(self, closes):
        self.values = list(closes)
        self.empty = not bool(closes)
        self.columns = type("Columns", (), {"nlevels": 1})()

    def __getitem__(self, key):
        if key == "Close":
            return self.values
        raise KeyError(key)


class MultiColumns:
    nlevels = 2

    def __init__(self, names):
        self.names = names

    def get_level_values(self, level):
        return self.names if level == 0 else ["Close"] * len(self.names)


class MultiFrame:
    empty = False

    def __init__(self, data):
        self.data = data
        self.columns = MultiColumns(list(data))

    def xs(self, ticker, axis, level):
        assert axis == 1 and level == 0
        return Frame(self.data[ticker])


def test_all_nan_return_is_retried_then_marked_unobserved():
    provider = Mock()
    provider.download.return_value = Frame([float("nan"), float("nan")])
    try:
        scanner.fetch_ohlcv_batch(provider, ["AAA"])
    except RuntimeError as exc:
        assert "provider_batch_without_usable_close" in str(exc)
    else:
        raise AssertionError("a provider-wide all-NaN response must fail closed")
    assert provider.download.call_count == 2


def test_empty_return_is_retried_and_valid_second_attempt_accepted():
    provider = Mock()
    valid = Frame([10.0, 11.0])
    provider.download.side_effect = [Frame([]), valid]
    result, retries = scanner.fetch_ohlcv_batch(provider, ["AAA"])
    assert result is valid
    assert retries == 1
    assert provider.download.call_count == 2


def test_partial_nan_history_stays_subject_to_per_ticker_validation():
    provider = Mock()
    partial = Frame([10.0, float("nan"), 11.0])
    provider.download.return_value = partial
    result, retries = scanner.fetch_ohlcv_batch(provider, ["AAA"])
    assert result is partial
    assert retries == 0
    assert provider.download.call_count == 1


def test_multiticker_one_valid_other_nan_not_entire_batch_failure():
    mixed = MultiFrame({"AAA": [float("nan")], "BBB": [13.0]})
    assert not scanner.batch_has_no_usable_close(mixed, ["AAA", "BBB"])
    assert scanner.batch_has_no_usable_close(mixed, ["AAA"])
