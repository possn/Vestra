from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_market_pipeline import install_gap_retrieval_observability


def test_gap_retrieval_summaries_are_visible_at_info_level():
    names = ("gap_retrieval", "quarterly_gap")
    loggers = [logging.getLogger(name) for name in names]
    previous = [logger.level for logger in loggers]
    try:
        for logger in loggers:
            logger.setLevel(logging.WARNING)

        installed = install_gap_retrieval_observability()

        assert installed == names
        assert all(logger.level == logging.INFO for logger in loggers)
    finally:
        for logger, level in zip(loggers, previous):
            logger.setLevel(level)


if __name__ == "__main__":
    test_gap_retrieval_summaries_are_visible_at_info_level()
