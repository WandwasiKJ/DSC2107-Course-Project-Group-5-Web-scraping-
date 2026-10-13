# Data dictionary

## Raw files: `data/raw/jiji_ug_YYYY-MM-DD.json`
`meta` (run info), `snapshot` (one record per card), `cohort_checks` (re-visits). Never edited.

| Raw field | Meaning |
|---|---|
| listing_id | ID taken from the listing URL |
| url, category_slug, area_slug | URL and URL-derived parts |
| title | Listing title |
| price_raw | Price text as shown, e.g. "UGX 450,000" (site shows "USh") |
| price_old_raw, discount_pct_raw | Old price and discount badge, when the card shows them (rare) |
| condition_raw | Condition label as shown |
| location_raw | "Region, Area" text as shown |
| index_position | Value of the `indexPosition` URL parameter |
| rank_in_category | On-screen rank across pages (cards sorted by indexPosition within each page) |
| category, page, scraped_at, run_id | Added by the scraper (scraped_at is UTC ISO) |

## Database tables
| Table.column | Type | Description / cleaning rule |
|---|---|---|
| categories.name | TEXT | Category slug scraped (mobile-phones, tablets, ...) |
| locations.region, area | TEXT | Split from "Region, Area" (e.g. Kampala / Central Division); title-cased |
| category_daily_totals.total_ads | INT | The "N results" counter shown on each category page that day |
| scrape_runs.* | | One row per run: counts, requests, blocked flag, FX rate (bonus) |
| products.source_listing_id | TEXT | Unique listing ID from URL |
| products.title | TEXT | As scraped |
| products.brand, model, storage_gb, color | | Heuristic extraction from title (see cleaning/clean.py); NULL if not found |
| products.condition | TEXT | new / used / refurbished (Brand New->new; Local/Foreign Used->used) |
| products.posting_date | TEXT | ISO date; converted from relative text using scraped_at (approximate) |
| products.in_cohort | INT | 1 if in the daily tracking cohort |
| products.first_seen, last_seen | TEXT | First/last scrape time seen active |
| observations.price_local | INT | UGX price as integer; NULL if missing or not numeric |
| observations.old_price_local, discount_pct | INT | From the discount badge when shown; otherwise NULL |
| observations.page_position | INT | rank_in_category (visibility proxy; promoted ads distort it) |
| observations.status | TEXT | active / gone (404/410 or redirected away; network errors are NOT treated as gone) |
| observations.source | TEXT | snapshot or cohort |
| observations.price_flag | TEXT | missing, very_low (< UGX 10,000) or NULL; flagged, not deleted |

## Known limitations
Relative posting dates are approximate; listing price is not sale price; "negotiable" prices
are not visible; promoted ads affect rank; only 7 days observed; brand/model parsing is heuristic.
