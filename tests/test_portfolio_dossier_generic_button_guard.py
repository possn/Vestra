from pathlib import Path


def test_generic_buttons_do_not_fall_through_to_portfolio_dossier_navigation():
    source = Path("portfolio-dossier-routing.js").read_text(encoding="utf-8")

    assert "const VERSION='1.4'" in source
    assert "a,button,input,select,textarea" in source
    assert "if(!row||!c.contains(row)||isControl(e.target,row))return;" in source
    assert "if(!row||isControl(e.target,row))return;" in source

    # The row-level fallback must never depend only on specialized button selectors;
    # a generic action button inside a portfolio suggestion is still a control.
    assert "a,input,select,textarea,[data-market-watch]" not in source
