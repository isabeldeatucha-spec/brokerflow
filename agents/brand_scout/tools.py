"""
All external tool calls for the Brand Scout agent — scraping, search, and email.

Real implementations:
  scrape_whole_foods_new_arrivals  — Tavily search
  scrape_sprouts_new_arrivals      — Tavily search
  scrape_target_new_arrivals       — Tavily search
  scrape_brand_website             — requests + BeautifulSoup
  scrape_amazon_listing            — Tavily search

Stubs remaining:
  scrape_faire_listing, search, find_founder_contact, send_email
"""
import os
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ── Discovery via Tavily search ───────────────────────────────────────────────

# Words that look like proper nouns but are not CPG brand names
_NOISE_WORDS = {
    "whole", "foods", "sprouts", "target", "walmart", "kroger", "amazon",
    "new", "arrivals", "products", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october", "november", "december",
    "food", "beverage", "brand", "brands", "grocery", "store", "market",
    "organic", "natural", "fresh", "healthy", "snack", "drink", "product",
    "best", "top", "must", "try", "here", "what", "this", "these", "that",
    "the", "and", "for", "with", "from", "has", "are", "its", "our", "your",
    "usa", "inc", "llc", "co", "corp", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday",
}

# Matches 1–4 consecutive Title-Cased words (typical CPG brand name shape)
_BRAND_NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z&']+){0,3})\b")


def _extract_brands_from_text(text: str, retailer: str) -> list[dict[str, Any]]:
    """Pull candidate brand names from a block of text using regex heuristics."""
    candidates: list[str] = []
    seen: set[str] = set()
    for m in _BRAND_NAME_RE.finditer(text):
        name = m.group(1).strip()
        words = name.lower().split()
        # Skip if all words are noise or the name is just one common word
        if all(w in _NOISE_WORDS for w in words):
            continue
        if len(name) < 3 or name in seen:
            continue
        seen.add(name)
        candidates.append(name)
    return [{"brand_name": b, "retailer": retailer} for b in candidates]


def _tavily_discovery_search(query: str, retailer: str) -> list[dict[str, Any]]:
    """Run one Tavily query and return extracted brand candidates."""
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return [{"error": f"TAVILY_API_KEY not set (query: {query})"}]
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=8, include_raw_content=False)
    except Exception as exc:
        return [{"error": f"Tavily search failed for '{retailer}': {exc}"}]

    results = response.get("results", [])
    if not results:
        return [{"error": f"No Tavily results for '{retailer}' query"}]

    # Combine titles + snippets from all results into one text block
    combined = " ".join(
        (r.get("title") or "") + " " + (r.get("content") or "")
        for r in results
    )
    brands = _extract_brands_from_text(combined, retailer)
    # Attach source URLs to the first few brands for traceability
    source_urls = [r.get("url", "") for r in results[:3]]
    for brand in brands:
        brand["source_urls"] = source_urls
    return brands if brands else [{"error": f"No brand names extracted for '{retailer}'"}]


def scrape_whole_foods_new_arrivals(brand_name: str = "") -> list[dict[str, Any]]:
    """Search for Whole Foods new arrivals via Tavily and extract brand names."""
    query = (
        f"{brand_name} whole foods"
        if brand_name
        else "whole foods new arrivals 2026 food beverage brand"
    )
    return _tavily_discovery_search(query, retailer="Whole Foods")


def scrape_target_new_arrivals(brand_name: str = "") -> list[dict[str, Any]]:
    """Search for Target new food/beverage brands via Tavily."""
    query = (
        f"{brand_name} target"
        if brand_name
        else "target new food beverage brands 2026"
    )
    return _tavily_discovery_search(query, retailer="Target")


def scrape_walmart_new_arrivals() -> list[dict[str, Any]]:
    """Scrape Walmart new arrivals — STUB."""
    return []


def scrape_sprouts_new_arrivals(brand_name: str = "") -> list[dict[str, Any]]:
    """Search for Sprouts new products via Tavily."""
    query = (
        f"{brand_name} sprouts"
        if brand_name
        else "sprouts farmers market new products 2026"
    )
    return _tavily_discovery_search(query, retailer="Sprouts")


# ── Brand research scraping ───────────────────────────────────────────────────

