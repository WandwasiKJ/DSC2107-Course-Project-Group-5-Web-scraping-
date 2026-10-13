"""Save one real page to disk so you can study it offline and test against it.

    python -m scraper.save_page https://jiji.ug/mobile-phones tests/fixtures/category_page.html
"""
import sys
from pathlib import Path

from scraper.fetch import PoliteSession


def main():
    url, out = sys.argv[1], Path(sys.argv[2])
    session = PoliteSession()
    session.load_robots()
    resp = session.get(url)
    if resp is None:
        sys.exit("Could not fetch the page")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(resp.text, encoding="utf-8")
    print(f"Saved {len(resp.text):,} characters (HTTP {resp.status_code}) to {out}")


if __name__ == "__main__":
    main()
