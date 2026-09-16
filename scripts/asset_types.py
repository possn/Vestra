"""Canonical market asset-type contract.

Only explicit upstream types are classified here, except for the provider's
canonical preferred-share ticker notation (for example ``DUK-PA``), which is an
instrument-identity signal rather than a company-name guess. A missing/unknown
quote type is never promoted to EQUITY by this module; callers may keep it in an
unresolved lane until stronger identity evidence is available.
"""
from __future__ import annotations

import re

NON_EQUITY_TYPES = frozenset({"ETF", "CRYPTO", "MUTUALFUND", "FUND", "PREFERRED"})
FUND_TYPES = frozenset({"MUTUALFUND", "FUND"})
PREFERRED_TICKER_RE = re.compile(r"^[A-Z0-9.]+-P[A-Z0-9]+$")


def normalized_quote_type(value) -> str:
    return str(value or "").strip().upper()


def is_preferred_ticker(ticker) -> bool:
    """Return True for canonical provider symbols representing preferred issues.

    Yahoo-style preferred listings use a ``-P<series>`` suffix (for example
    DUK-PA, JPM-PD or USB-PP). This deliberately does not match ordinary share
    classes such as BRK-B.
    """
    return bool(PREFERRED_TICKER_RE.fullmatch(str(ticker or "").strip().upper()))


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
