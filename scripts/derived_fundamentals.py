"""Conservative derived fundamentals for Vestra.

This module never invents missing statement inputs and never overwrites an
observed provider value. It only derives ratios whose numerator/denominator are
already present on RawMetrics. Derived metrics are tagged separately from data
sources so dossier provenance stays explicit.
"""
from __future__ import annotations

import logging

log = logging.getLogger("derived_fundamentals")


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _sum_recent(series, count=4):
    if not isinstance(series, list) or len(series) < count:
        return None
    vals = []
    for row in series[:count]:
        if not isinstance(row, dict):
            return None
        value = _num(row.get("value"))
        if value is None:
            return None
        vals.append(value)
    return sum(vals)


def _tag(metric, model):
    tags = getattr(model, "derived_metrics", None)
    if not isinstance(tags, list):
        tags = []
        setattr(model, "derived_metrics", tags)
    if metric not in tags:
        tags.append(metric)


def enrich(raw):
    """Fill only high-confidence ratio gaps from already observed inputs."""
    derived_rows = 0
    derived_values = 0

    for model in raw or []:
        if getattr(model, "quote_type", None) in ("ETF", "CRYPTO"):
            continue
        changed = False

        # Trailing P/E from market cap / four-quarter net income. Requiring all
        # four quarters avoids mixing annual and partial-period observations.
        if getattr(model, "trailing_pe", None) is None:
            market_cap = _num(getattr(model, "market_cap", None))
            ttm_net_income = _sum_recent(getattr(model, "quarterly_net_income", None), 4)
            if market_cap is not None and market_cap > 0 and ttm_net_income is not None and ttm_net_income > 0:
                pe = market_cap / ttm_net_income
                # Reject pathological values that are not useful as a valuation
                # multiple and would distort cross-sectional percentiles.
                if 0 < pe <= 500:
                    model.trailing_pe = pe
                    _tag("trailing_pe", model)
                    changed = True
                    derived_values += 1

        # EV/EBITDA from complete capital-structure inputs. Debt/cash must both
        # be observed; treating a missing component as zero is explicitly banned.
        if getattr(model, "enterprise_to_ebitda", None) is None:
            market_cap = _num(getattr(model, "market_cap", None))
            debt = _num(getattr(model, "total_debt", None))
            cash = _num(getattr(model, "total_cash", None))
            ebitda = _num(getattr(model, "ebitda", None))
            if all(v is not None for v in (market_cap, debt, cash, ebitda)) and market_cap > 0 and ebitda > 0:
                enterprise_value = market_cap + debt - cash
                multiple = enterprise_value / ebitda if enterprise_value > 0 else None
                if multiple is not None and 0 < multiple <= 100:
                    model.enterprise_to_ebitda = multiple
                    _tag("enterprise_to_ebitda", model)
                    changed = True
                    derived_values += 1

        if changed:
            derived_rows += 1

    log.info("Derived fundamentals: %d values across %d rows", derived_values, derived_rows)
    return raw


__all__ = ["enrich"]
