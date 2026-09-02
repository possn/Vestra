"""Canonical market asset-type contract.

Only explicit upstream types are classified here. A missing/unknown quote type is
never promoted to EQUITY by this module; callers may keep it in an unresolved
lane until stronger identity evidence is available.
"""
from __future__ import annotations

NON_EQUITY_TYPES = frozenset({"ETF", "CRYPTO", "MUTUALFUND", "FUND"})
FUND_TYPES = frozenset({"MUTUALFUND", "FUND"})


def normalized_quote_type(value) -> str:
    return str(value or "").strip().upper()


def is_explicit_non_equity(value) -> bool:
    return normalized_quote_type(value) in NON_EQUITY_TYPES


def is_fund_type(value) -> bool:
    return normalized_quote_type(value) in FUND_TYPES


def is_equity_candidate(value) -> bool:
    """True unless an explicit non-equity type is known.

    Empty/unknown remains a candidate rather than being asserted as EQUITY.
    This preserves fail-closed identity semantics while keeping legacy coverage
    until authoritative identity evidence resolves the row.
    """
    return not is_explicit_non_equity(value)
