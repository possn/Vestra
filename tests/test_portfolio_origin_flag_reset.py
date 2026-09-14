from pathlib import Path


SOURCE = Path('portfolio-sheet-navigation.js').read_text(encoding='utf-8')


def _open_company_body():
    start = SOURCE.index('async function openCompany')
    end = SOURCE.index('\n  function cleanupPortfolioChrome', start)
    return SOURCE[start:end]


def test_portfolio_origin_is_resolved_before_empty_ticker_guard():
    body = _open_company_body()
    assert body.index('const origin=') < body.index('if(!tk)')


def test_empty_portfolio_ticker_releases_pending_origin_flag():
    body = _open_company_body()
    guard = body[body.index('if(!tk)'):body.index('const request=', body.index('if(!tk)'))]
    assert "if(origin==='portfolio') openingFromPortfolio=false;" in guard


def test_missing_market_api_releases_pending_origin_flag():
    body = _open_company_body()
    start = body.index('if(!api?.openTicker)')
    end = body.index('// Establish the navigation state', start)
    guard = body[start:end]
    assert "if(origin==='portfolio') openingFromPortfolio=false;" in guard
    assert 'return false;' in guard


def test_successful_portfolio_navigation_still_clears_flag_via_origin_prepare():
    assert "sh.dataset.tool='ticker-from-portfolio';" in SOURCE
    assert "sh.dataset.returnView='portfolio';" in SOURCE
    assert 'openingFromPortfolio=false;' in SOURCE
