"""Daily run entry point.

Usage (from the project root):
    python -m scraper.run --sample          # Day 3: ~120-row sample CSV
    python -m scraper.run --init-cohort     # Day 4: first run, also pick the cohort
    python -m scraper.run                   # Days 5-10: snapshot + cohort re-check

A run does three things, always inside the request budget:
  1. SNAPSHOT: first N listings per category (price, condition, location, rank)
  2. COHORT:   re-visit the fixed tracking set to catch price changes / removals
  3. Save everything, unmodified, to data/raw/jiji_ug_YYYY-MM-DD.json

If the site blocks us (403/429/CAPTCHA) the run STOPS, saves what it has,
and records the block in the metadata. Nothing is bypassed.
"""
import argparse
import csv
import json
import logging
import random
import sys
sys.path.append('C:/Users/jonnathan/Desktop/YEAR 2/Data Mining and Wrangling/webscraping/jiji_ug_scraper_starter_kit/jiji-ug-scraper/scraper')
from datetime import date, datetime, timezone


import scraper.config as config
from scraper.fetch import (BlockedError, BudgetExceeded, PoliteSession,
                           RobotsDisallowed)
from scraper.parse import (match_listing_url, parse_detail, parse_listing_cards,
                           parse_total_results)

log = logging.getLogger("run")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def setup_logging(run_label):
    config.LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(config.LOG_DIR / f"scraper_{run_label}.log"),
                  logging.StreamHandler()])


def scrape_category(session, name, path, target, run_label, sink, totals=None):
    """Paginate one category until `target` listings or no new listings.

    Results are appended to `sink` as they arrive, so if the run is blocked
    or hits the budget mid-category the rows already collected are kept.
    """
    seen, count = set(), 0
    totals = totals if totals is not None else {}
    for page in range(1, config.MAX_PAGES_PER_CATEGORY + 1):
        params = dict(config.EXTRA_PARAMS)
        if page > 1:
            params[config.PAGE_PARAM] = page
        resp = session.get(config.BASE_URL + path, params=params or None)
        if resp is None:
            log.error("%s page %d failed after retries; stopping category", name, page)
            break
        if resp.status_code != 200:
            log.error("%s page %d returned HTTP %d", name, page, resp.status_code)
            break
        if page == 1:
            totals[name] = parse_total_results(resp.text)   # e.g. 15154 ads in category
            log.info("%s: site reports %s ads in total", name, totals[name])
        new = [c for c in parse_listing_cards(resp.text)
               if c["listing_id"] not in seen]
        # The HTML lists cards column by column, so DOM order is NOT rank order.
        # Sort by indexPosition to recover the on-screen order.
        new.sort(key=lambda c: (c["index_position"] is None, c["index_position"] or 0))
        if len(new) != config.CARDS_PER_PAGE_EXPECTED:
            log.info("%s page %d: %d cards (expected %d)", name, page, len(new),
                     config.CARDS_PER_PAGE_EXPECTED)
        if not new:
            log.info("%s page %d: no new listings, stopping", name, page)
            break
        scraped_at = now_iso()
        for card in new[:target - count]:
            seen.add(card["listing_id"])
            count += 1
            card.update(category=name, page=page, rank_in_category=count,
                        scraped_at=scraped_at, run_id=run_label)
            sink.append(card)
        log.info("%s page %d: +%d (category total %d)", name, page, len(new), count)
        if count >= target:
            break


def check_listing(session, record, run_label):
    """Re-visit one cohort listing; report status, price and posting date."""
    base = {"listing_id": record["listing_id"], "url": record["url"],
            "category": record["category"], "run_id": run_label,
            "scraped_at": now_iso()}
    resp = session.get(record["url"])
    if resp is None:
        return {**base, "status": "error"}
    if resp.status_code in (404, 410):
        return {**base, "status": "gone"}
    if resp.status_code != 200:
        return {**base, "status": f"http_{resp.status_code}"}
    m = match_listing_url(resp.url.replace(config.BASE_URL, ""))
    if not m or m.group("id") != record["listing_id"]:
        return {**base, "status": "gone"}     # redirected away = removed
    return {**base, "status": "active", **parse_detail(resp.text)}


