"""Load every raw daily file into SQLite. Safe to re-run: runs already
loaded (matched by run_label) are skipped.

    python -m db.load             # add any new raw files
    python -m db.load --rebuild   # delete the database and rebuild it from every raw file
"""
import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

import pandas as pd

import scraper.config as config
from cleaning.clean import clean_run, load_raw_file

log = logging.getLogger("load")


def _none(v):
    """pandas NaN/NA -> None (NULL); numpy scalars -> plain Python (sqlite3 rejects numpy.int64)."""
    if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)):
        return None
    if hasattr(v, "item"):          # numpy.int64 / float64 / bool_
        v = v.item()
    if isinstance(v, float) and v.is_integer():
        return int(v)               # 128.0 -> 128 for INTEGER columns
    return v


ID_COLUMN = {"categories": "category_id", "locations": "location_id"}


def get_or_create(cur, table, key_cols, values):
    where = " AND ".join(f"{c} IS ?" for c in key_cols)
    row = cur.execute(f"SELECT {ID_COLUMN[table]} FROM {table} WHERE {where}",
                      [values[c] for c in key_cols]).fetchone()
    if row:
        return row[0]
    cols = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(values.values()))
    return cur.lastrowid


def load_run(conn, raw_path):
    raw = load_raw_file(raw_path)
    meta, products, obs = clean_run(raw)
    cur = conn.cursor()
    label = Path(raw_path).stem.replace(config.RAW_PREFIX, "")
    if cur.execute("SELECT 1 FROM scrape_runs WHERE run_label=?", (label,)).fetchone():
        log.info("Run %s already loaded; skipping", label)
        return False

    cur.execute(
        "INSERT INTO scrape_runs (run_label, started_at, finished_at, requests_made,"
        " items_scraped, blocked, currency, fx_rate_to_usd, notes) VALUES (?,?,?,?,?,?,?,?,?)",
        (label, meta.get("started_at"), meta.get("finished_at"),
         meta.get("requests_made"), meta.get("items_scraped"),
         int(bool(meta.get("blocked"))), meta.get("currency", config.CURRENCY),
         config.USD_PER_LOCAL, json.dumps(meta.get("notes", []))))
    run_id = cur.lastrowid
    cohort_ids = set()
    cohort_file = config.COHORT_FILE
    if cohort_file.exists():
        cohort_ids = {c["listing_id"] for c in json.loads(cohort_file.read_text())}
    else:
        log.warning("No cohort file at %s: products.in_cohort will be 0 for every row", cohort_file)
    posting_dates = products.attrs.get("cohort_posting_dates", {})
    for cat_name, total in (meta.get("category_totals") or {}).items():
        cat_id = get_or_create(cur, "categories", ["name"], {"name": cat_name})
        cur.execute("INSERT OR REPLACE INTO category_daily_totals VALUES (?,?,?)",
                    (run_id, cat_id, total))

    first_seen = obs.groupby("source_listing_id")["scraped_at"].min().to_dict()
    for p in products.to_dict("records"):
        cat_id = get_or_create(cur, "categories", ["name"], {"name": p["category"]})
        loc_id = get_or_create(cur, "locations", ["region", "area"],
                               {"region": _none(p["region"]), "area": _none(p["area"])})
        seen = first_seen.get(p["source_listing_id"])
        cur.execute(
            """INSERT INTO products (source_listing_id, title, title_source, badge, brand,
                   model, storage_gb, color, category_id, condition, location_id,
                   posting_date, url, in_cohort, first_seen, last_seen)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source_listing_id) DO UPDATE SET
                   last_seen = MAX(COALESCE(products.last_seen, ''), excluded.last_seen),
                   in_cohort = MAX(products.in_cohort, excluded.in_cohort),
                   posting_date = COALESCE(products.posting_date, excluded.posting_date)""",
            (p["source_listing_id"], _none(p["title"]), _none(p["title_source"]),
             _none(p["badge"]), _none(p["brand"]),
             _none(p["model"]), _none(p["storage_gb"]), _none(p["color"]), cat_id,
             _none(p["condition"]), loc_id, _none(p["posting_date"]), _none(p["url"]),
             int(p["source_listing_id"] in cohort_ids), seen, seen))

    for lid, d in posting_dates.items():
        cur.execute("UPDATE products SET posting_date=COALESCE(posting_date, ?) "
                    "WHERE source_listing_id=?", (d, lid))

    missing = 0
    for o in obs.to_dict("records"):
        row = cur.execute("SELECT product_id FROM products WHERE source_listing_id=?",
                          (o["source_listing_id"],)).fetchone()
        if not row:
            missing += 1
            continue
        cur.execute(
            """INSERT OR IGNORE INTO observations (product_id, run_id, scraped_at,
                   price_local, old_price_local, discount_pct, page_position, is_promoted,
                   status, source, price_flag)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (row[0], run_id, o["scraped_at"], _none(o["price_local"]),
             _none(o["old_price_local"]), _none(o["discount_pct"]),
             _none(o["page_position"]), _none(o["is_promoted"]), o["status"],
             o["source"], _none(o["price_flag"])))
        if o["status"] == "active":
            cur.execute("UPDATE products SET last_seen=MAX(COALESCE(last_seen,''), ?) "
                        "WHERE product_id=?", (o["scraped_at"], row[0]))
    if missing:
        log.warning("%d observations had no matching product (skipped)", missing)
    conn.commit()
    log.info("Loaded %s: %d products, %d observations", label, len(products), len(obs))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rebuild", action="store_true",
                    help="delete the existing database first and reload every raw file")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config.DB_PATH.parent.mkdir(exist_ok=True)
    if args.rebuild and config.DB_PATH.exists():
        config.DB_PATH.unlink()
        log.info("Removed %s", config.DB_PATH)
    conn = sqlite3.connect(config.DB_PATH)
    conn.executescript((Path(__file__).parent / "schema.sql").read_text())
    files = sorted(config.RAW_DIR.glob(f"{config.RAW_PREFIX}*.json"))
    if not files:
        log.error("No raw files found in %s", config.RAW_DIR)
        return 1
    status = 0
    for f in files:
        try:
            load_run(conn, f)
        except Exception:
            conn.rollback()           # never leave a half-loaded run behind
            log.exception("Failed to load %s; rolled back", f.name)
            status = 1
    conn.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
