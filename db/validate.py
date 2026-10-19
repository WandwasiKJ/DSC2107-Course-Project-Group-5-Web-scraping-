"""Integrity + data-quality checks for the loaded database.

    python -m db.validate

Exit code 0 = every hard check passed; 1 = at least one FAILED. WARN lines are
data limitations worth knowing about, not errors.
"""
import sqlite3
import sys

import scraper.config as config

HARD_CHECKS = [
    # (name, SQL returning the number of BAD rows -- must be 0)
    ("foreign keys valid",
     "SELECT COUNT(*) FROM pragma_foreign_key_check"),
    ("every product has a category",
     "SELECT COUNT(*) FROM products WHERE category_id IS NULL"),
    ("every product has a title",
     "SELECT COUNT(*) FROM products WHERE title IS NULL OR TRIM(title) = ''"),
    ("no badge text left in titles (5, -10%, Replica...)",
     "SELECT COUNT(*) FROM products WHERE title GLOB '[0-9]' OR title GLOB '-[0-9]*%' "
     "OR LOWER(title) IN ('replica','popular','vip','top','hot','featured','promoted')"),
    ("no duplicate listing per run",
     "SELECT COUNT(*) FROM (SELECT product_id, run_id FROM observations "
     "GROUP BY 1,2 HAVING COUNT(*) > 1)"),
    ("every run has observations",
     "SELECT COUNT(*) FROM scrape_runs r WHERE NOT EXISTS "
     "(SELECT 1 FROM observations o WHERE o.run_id = r.run_id)"),
    ("every product has at least one observation",
     "SELECT COUNT(*) FROM products p WHERE NOT EXISTS "
     "(SELECT 1 FROM observations o WHERE o.product_id = p.product_id)"),
    ("prices are positive integers",
     "SELECT COUNT(*) FROM observations WHERE price_local IS NOT NULL "
     "AND (price_local <= 0 OR typeof(price_local) <> 'integer')"),
    ("condition uses the controlled vocabulary",
     "SELECT COUNT(*) FROM products WHERE condition IS NOT NULL "
     "AND condition NOT IN ('new','used','refurbished')"),
    ("first_seen <= last_seen",
     "SELECT COUNT(*) FROM products WHERE first_seen > last_seen"),
    ("observation counts match scrape_runs.items_scraped",
     "SELECT COUNT(*) FROM scrape_runs r WHERE r.items_scraped <> "
     "(SELECT COUNT(*) FROM observations o WHERE o.run_id = r.run_id AND o.source='snapshot')"),
]


def main():
    if not config.DB_PATH.exists():
        print(f"FAIL  no database at {config.DB_PATH} -- run: python -m db.load")
        return 1
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    failed = 0

    for name, sql in HARD_CHECKS:
        bad = conn.execute(sql).fetchone()[0]
        print(f"{'ok  ' if bad == 0 else 'FAIL'}  {name}" + ("" if bad == 0 else f"  ({bad} bad rows)"))
        failed += bad != 0

    q = lambda sql: conn.execute(sql).fetchone()[0]          # noqa: E731
    n_prod, n_obs = q("SELECT COUNT(*) FROM products"), q("SELECT COUNT(*) FROM observations")
    print(f"\n{q('SELECT COUNT(*) FROM scrape_runs')} runs, {n_prod} products, {n_obs} observations")

    # ---- soft warnings: known limitations of this dataset -------------------------
    warns = []
    if q("SELECT COUNT(*) FROM products WHERE in_cohort = 1") == 0:
        warns.append("no tracking cohort (scraper/data/cohort.json missing): in_cohort is 0 "
                     "everywhere and there are no 'gone' observations")
    if q("SELECT COUNT(*) FROM products WHERE posting_date IS NULL") == n_prod:
        warns.append("posting_date is NULL for every product (cards carry no posted time and "
                     "no cohort detail pages were fetched)")
    pct = lambda sql: round(100 * q(sql) / max(n_prod, 1), 1)  # noqa: E731
    warns.append(f"brand missing for {pct('SELECT COUNT(*) FROM products WHERE brand IS NULL')}% "
                 "of products (many are genuinely unbranded, e.g. 'New Tablet 128 GB')")
    warns.append(f"{q('SELECT COUNT(*) FROM products WHERE title_source = ' + chr(39) + 'url_slug' + chr(39))} "
                 "titles were recovered from the URL slug because the card showed a badge")
    short = conn.execute(
        "SELECT run_label, items_scraped FROM scrape_runs "
        "WHERE items_scraped < ?", (config.MIN_ITEMS_FOR_SUCCESS + 100,)).fetchall()
    for label, n in short:
        warns.append(f"run {label} collected only {n} listings (target 600)")
    for w in warns:
        print(f"WARN  {w}")

    conn.close()
    print("\nRESULT:", "FAILED" if failed else "all hard checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
