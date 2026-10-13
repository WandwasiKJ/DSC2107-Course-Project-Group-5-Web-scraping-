"""Parsing of Jiji (Uganda / Kenya) listing pages and detail pages.

IMPORTANT - VERIFY AGAINST THE LIVE SITE
The card layout was inferred from the page text, not from the raw HTML.
The parser is therefore deliberately defensive: it finds listing links by
their URL pattern, then reads the card's text lines. After inspecting the
real HTML (DevTools -> Elements), tighten it with real CSS selectors and
update tests/test_parse.py with a saved real page.

PRIVACY: this module only ever extracts title, price, condition, location,
URL-derived fields and a posting-date string. Seller names, badges,
descriptions (which can contain phone numbers) are never read into records.
"""
import json
import logging
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

import scraper.config as config

log = logging.getLogger(__name__)

# /nairobi-central/mobile-phones/apple-iphone-12-128-gb-purple-<ID>.html
LISTING_PATH_RE = re.compile(
    r"^/(?P<area>[^/]+)/(?P<category>[^/]+)/(?P<slug>[^/?#]+)"
    r"-(?P<id>[A-Za-z0-9]{20,26})\.html$"
)
CUR = r"(?:USh|UGX|KSh|KES)"           # jiji.ug shows "USh 450,000"; jiji.co.ke shows "KSh ..."
PRICE_RE = re.compile(CUR + r"\s*([\d,]+(?:\.\d+)?)", re.I)
# Discounted cards look like: "USh 2,000,000 -2% USh 2,050,000" (new price, discount, old price)
DISCOUNT_RE = re.compile(CUR + r"\s*([\d,]+)\s*-\s*(\d{1,2})\s*%\s*" + CUR + r"\s*([\d,]+)", re.I)
TOTAL_RE = re.compile(r"([\d\s,]+?)\s+results?\s+for\b", re.I)
CONDITION_LABELS = ("brand new", "refurbished", "local used", "foreign used", "used")
# Seller/promotion badges to skip when hunting for the title line.
BADGE_RE = re.compile(
    r"^(verified id|\d+\+?\s*years?\s+on\s+jiji|vip(_gold)?|enterprise|diamond|"
    r"premium|locked|top|\d\.\d)$", re.I)
LOCATION_RE = re.compile(r"^[A-Za-z][\w .'/()&-]*,\s*\S.*$")
# VERIFY on a real detail page: where/how the posting date appears.
POSTED_RE = re.compile(r"\b(\d+\s+(?:minute|hour|day|week|month)s?\s+ago)\b", re.I)


def match_listing_url(href: str):
    """Return the regex match for a listing href, or None."""
    if not href:
        return None
    return LISTING_PATH_RE.match(urlparse(href).path)


def _card_node(anchor):
    """Climb from the link to the element that holds the whole card."""
    node = anchor
    for _ in range(3):
        if PRICE_RE.search(node.get_text(" ")):
            return node
        parent = node.parent
        if parent is None:
            break
        n_links = sum(1 for a in parent.find_all("a", href=True)
                      if match_listing_url(a["href"]))
        if n_links > 1:      # parent holds several cards: stop climbing
            break
        node = parent
    return anchor


def _lines(node):
    return [ln.strip() for ln in node.get_text("\n", strip=True).split("\n")
            if ln.strip()]


def _slug_title(slug: str) -> str:
    return slug.replace("-", " ").strip().title()


def parse_listing_cards(html: str):
    """Extract one record per listing card on a category page."""
    soup = BeautifulSoup(html, "html.parser")
    records = {}
    for a in soup.find_all("a", href=True):
        m = match_listing_url(a["href"])
        if not m:
            continue
        listing_id = m.group("id")
        node = _card_node(a)
        lines = _lines(node)
        text = " ".join(lines)

        price_m = PRICE_RE.search(text)
        price_raw = f"{config.CURRENCY} {price_m.group(1)}" if price_m else None

        # Old price / discount badge (only a handful of ads have one).
        price_old_raw, discount_pct_raw = None, None
        for i, ln in enumerate(lines):
            if PRICE_RE.search(ln):
                window = " ".join(lines[i:i + 4])
                dm = DISCOUNT_RE.search(window)
                if dm:
                    price_old_raw = f"{config.CURRENCY} {dm.group(3)}"
                    discount_pct_raw = f"{dm.group(2)}%"
                break

        cond_idx, condition_raw = None, None
        for i, ln in enumerate(lines):
            if ln.lower() in CONDITION_LABELS:
                cond_idx, condition_raw = i, ln
                break

        location_raw = None
        if cond_idx is not None:
            for ln in lines[cond_idx + 1:cond_idx + 4]:
                if LOCATION_RE.match(ln) and not PRICE_RE.search(ln):
                    location_raw = ln
                    break

        title, title_source = a.get("title"), "attr"
        if not title:
            for ln in lines:
                if not BADGE_RE.match(ln) and not PRICE_RE.search(ln):
                    title, title_source = ln, "text"
                    break
        if not title:
            title, title_source = _slug_title(m.group("slug")), "slug"

        qs = parse_qs(urlparse(a["href"]).query)
        try:
            index_position = int(qs.get("indexPosition", [None])[0])
        except (TypeError, ValueError):
            index_position = None

        rec = {
            "listing_id": listing_id,
            "url": config.BASE_URL + urlparse(a["href"]).path
                   if a["href"].startswith("/") else a["href"].split("?")[0],
            "category_slug": m.group("category"),
            "area_slug": m.group("area"),
            "title": title,
            "title_source": title_source,
            "price_raw": price_raw,
            "price_old_raw": price_old_raw,
            "discount_pct_raw": discount_pct_raw,
            "condition_raw": condition_raw,
            "location_raw": location_raw,
            "index_position": index_position,
        }
        # Keep the first anchor per listing unless a later one has the price.
        prev = records.get(listing_id)
        if prev is None or (prev["price_raw"] is None and price_raw):
            records[listing_id] = rec
        for field in ("price_raw", "condition_raw", "location_raw"):
            if rec[field] is None:
                log.debug("Missing %s for %s", field, listing_id)
    return list(records.values())


def parse_total_results(html: str):
    """'15154 results for Mobile Phones' -> 15154 (cheap market-size data point)."""
    soup = BeautifulSoup(html, "html.parser")
    m = TOTAL_RE.search(soup.get_text(" "))
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(1))
    return int(digits) if digits else None


def _find_price(obj):
    """Walk parsed JSON-LD looking for an offer price."""
    if isinstance(obj, dict):
        if "price" in obj and obj["price"] not in (None, ""):
            return obj["price"]
        for v in obj.values():
            found = _find_price(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_price(v)
            if found is not None:
                return found
    return None


def parse_detail(html: str):
    """Price and posting-date string from a listing's detail page.

    Only these two values are read. VERIFY the selectors on a real page.
    """
    soup = BeautifulSoup(html, "html.parser")
    price_raw = None
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        price = _find_price(data)
        if price is not None:
            try:
                price_raw = f"{config.CURRENCY} {int(float(price)):,}"
            except (ValueError, TypeError):
                pass
            break
    text = soup.get_text(" ")
    if price_raw is None:
        m = PRICE_RE.search(text)
        price_raw = f"{config.CURRENCY} {m.group(1)}" if m else None
    posted = POSTED_RE.search(text)
    return {"price_raw": price_raw,
            "posted_raw": posted.group(1) if posted else None}

