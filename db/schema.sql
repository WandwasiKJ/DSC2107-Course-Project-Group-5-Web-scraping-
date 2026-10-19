-- Normalised schema for the Jiji Uganda project (SQLite).
-- products     : one row per listing (slowly changing attributes)
-- observations : one row per listing per run (price, rank, status)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY,
    region      TEXT,
    area        TEXT,
    UNIQUE (region, area)
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id         INTEGER PRIMARY KEY,
    run_label      TEXT NOT NULL UNIQUE,   -- e.g. 2026-10-14
    started_at     TEXT,
    finished_at    TEXT,
    requests_made  INTEGER,
    items_scraped  INTEGER,
    blocked        INTEGER DEFAULT 0,
    currency       TEXT DEFAULT 'UGX',
    fx_rate_to_usd REAL,                   -- fill in for the bonus comparison
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id        INTEGER PRIMARY KEY,
    source_listing_id TEXT NOT NULL UNIQUE,
    title             TEXT,
    title_source      TEXT CHECK (title_source IN ('scraped','url_slug','missing') OR title_source IS NULL),
    badge             TEXT,                -- text the card showed instead of a title (e.g. 'Replica', '5', '-16%')
    brand             TEXT,
    model             TEXT,
    storage_gb        INTEGER,
    color             TEXT,
    category_id       INTEGER REFERENCES categories(category_id),
    condition         TEXT CHECK (condition IN ('new','used','refurbished') OR condition IS NULL),
    location_id       INTEGER REFERENCES locations(location_id),
    posting_date      TEXT,
    url               TEXT,
    in_cohort         INTEGER DEFAULT 0,
    first_seen        TEXT,
    last_seen         TEXT
);

CREATE TABLE IF NOT EXISTS observations (
    obs_id        INTEGER PRIMARY KEY,
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    run_id        INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    scraped_at    TEXT NOT NULL,
    price_local   INTEGER,                 -- UGX
    old_price_local INTEGER,               -- only when the card shows a discount
    discount_pct  INTEGER,
    page_position INTEGER,
    is_promoted   INTEGER,
    status        TEXT NOT NULL CHECK (status IN ('active','gone')),
    source        TEXT,                    -- snapshot | cohort
    price_flag    TEXT,                    -- missing | very_low | NULL
    UNIQUE (product_id, run_id)
);

CREATE TABLE IF NOT EXISTS category_daily_totals (
    run_id      INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    total_ads   INTEGER,                   -- "N results" shown by the site that day
    PRIMARY KEY (run_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_obs_product ON observations(product_id);
CREATE INDEX IF NOT EXISTS idx_obs_run     ON observations(run_id);
CREATE INDEX IF NOT EXISTS idx_prod_cat    ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_prod_loc    ON products(location_id);