def pick_cohort(snapshot, size):
    """Random, category-balanced cohort (seeded so it is reproducible)."""
    rng = random.Random(42)
    by_cat = {}
    for rec in snapshot:
        by_cat.setdefault(rec["category"], []).append(rec)
    per_cat = max(1, size // max(1, len(by_cat)))
    cohort = []
    for cat, recs in by_cat.items():
        chosen = rng.sample(recs, min(per_cat, len(recs)))
        cohort += [{"listing_id": r["listing_id"], "url": r["url"],
                    "category": cat} for r in chosen]
    return cohort


def unique_raw_path(run_label):
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RAW_DIR / f"{config.RAW_PREFIX}{run_label}.json"
    n = 2
    while path.exists():          # never overwrite evidence
        path = config.RAW_DIR / f"{config.RAW_PREFIX}{run_label}_run{n}.json"
        n += 1
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", action="store_true",
                    help="small run (40/category) written to data/sample/*.csv")
    ap.add_argument("--init-cohort", action="store_true",
                    help="after the snapshot, choose and save the tracking cohort")
    args = ap.parse_args(argv)

    run_label = date.today().isoformat()
    setup_logging(run_label)
    started = now_iso()
    session = PoliteSession()
    target = 40 if args.sample else config.TARGET_PER_CATEGORY
    snapshot, cohort_checks, notes, blocked = [], [], [], False
    category_totals = {}

    try:
        session.load_robots()
        for name, path in config.CATEGORIES.items():
            try:
                scrape_category(session, name, path, target, run_label, snapshot,
                                category_totals)
            except RobotsDisallowed as exc:
                msg = f"Skipped {name}: disallowed by robots.txt ({exc})"
                log.error(msg)
                notes.append(msg)

        if args.init_cohort and not args.sample:
            cohort = pick_cohort(snapshot, config.COHORT_SIZE)
            config.COHORT_FILE.write_text(json.dumps(cohort, indent=1))
            log.info("Cohort of %d listings saved to %s", len(cohort), config.COHORT_FILE)
        elif config.COHORT_FILE.exists() and not args.sample:
            cohort = json.loads(config.COHORT_FILE.read_text())
            in_snapshot = {r["listing_id"] for r in snapshot}
            todo = [c for c in cohort if c["listing_id"] not in in_snapshot]
            log.info("Re-checking %d cohort listings (%d already in snapshot)",
                     len(todo), len(cohort) - len(todo))
            for rec in todo:
                cohort_checks.append(check_listing(session, rec, run_label))
    except BlockedError as exc:
        blocked = True
        msg = f"BLOCKED: {exc}. Run stopped; no workaround attempted."
        log.error(msg)
        notes.append(msg)
    except BudgetExceeded as exc:
        msg = f"Request budget reached: {exc}"
        log.warning(msg)
        notes.append(msg)
    except Exception:
        log.exception("Unexpected failure; saving partial results")
        notes.append("Unexpected exception; see log")
    finally:
        meta = {"run_id": run_label, "started_at": started,
                "finished_at": now_iso(), "requests_made": session.requests_made,
                "network_errors": session.errors, "items_scraped": len(snapshot),
                "cohort_checked": len(cohort_checks), "blocked": blocked,
                "category_totals": category_totals, "currency": config.CURRENCY,
                "base_url": config.BASE_URL,
                "user_agent": config.USER_AGENT, "notes": notes}
        if args.sample:
            config.SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
            out = config.SAMPLE_DIR / f"jiji_{config.SITE_CODE}_sample.csv"
            if snapshot:
                with open(out, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(snapshot[0].keys()))
                    w.writeheader()
                    w.writerows(snapshot)
            log.info("Sample written to %s (%d rows)", out, len(snapshot))
        else:
            out = unique_raw_path(run_label)
            out.write_text(json.dumps({"meta": meta, "snapshot": snapshot,
                                       "cohort_checks": cohort_checks},
                                      indent=1, ensure_ascii=False), encoding="utf-8")
            log.info("Raw file saved: %s", out)
        log.info("Done: %d items, %d requests, blocked=%s",
                 len(snapshot), session.requests_made, blocked)

    low = len(snapshot) < (100 if args.sample else config.MIN_ITEMS_FOR_SUCCESS)
    return 2 if (blocked or low) else 0   # non-zero exit lets a scheduler alert


if __name__ == "__main__":
    sys.exit(main())