_RETAIL_KEYWORDS = [
    "whole foods", "sprouts", "target", "walmart", "kroger", "costco",
    "trader joe", "publix", "wegmans", "safeway", "albertsons", "cvs",
    "walgreens", "amazon", "thrive market", "fresh market", "erewhon",
]
_WHERE_TO_BUY_PATTERNS = re.compile(
    r"(find us|where to buy|store locator|retailers|stockists|available at)",
    re.IGNORECASE,
)
_SOCIAL_PATTERNS = {
    "instagram": re.compile(r"instagram\.com/([A-Za-z0-9_.]+)", re.IGNORECASE),
    "tiktok": re.compile(r"tiktok\.com/@([A-Za-z0-9_.]+)", re.IGNORECASE),
}
_PRICE_PATTERN = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")


def scrape_brand_website(url: str) -> dict[str, Any]:
    """Scrape a brand's own website for description, retailers, SKUs, prices, social."""
    if not url:
        return {"error": "No URL provided"}
    if not url.startswith("http"):
        url = "https://" + url

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        return {"url": url, "error": f"Request failed: {exc}"}

    soup = BeautifulSoup(resp.text, "html.parser")
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    # ── Description / about text ──────────────────────────────────────────────
    description = ""
    for sel in ["meta[name='description']", "meta[property='og:description']"]:
        tag = soup.select_one(sel)
        if tag and tag.get("content"):
            description = tag["content"].strip()
            break
    if not description:
        for tag in soup.select("p"):
            text = tag.get_text(strip=True)
            if len(text) > 80:
                description = text[:300]
                break

    # ── Social links ──────────────────────────────────────────────────────────
    page_text = resp.text
    social_links: dict[str, str] = {}
    for platform, pattern in _SOCIAL_PATTERNS.items():
        m = pattern.search(page_text)
        if m:
            handle = m.group(1).rstrip("/")
            if platform == "instagram":
                social_links["instagram"] = f"https://instagram.com/{handle}"
            else:
                social_links["tiktok"] = f"https://tiktok.com/@{handle}"

    # ── Retail partners ───────────────────────────────────────────────────────
    retailers_found: list[str] = []
    full_text = soup.get_text(" ", strip=True).lower()
    for retailer in _RETAIL_KEYWORDS:
        if retailer in full_text:
            retailers_found.append(retailer.title())

    # Also follow "where to buy" / "find us" links one level deep
    wtb_links = [
        a["href"] for a in soup.find_all("a", href=True)
        if _WHERE_TO_BUY_PATTERNS.search(a.get_text()) or
           _WHERE_TO_BUY_PATTERNS.search(str(a.get("href", "")))
    ]
    has_store_locator = bool(wtb_links)
    for rel_link in wtb_links[:2]:
        wtb_url = urljoin(base_url, rel_link)
        if urlparse(wtb_url).netloc != urlparse(base_url).netloc:
            continue
        try:
            sub = requests.get(wtb_url, headers=_HEADERS, timeout=10)
            sub_text = sub.text.lower()
            for retailer in _RETAIL_KEYWORDS:
                if retailer in sub_text and retailer.title() not in retailers_found:
                    retailers_found.append(retailer.title())
        except Exception:
            pass

    # ── Price points ──────────────────────────────────────────────────────────
    prices = sorted(set(float(p) for p in _PRICE_PATTERN.findall(page_text)
                        if 0.5 < float(p) < 200))
    price_range = ""
    if prices:
        lo, hi = prices[0], prices[-1]
        price_range = f"${lo:.2f}" if lo == hi else f"${lo:.2f} – ${hi:.2f}"

    # ── SKU count (distinct product names) ────────────────────────────────────
    product_names: list[str] = []
    for sel in [
        "[class*='product'] [class*='title']",
        "[class*='product'] [class*='name']",
        "[class*='ProductCard'] h2",
        "[class*='ProductCard'] h3",
        ".product-title", ".product-name",
        "h2[class*='product']", "h3[class*='product']",
    ]:
        els = soup.select(sel)
        if els:
            product_names = list(dict.fromkeys(e.get_text(strip=True) for e in els if e.get_text(strip=True)))
            break

    # Fallback: look for /products/ links (Shopify pattern)
    if not product_names:
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/products/" in href:
                label = a.get_text(strip=True)
                if label and label not in seen:
                    seen.add(label)
                    product_names.append(label)
        product_names = [n for n in product_names if len(n) > 2][:40]

    return {
        "url": url,
        "description": description,
        "retail_partners": list(dict.fromkeys(retailers_found)),
        "has_store_locator": has_store_locator,
        "sku_count": len(product_names),
        "product_names_sample": product_names[:10],
        "price_range": price_range,
        "social_links": social_links,
    }


