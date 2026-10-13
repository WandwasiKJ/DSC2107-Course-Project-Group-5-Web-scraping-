"""Polite HTTP layer: every request in the project goes through here.

Rules of Engagement implemented in code (so they can be shown to markers):
  * robots.txt is fetched, saved as evidence, and checked before every URL
  * a random 2-5 s delay precedes every request (including retries)
  * a hard per-run request budget
  * a clear User-Agent naming the course and a contact email
  * retry with exponential-style back-off on timeouts / 5xx
  * STOP (never bypass) on 403 / 429 / block pages
"""
import logging
import random
import time
from datetime import date
from urllib import robotparser
from urllib.parse import urlparse

import requests  # type: ignore[reportMissingModuleSource]

import config

log = logging.getLogger(__name__)

BLOCK_PHRASES = (
    "verify you are human",
    "access denied",
    "attention required",
    "captcha-delivery",
    "unusual traffic",
)


class BlockedError(RuntimeError):
    """Site refused us (403/429/CAPTCHA). We stop and document, never bypass."""


class BudgetExceeded(RuntimeError):
    """Per-run request budget used up."""


class RobotsDisallowed(RuntimeError):
    """robots.txt does not allow this URL."""


def looks_blocked(text: str) -> bool:
    """Block/CAPTCHA pages are small; real listing pages are large."""
    if len(text) > 20000:
        return False
    low = text.lower()
    return any(p in low for p in BLOCK_PHRASES)


class PoliteSession:
    def __init__(self, max_requests=config.MAX_REQUESTS_PER_RUN,
                 delay_range=config.DELAY_RANGE, sleep=time.sleep,
                 base_url=config.BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.http = requests.Session()
        self.http.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en",
        })
        self.max_requests = max_requests
        self.delay_range = delay_range
        self._sleep = sleep
        self.requests_made = 0
        self.errors = 0
        self._robots = None

    # ------------------------------------------------------------ robots.txt
    def load_robots(self, save_copy=True):
        """Fetch robots.txt once per run and keep a dated copy as evidence."""
        url = self.base_url + "/robots.txt"
        self._sleep(random.uniform(*self.delay_range))
        self.requests_made += 1
        resp = self.http.get(url, timeout=config.TIMEOUT)
        rp = robotparser.RobotFileParser()
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
            if save_copy:
                config.DOCS_DIR.mkdir(exist_ok=True)
                host = urlparse(self.base_url).netloc
                out = config.DOCS_DIR / f"robots_{host}_{date.today().isoformat()}.txt"
                out.write_text(resp.text, encoding="utf-8")
                log.info("Saved robots.txt copy to %s", out)
        elif resp.status_code == 404:
            rp.parse([])  # no robots.txt = nothing disallowed
            log.warning("robots.txt returned 404")
        else:
            raise RuntimeError(
                f"Cannot verify robots.txt (HTTP {resp.status_code}); stopping.")
        self._robots = rp

    def allowed(self, url: str) -> bool:
        if self._robots is None:
            raise RuntimeError("Call load_robots() before fetching pages.")
        # NOTE: urllib's parser does not understand '*' / '$' wildcards in
        # Disallow lines. Also read robots.txt yourselves and document it.
        return self._robots.can_fetch(config.ROBOTS_AGENT, url)

    # --------------------------------------------------------------- fetching
    def get(self, url: str, params=None):
        """GET with politeness. Returns a Response, or None after retries fail.

        Raises BlockedError, BudgetExceeded or RobotsDisallowed.
        """
        if not self.allowed(url):
            raise RobotsDisallowed(url)

        attempts = len(config.RETRY_BACKOFF) + 1
        for attempt in range(attempts):
            if self.requests_made >= self.max_requests:
                raise BudgetExceeded(f"{self.max_requests} requests reached")
            self._sleep(random.uniform(*self.delay_range))
            self.requests_made += 1
            try:
                resp = self.http.get(url, params=params, timeout=config.TIMEOUT)
            except (requests.Timeout, requests.ConnectionError) as exc:
                self.errors += 1
                log.warning("Network error on %s (attempt %d): %s",
                            url, attempt + 1, exc)
            else:
                if resp.status_code in (403, 429):
                    raise BlockedError(f"HTTP {resp.status_code} on {url}")
                if resp.status_code == 200 and looks_blocked(resp.text):
                    raise BlockedError(f"Block/CAPTCHA page on {url}")
                if resp.status_code >= 500:
                    self.errors += 1
                    log.warning("HTTP %d on %s (attempt %d)",
                                resp.status_code, url, attempt + 1)
                else:
                    return resp  # 200, 404, 410 etc: caller decides

            if attempt < len(config.RETRY_BACKOFF):
                wait = config.RETRY_BACKOFF[attempt]
                log.info("Backing off %ss before retry", wait)
                self._sleep(wait)

        log.error("Giving up on %s after %d attempts", url, attempts)
        return None