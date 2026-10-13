"""Central configuration for the DSC2107 Jiji Uganda scraper (Group 5).

Everything a teammate might need to change lives here, so that the
scraper, cleaner and loader never contain "magic numbers".

Items marked VERIFY must be checked against the live site during
reconnaissance (Day 1-2) and recorded in the recon note.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
SAMPLE_DIR = ROOT / "data" / "sample"
LOG_DIR = ROOT / "logs"
DOCS_DIR = ROOT / "docs"
DB_PATH = ROOT / "db" / "jiji_ug.db"
COHORT_FILE = ROOT / "data" / "cohort.json"

# ---------------------------------------------------------------- identity
SITE_CODE = "ug"
BASE_URL = "https://jiji.ug"
RAW_PREFIX = f"jiji_{SITE_CODE}_"      # raw files: jiji_ug_YYYY-MM-DD.json
CURRENCY = "UGX"                         # the site displays this as "USh"
GROUP = "Group 5"                       # per the assignment sheet: Jiji Uganda
CONTACT_EMAIL = "B32912@students.ucu.ac.ug"   # TODO: a monitored address
USER_AGENT = f"DSC2107-Course-Project ({GROUP}, {CONTACT_EMAIL})"
ROBOTS_AGENT = "DSC2107-Course-Project"  # token matched against robots.txt

# ------------------------------------------------------- rules of engagement
DELAY_RANGE = (2.0, 5.0)        # seconds, random wait before EVERY request
MAX_REQUESTS_PER_RUN = 950      # hard stop; the rubric cap is ~1,000
RETRY_BACKOFF = (5, 15, 45)     # seconds between retry attempts
TIMEOUT = 20                    # seconds per request

# --------------------------------------------------------------- what to scrape
# name -> path. Confirm each path is allowed in robots.txt and agree the
# list with the Jiji Uganda group (they must use the same categories).
CATEGORIES = {
    "mobile-phones": "/mobile-phones",
    "tablets": "/tablets",
    "smart-watches": "/smart-watches",
}
TARGET_PER_CATEGORY = 200       # 3 x 200 = 600 >= 500 required
MAX_PAGES_PER_CATEGORY = 25     # loop guard
PAGE_PARAM = "page"             # VERIFY: query parameter used for page 2, 3...
EXTRA_PARAMS = {}               # VERIFY: e.g. a sort-by-newest parameter
MIN_ITEMS_FOR_SUCCESS = 500     # run is flagged if fewer rows collected
CARDS_PER_PAGE_EXPECTED = 20    # seen on jiji.ug category pages; used only for log sanity checks

# Tracking cohort: the same listings re-checked daily (for price changes
# and disappearances). Chosen once, on Day 4, from that day's snapshot.
COHORT_SIZE = 300

# ------------------------------------------------------------------ cleaning
USD_PER_LOCAL = None            # set (with the date) for the bonus UGX->USD comparison
VERY_LOW_PRICE_LOCAL = 10000    # UGX; prices below this are flagged, not deleted

