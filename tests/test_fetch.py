"""Tests for scraper/fetch.py (no network). Run: python -m pytest -q tests/test_fetch.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from scraper.fetch import BudgetExceeded, PoliteSession, looks_blocked


def test_block_page_detection():
    assert looks_blocked("<html>Please verify you are human</html>")
    assert not looks_blocked("x" * 30000 + "verify you are human")   # big pages are real pages


def test_request_budget_is_enforced():
    s = PoliteSession(max_requests=0, sleep=lambda *_: None)
    s._robots = type("R", (), {"can_fetch": lambda *a: True})()
    try:
        s.get(config.BASE_URL + "/mobile-phones")
        assert False, "should have hit the budget"
    except BudgetExceeded:
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)