_REVIEW_COUNT_PATTERN = re.compile(r"([\d,]+)\s*(ratings?|reviews?)", re.IGNORECASE)
_RATING_PATTERN = re.compile(r"(\d\.\d)\s*out of\s*5", re.IGNORECASE)
_PRICE_EXTRACT = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")
_ASIN_PATTERN = re.compile(r"/dp/([A-Z0-9]{10})")


def scrape_amazon_listing(brand_name: str) -> dict[str, Any]:
    """Search Amazon via Tavily and extract presence, pricing, ratings, SKU count."""
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return {"brand_name": brand_name, "error": "TAVILY_API_KEY not set"}

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=f"{brand_name} site:amazon.com",
            max_results=8,
            include_raw_content=True,
        )
    except Exception as exc:
        return {"brand_name": brand_name, "error": f"Tavily search failed: {exc}"}

    results = response.get("results", [])
    if not results:
        return {"brand_name": brand_name, "on_amazon": False}

    # Aggregate across all result snippets
    all_text = " ".join(
        (r.get("content") or "") + " " + (r.get("raw_content") or "")
        for r in results
    )

    # Review count
    review_count = 0
    m = _REVIEW_COUNT_PATTERN.search(all_text)
    if m:
        review_count = int(m.group(1).replace(",", ""))

    # Average rating
    average_rating = 0.0
    m = _RATING_PATTERN.search(all_text)
    if m:
        average_rating = float(m.group(1))

    # Price — take the median of all found prices to avoid outliers
    raw_prices = [float(p) for p in _PRICE_EXTRACT.findall(all_text) if 0.5 < float(p) < 500]
    price = 0.0
    if raw_prices:
        raw_prices.sort()
        mid = len(raw_prices) // 2
        price = raw_prices[mid]

    # ASIN / SKU count — count unique ASINs across result URLs
    asins: set[str] = set()
    for r in results:
        for asin in _ASIN_PATTERN.findall(r.get("url", "")):
            asins.add(asin)

    has_subscribe_save = "subscribe" in all_text.lower() and "save" in all_text.lower()

    return {
        "brand_name": brand_name,
        "on_amazon": True,
        "review_count": review_count,
        "average_rating": average_rating,
        "price": price,
        "sku_count": len(asins),
        "asin_sample": list(asins)[:5],
        "has_subscribe_and_save": has_subscribe_save,
        "sources": [r.get("url") for r in results[:3]],
    }


_REORDER_RATE_RE = re.compile(r"(\d+)\s*%\s*reorder", re.IGNORECASE)
_DOOR_COUNT_RE = re.compile(r"([\d,]+)\s*(retailers?|stores?|doors?|accounts?)", re.IGNORECASE)


def scrape_faire_listing(brand_name: str) -> dict[str, Any]:
    """Search for Faire wholesale presence via Tavily."""
    results = search(f"{brand_name} faire.com wholesale", max_results=5)
    if results and "error" in results[0]:
        return {"brand_name": brand_name, "error": results[0]["error"]}

    all_text = " ".join(r.get("content", "") for r in results)
    on_faire = any("faire" in r.get("url", "").lower() for r in results)

    reorder_rate = ""
    m = _REORDER_RATE_RE.search(all_text)
    if m:
        reorder_rate = f"{m.group(1)}%"

    retailers_carrying = 0
    m = _DOOR_COUNT_RE.search(all_text)
    if m:
        retailers_carrying = int(m.group(1).replace(",", ""))

    return {
        "brand_name": brand_name,
        "on_faire": on_faire,
        "reorder_rate": reorder_rate,
        "retailers_carrying": retailers_carrying,
        "sources": [r.get("url") for r in results[:3]],
    }


# ── Web search ────────────────────────────────────────────────────────────────

