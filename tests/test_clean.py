"""Tests for cleaning/clean.py and the database loader (no network).

Run from the project root:  python -m pytest -q
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import scraper.config as config
from cleaning import clean as C
from db import load


# ------------------------------------------------------------ unit tests
def test_missing_values_do_not_crash():
    nan = float("nan")
    assert C.split_location(nan) == (None, None)
    assert C.parse_price(nan) is None
    assert C.normalise_condition(nan) is None
    assert C.is_junk_title(nan)


def test_price_and_location_and_condition():
    assert C.parse_price("UGX 1,250,000") == 1250000
    assert C.split_location("Kampala, Central Division") == ("Kampala", "Central Division")
    assert C.normalise_condition("Brand new") == "new"       # mixed case exists in the data
    assert C.normalise_condition("Refurbished") == "refurbished"


@pytest.mark.parametrize("badge", ["5", "-16%", "Replica", "Popular"])
def test_badge_titles_are_recovered_from_url(badge):
    url = "https://jiji.ug/x/mobile-phones/new-samsung-galaxy-s10-128-gb-white-q9Lwf7V0MgKrnDd562lBszEm.html"
    title, source, kept = C.clean_title(badge, url)
    assert title == "New Samsung Galaxy S10 128 GB White"
    assert source == "url_slug" and kept == badge


def test_title_recovery_works_for_short_listing_ids():
    url = "https://jiji.ug/x/y/new-foo-bar-5-gb-abcdefghijklmnopqrstuv.html"   # 22-char id
    assert C.title_from_url(url) == "New Foo Bar 5 GB"


def test_attribute_extraction():
    a = C.extract_attributes("New Samsung Galaxy A57 256 GB Purple")
    assert (a["brand"], a["storage_gb"], a["color"]) == ("Samsung", 256, "Purple")
    assert C.extract_attributes("Galaxy Watch 8 44mm")["brand"] == "Samsung"
    assert C.extract_attributes("New Tablet 128 GB")["brand"] is None


# ------------------------------------------------------- end-to-end load
def _raw(tmp_path, with_missing_location=True):
    card = lambda i, **kw: {   # noqa: E731
        "listing_id": f"id{i:022d}", "url": f"https://jiji.ug/c/tablets/new-tab-{i}-id{i:022d}.html",
        "category": "tablets", "area_slug": "central-division", "title": f"New Tab {i} 64 GB",
        "price_raw": f"UGX {i}00,000", "condition_raw": "Brand New",
        "location_raw": "Kampala, Central Division", "rank_in_category": i,
        "scraped_at": "2026-10-14T10:00:00+00:00", **kw}
    snap = [card(1), card(2, location_raw=None) if with_missing_location else card(2),
            card(3, title="Replica")]
    raw = {"meta": {"run_id": "t", "started_at": "x", "finished_at": "y", "requests_made": 1,
                    "items_scraped": 3, "blocked": False, "category_totals": {"tablets": 99}},
           "snapshot": snap, "cohort_checks": []}
    f = tmp_path / "jiji_ug_2026-01-01.json"
    f.write_text(json.dumps(raw))
    return f


def test_loader_handles_missing_location_and_badge_title(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.executescript((Path(load.__file__).parent / "schema.sql").read_text())
    assert load.load_run(conn, _raw(tmp_path)) is True
    assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 3
    # missing location falls back to the URL area slug instead of crashing / NULL
    assert conn.execute("SELECT COUNT(*) FROM products p JOIN locations l USING(location_id) "
                        "WHERE l.region IS NULL").fetchone()[0] == 0
    assert conn.execute("SELECT title_source, badge FROM products WHERE title LIKE 'New Tab 3%' "
                        "OR badge='Replica'").fetchone() == ("url_slug", "Replica")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_loader_is_idempotent(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.executescript((Path(load.__file__).parent / "schema.sql").read_text())
    f = _raw(tmp_path)
    assert load.load_run(conn, f) is True
    assert load.load_run(conn, f) is False          # second load is skipped
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 3


def test_db_path_is_in_project_db_folder():
    assert config.DB_PATH.parent.name == "db"
    assert config.DB_PATH.parent.parent == config.PROJECT_ROOT
