"""Reproducible cleaning: raw daily JSON in, tidy DataFrames out.

No manual edits anywhere: re-running this on the raw files must always give
the same result. Raw files are read-only evidence and are never modified.
"""
import json
import re
from datetime import datetime, timedelta

import pandas as pd

import scraper.config as config

CONDITION_MAP = {
    "brand new": "new", "new": "new",
    "used": "used", "local used": "used", "foreign used": "used",
    "refurbished": "refurbished",
}

# canonical brand -> aliases that may appear in titles (lowercase)
BRANDS = {
    "Apple": ["apple", "iphone", "ipad", "airpods"],
    "Samsung": ["samsung"], "Tecno": ["tecno"], "Infinix": ["infinix"],
    "Itel": ["itel"], "Xiaomi": ["xiaomi", "redmi", "poco", "mi"],
    "Oppo": ["oppo"], "Vivo": ["vivo"], "Realme": ["realme"],
    "Nokia": ["nokia"], "Huawei": ["huawei"], "Honor": ["honor"],
    "Google": ["google", "pixel"], "Motorola": ["motorola", "moto"],
    "OnePlus": ["oneplus"], "LG": ["lg"], "Sony": ["sony"],
    "Lenovo": ["lenovo"], "HP": ["hp"], "Dell": ["dell"],
    "Oraimo": ["oraimo"], "Amazon": ["amazon"], "Nothing": ["nothing"],
    "ZTE": ["zte"], "Fitbit": ["fitbit"], "Garmin": ["garmin"],
    "Sharp": ["sharp"], "Kyocera": ["kyocera"], "Fujitsu": ["fujitsu"], "Bebe": ["bebe"],
    "Discover": ["discover"], "AirTab": ["airtab"], "Idino": ["idino"], "Modio": ["modio"],
    "Amazon": ["amazon", "fire"], "Lenovo": ["lenovo"], "Telzeal": ["telzeal"],
}

STORAGE_RE = re.compile(r"(\d+)\s*(GB|TB)\b", re.I)
RELATIVE_RE = re.compile(r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago", re.I)
UNIT_DAYS = {"minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30}


def parse_price(raw):
    """'USh 450,000' -> 450000 ; anything unparseable -> None."""
    if not raw:
        return None
    digits = re.sub(r"[^\d.]", "", str(raw))
    if not digits:
        return None
    try:
        return int(float(digits))
    except ValueError:
        return None


def price_flag(price):
    if price is None:
        return "missing"
    if price < config.VERY_LOW_PRICE_LOCAL:
        return "very_low"
    return None


def normalise_condition(raw):
    return CONDITION_MAP.get((raw or "").strip().lower())


def split_location(raw):
    """'Kampala, Central Division' -> ('Kampala', 'Central Division')."""
    if not raw:
        return None, None
    parts = [p.strip() for p in raw.split(",", 1)]
    region = parts[0].title() if parts[0] else None
    area = parts[1].title() if len(parts) > 1 and parts[1] else None
    return region, area


def extract_attributes(title):
    """Heuristic brand / model / storage / colour from a Jiji title.

    Titles look like 'Apple iPhone 15 Pro Max 256 GB Blue' (colour is often missing). This is a
    heuristic: check a sample by eye and report the match rate.
    """
    if not title:
        return {"brand": None, "model": None, "storage_gb": None, "color": None}
    t = re.sub(r"^new\s+", "", title.strip(), flags=re.I)
    low = t.lower()

    brand, best = None, None
    for canon, aliases in BRANDS.items():
        for alias in aliases:
            m = re.search(rf"\b{re.escape(alias)}\b", low)
            if m and (best is None or m.start() < best):
                brand, best = canon, m.start()

    storage_gb, color, head = None, None, t
    sm = STORAGE_RE.search(t)
    if sm:
        n = int(sm.group(1))
        storage_gb = n * 1024 if sm.group(2).upper() == "TB" else n
        head = t[:sm.start()].strip()
        tail = t[sm.end():].strip()
        color = tail.title() if tail and len(tail.split()) <= 3 else None

    model = head
    if brand and model.lower().startswith(brand.lower() + " "):
        model = model[len(brand) + 1:]
    return {"brand": brand, "model": model or None,
            "storage_gb": storage_gb, "color": color}


def parse_posted(raw, scraped_at_iso):
    """'3 hours ago' -> ISO date, relative to the scrape time (approximate)."""
    if not raw:
        return None
    m = RELATIVE_RE.search(raw)
    if not m:
        return None
    delta = timedelta(days=int(m.group(1)) * UNIT_DAYS[m.group(2).lower()])
    return (datetime.fromisoformat(scraped_at_iso) - delta).date().isoformat()


def clean_run(raw):
    """Turn one raw run dict into (meta, products_df, observations_df)."""
    meta = raw["meta"]
    snap = pd.DataFrame(raw.get("snapshot", []))
    prod_cols = ["source_listing_id", "title", "brand", "model", "storage_gb",
                 "color", "category", "condition", "region", "area",
                 "posting_date", "url"]
    obs_cols = ["source_listing_id", "scraped_at", "price_local", "old_price_local",
                "discount_pct", "page_position", "is_promoted", "status", "source",
                "price_flag"]
    products, observations = [], []

    if not snap.empty:
        sort_col = "rank_in_category" if "rank_in_category" in snap else "index_position"
        snap = snap.sort_values(sort_col, na_position="last")
        snap = snap.drop_duplicates("listing_id", keep="first")   # dedupe in-run
        for r in snap.to_dict("records"):
            price = parse_price(r.get("price_raw"))
            region, area = split_location(r.get("location_raw"))
            attrs = extract_attributes(r.get("title"))
            products.append({
                "source_listing_id": r["listing_id"], "title": r.get("title"),
                **attrs, "category": r.get("category"),
                "condition": normalise_condition(r.get("condition_raw")),
                "region": region, "area": area,
                "posting_date": parse_posted(r.get("posted_raw"), r["scraped_at"]),
                "url": r.get("url")})
            observations.append({
                "source_listing_id": r["listing_id"], "scraped_at": r["scraped_at"],
                "price_local": price,
                "old_price_local": parse_price(r.get("price_old_raw")),
                "discount_pct": parse_price(r.get("discount_pct_raw")),
                # rank_in_category = true on-screen order across pages
                "page_position": r.get("rank_in_category", r.get("index_position")),
                "is_promoted": None,          # TODO: set if recon finds a reliable marker
                "status": "active", "source": "snapshot",
                "price_flag": price_flag(price)})

    snapshot_ids = {p["source_listing_id"] for p in products}
    posting = {}
    for c in raw.get("cohort_checks", []):
        lid = c["listing_id"]
        if lid in snapshot_ids:
            continue
        price = parse_price(c.get("price_raw")) if c["status"] == "active" else None
        if c["status"] in ("active", "gone"):      # errors are not evidence of removal
            observations.append({
                "source_listing_id": lid, "scraped_at": c["scraped_at"],
                "price_local": price, "old_price_local": None, "discount_pct": None,
                "page_position": None, "is_promoted": None,
                "status": c["status"], "source": "cohort",
                "price_flag": price_flag(price) if c["status"] == "active" else None})
        d = parse_posted(c.get("posted_raw"), c["scraped_at"])
        if d:
            posting[lid] = d

    products_df = pd.DataFrame(products, columns=prod_cols)
    obs_df = pd.DataFrame(observations, columns=obs_cols)
    products_df.attrs["cohort_posting_dates"] = posting
    return meta, products_df, obs_df


def load_raw_file(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
