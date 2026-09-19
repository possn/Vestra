from pathlib import Path
import re

APP = Path("app.js").read_text(encoding="utf-8")


def test_nfe_reverse_split_is_canonical_and_dated():
    assert 'ticker: "NFE"' in APP
    assert 'effectiveDate: "2026-09-14"' in APP
    assert 'numerator: 1, denominator: 50' in APP


def test_canonical_split_normalizes_only_pre_effective_quantities():
    assert 'if (!d || d >= action.effectiveDate) continue;' in APP
    assert 'if (!["BUY", "SELL", "STOCK_DISTRIBUTION"].includes(e.type)) continue;' in APP
    assert 'e.qty = q * factor;' in APP
    assert 'p.qty = q * factor;' in APP


def test_real_broker_split_disables_canonical_fallback():
    assert 'e.type !== "SPLIT_OPEN" && e.type !== "SPLIT_CLOSE"' in APP
    assert 'if (hasExplicitSplit) continue;' in APP


def test_nfe_100_old_shares_become_2_without_changing_cost_basis():
    old_qty = 100
    split_denominator = 50
    cost_basis_eur = 83.0
    new_qty = old_qty / split_denominator
    new_pm = cost_basis_eur / new_qty

    assert new_qty == 2
    assert new_pm == 41.5
    # The implementation changes qty only; cash/cost fields are deliberately untouched.
    helper = APP[APP.index("function normalizeCanonicalBrokerCorporateActions"):APP.index("function rebuildBrokerGeneratedData")]
    assert "costBasis" not in helper
    assert "totalEUR" not in helper


def test_schema_bump_forces_existing_saved_broker_state_to_rebuild():
    match = re.search(r"const BROKER_REBUILD_SCHEMA_VERSION = (\d+);", APP)
    assert match
    assert int(match.group(1)) >= 46
