# Database fixes (what changed and why)

| # | File | Problem | Fix |
|---|------|---------|-----|
| 1 | `cleaning/clean.py` | Loader crashed (`'float' object has no attribute 'split'`): listings with no location arrive from pandas as `NaN` | Added `_blank()`; every parser is NaN-safe and the snapshot is converted NaN -> None once |
| 2 | `scraper/config.py` | `DB_PATH` resolved to `scraper/db/jiji_ug.db`, not `db/` | Added `PROJECT_ROOT`; `DB_PATH = PROJECT_ROOT / "db" / "jiji_ug.db"` |
| 3 | `clean.py` (repo root) | Stale duplicate of `cleaning/clean.py` (no title/location recovery) | Deleted. Only `cleaning/clean.py` is used |
| 4 | `cleaning/clean.py` | Title recovery regex required 24-char IDs; 95 IDs are 22-23 chars | Accept 20-25 chars |
| 5 | `cleaning/clean.py` | Duplicate keys in `BRANDS`; ~31% of products had no brand | De-duplicated; added missing brands/aliases (84% coverage) |
| 6 | `db/load.py` | numpy ints can't be bound by sqlite3; no rollback; no rebuild; `last_seen` not monotonic | `_none()` converts numpy -> Python; rollback per run; `--rebuild`; `last_seen`/`in_cohort` use MAX |
| 7 | `db/schema.sql` + loader | Recovered titles and badge text were not stored | Added `products.title_source`, `products.badge` |
| 8 | `db/validate.py` (new) | Nothing verified the database | 11 hard integrity checks + warnings on known data limits |
| 9 | `scraper/run.py` | Hard-coded `sys.path.append('C:/Users/jonnathan/...')` | Removed |
| 10 | `.vscode/settings.json` | Plaintext MySQL password committed | Removed. **Rotate that password; it is still in git history** |
| 11 | `.gitignore` | Saved as UTF-16, which git ignores (so `__pycache__` got committed) | Rewritten as UTF-8, added `.vscode/` |
| 12 | `__init__.py` (root) | `print("hello world")`; breaks pytest import resolution | Deleted |
| 13 | `tests/test_clean.py` (new) | No tests for cleaning/loading | 11 tests |

## Rebuild
    python -m db.load --rebuild
    python -m db.validate
    python -m pytest -q