def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Run a Tavily web search. Returns list of result dicts or a single error dict."""
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return [{"error": "TAVILY_API_KEY not set", "query": query}]
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
    except Exception as exc:
        return [{"error": f"Tavily search failed: {exc}", "query": query}]
    return response.get("results", [])


def search_velocity_signals(brand_name: str) -> dict[str, Any]:
    """Search for SPINS/NIQ velocity data, press sell-through mentions, Instacart presence."""
    spins_results = search(f"{brand_name} SPINS velocity NIQ scan data units per store", max_results=4)
    instacart_results = search(f"{brand_name} site:instacart.com", max_results=4)
    press_velocity = search(f"{brand_name} sell-through restock NOSH \"New Hope Network\"", max_results=4)

    all_spins = " ".join(r.get("content", "") for r in spins_results if "error" not in r)
    all_instacart = " ".join(r.get("content", "") for r in instacart_results if "error" not in r)

    instacart_banners: list[str] = []
    for keyword in ["whole foods", "sprouts", "kroger", "safeway", "publix", "target", "costco"]:
        if keyword in all_instacart.lower():
            instacart_banners.append(keyword.title())

    return {
        "spins_mentions": [r.get("title") for r in spins_results if "error" not in r][:3],
        "spins_snippets": all_spins[:600],
        "instacart_banners": instacart_banners,
        "instacart_sources": [r.get("url") for r in instacart_results if "error" not in r][:3],
        "press_velocity_snippets": [r.get("content", "")[:200] for r in press_velocity if "error" not in r][:3],
    }


def search_press_and_story(brand_name: str) -> dict[str, Any]:
    """Search trade and consumer press for brand story, awards, Expo West presence."""
    trade_results = search(
        f"{brand_name} site:nosh.com OR site:foodnavigator-usa.com OR site:newhope.com OR site:grocerydive.com",
        max_results=4,
    )
    consumer_results = search(
        f"{brand_name} Forbes \"Bon Appetit\" NYT Food52 \"Serious Eats\"",
        max_results=4,
    )
    expo_results = search(
        f"{brand_name} \"expo west\" OR \"expo east\" 2024 2025",
        max_results=3,
    )
    social_results = search(
        f"{brand_name} instagram followers tiktok viral",
        max_results=4,
    )

    trade_hits = [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:200]}
                  for r in trade_results if "error" not in r]
    consumer_hits = [{"title": r.get("title"), "url": r.get("url")}
                     for r in consumer_results if "error" not in r]
    expo_hits = [{"title": r.get("title"), "url": r.get("url")}
                 for r in expo_results if "error" not in r]

    social_text = " ".join(r.get("content", "") for r in social_results if "error" not in r)
    follower_match = re.search(r"([\d.,]+[Kk]?)\s*followers", social_text)
    follower_count = follower_match.group(1) if follower_match else ""

    return {
        "trade_press_hits": trade_hits,
        "consumer_press_hits": consumer_hits,
        "expo_west_hits": expo_hits,
        "instagram_follower_signal": follower_count,
        "social_snippets": social_text[:400],
    }


def search_funding_and_team(brand_name: str) -> dict[str, Any]:
    """Search for funding rounds, team hires, and promo dependency signals."""
    funding_results = search(
        f"{brand_name} funding raised seed series crunchbase",
        max_results=4,
    )
    promo_results = search(
        f"{brand_name} promotion discount sale BOGO coupon",
        max_results=3,
    )

    funding_text = " ".join(r.get("content", "") for r in funding_results if "error" not in r)
    amount_match = re.search(r"\$\s*([\d,.]+)\s*(million|M\b|thousand|K\b)", funding_text, re.IGNORECASE)
    raised = amount_match.group(0).strip() if amount_match else ""

    promo_text = " ".join(r.get("content", "") for r in promo_results if "error" not in r)

    return {
        "funding_raised": raised,
        "funding_snippets": funding_text[:400],
        "funding_sources": [r.get("url") for r in funding_results if "error" not in r][:3],
        "promo_dependency_snippets": promo_text[:300],
    }


def find_founder_contact(brand_name: str, website_url: str) -> dict[str, str]:
    """Search for founder name and email — STUB."""
    return {
        "founder_name": "Jane Smith",
        "founder_email": "jane@oatandhonor.com",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "source": "mock",
    }


# ── Email sending ─────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, body: str) -> dict[str, str]:
    """Send an email via Gmail API — STUB logs to console."""
    print(f"\n[GMAIL STUB] Would send email:")
    print(f"  To:      {to}")
    print(f"  Subject: {subject}")
    print(f"  Body:\n{body}\n")
    return {"status": "sent_stub", "message_id": "stub_msg_001"}


def get_gmail_service():
    """Build an authenticated Gmail service — STUB."""
    raise NotImplementedError(
        "Swap in real OAuth flow. See: "
        "https://developers.google.com/gmail/api/quickstart/python"
    )
