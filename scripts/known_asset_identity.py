"""Small exact-match identity overrides for broker symbols with unstable quote types.

This table is intentionally tiny. Entries require deterministic external evidence
that the exact broker/exchange symbol represents the stated asset type. It is not
a substitute for live discovery and never performs fuzzy/name-based matching.
Only identity metadata belongs here; live TER, AUM, holdings and prices remain
retrieved from market/fund sources.
"""
from __future__ import annotations

KNOWN_ASSET_IDENTITY = {
    "SPY4.DE": {
        "quote_type": "ETF",
        "name": "State Street SPDR S&P 400 U.S. Mid Cap UCITS ETF (Acc)",
        "isin": "IE00B4YBJ215",
        "identity_source": "State Street official listing",
    },
    "SPYD.DE": {
        "quote_type": "ETF",
        "name": "State Street SPDR S&P U.S. Dividend Aristocrats UCITS ETF (Dist)",
        "isin": "IE00B6YX5D40",
        "identity_source": "State Street official fund + XTB broker symbol",
    },
    "SPYL.DE": {
        "quote_type": "ETF",
        "name": "State Street SPDR S&P 500 UCITS ETF (Acc)",
        "isin": "IE000XZSV718",
        "identity_source": "State Street official listing",
    },
    "VGWD.DE": {
        "quote_type": "ETF",
        "name": "Vanguard FTSE All-World High Dividend Yield UCITS ETF (USD) Distributing",
        "isin": "IE00B8GKDB10",
        "identity_source": "Vanguard official listing",
    },
}


def exact_identity_override(ticker):
    key = str(ticker or "").strip().upper()
    row = KNOWN_ASSET_IDENTITY.get(key)
    return dict(row) if row else None


__all__ = ["KNOWN_ASSET_IDENTITY", "exact_identity_override"]
