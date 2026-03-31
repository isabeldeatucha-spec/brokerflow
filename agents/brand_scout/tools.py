"""
All external tool calls for the Brand Scout agent — scraping, search, and email.

Uses Parallel AI Python SDK (parallel-web) for all data gathering.

Real implementations:
  scrape_whole_foods_new_arrivals  — Parallel Extract + Search fallback
  scrape_target_new_arrivals       — Parallel Extract + Search fallback
  scrape_sprouts_new_arrivals      — Parallel Extract + Search fallback
  scrape_walmart_new_arrivals      — Parallel Search
  scrape_brand_website             — Parallel Extract
  scrape_amazon_listing            — Parallel Extract
  scrape_faire_listing             — Parallel Extract + Search fallback
  search / search_velocity_signals
  search_press_and_story
  search_funding_and_team          — Parallel Search
  find_founder_contact             — Parallel Search (real, not stub)

Stubs remaining:
  send_email                       — Gmail OAuth not wired
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from dotenv import load_dotenv
from parallel import Parallel

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Reads PARALLEL_API_KEY from env automatically
parallel_client = Parallel()


# ── Parallel AI helpers ───────────────────────────────────────────────────────

def parallel_extract(url: str, objective: str) -> str:
    """
    Extract content from a URL using Parallel Extract SDK.
    Returns full_content markdown, or joined excerpts, or error string.
    """
    try:
        response = parallel_client.beta.extract(
            urls=[url],
            objective=objective,
            full_content=True,
        )
        if response.results:
            r = response.results[0]
            if r.full_content:
                return r.full_content
            if r.excerpts:
                return "\n\n".join(r.excerpts)
        if response.errors:
            return f"extract_error: {response.errors[0]}"
        return "extract_error: no content returned"
    except Exception as e:
        return f"extract_error: {e}"


def _parallel_search_raw(query: str, num_results: int = 5) -> list:
    """
    Run a Parallel web search. Returns list of WebSearchResult objects.
    Internal helper — callers use search() or parallel_search_text().
    """
    try:
        response = parallel_client.beta.search(
            objective=query,
            search_queries=[query],
            max_results=num_results,
            mode="fast",
        )
        return response.results or []
    except Exception as e:
        return []


def parallel_search_text(query: str, num_results: int = 5) -> str:
    """Search the web and return concatenated excerpts as a single string."""
    try:
        results = _parallel_search_raw(query, num_results)
        parts = []
        for r in results:
            title = r.title or ""
            excerpt = " ".join(r.excerpts) if r.excerpts else ""
            parts.append(f"{title}: {excerpt}".strip(": "))
        return "\n\n".join(parts)
    except Exception as e:
        return f"search_error: {e}"


# ── Brand name extraction helpers ─────────────────────────────────────────────

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

_BRAND_NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z&']+){0,3})\b")


def _extract_brands_from_text(text: str, retailer: str) -> list[dict[str, Any]]:
    """Pull candidate brand names from a block of text using regex heuristics."""
    candidates: list[str] = []
    seen: set[str] = set()
    for m in _BRAND_NAME_RE.finditer(text):
        name = m.group(1).strip()
        words = name.lower().split()
        if all(w in _NOISE_WORDS for w in words):
            continue
        if len(name) < 3 or name in seen:
            continue
        seen.add(name)
        candidates.append(name)
    return [{"brand_name": b, "retailer": retailer} for b in candidates]


# ── Discovery via Parallel Extract / Search ───────────────────────────────────

def scrape_whole_foods_new_arrivals(brand_name: str = "") -> list[dict[str, Any]]:
    """Discover new Whole Foods brands via Parallel Extract, with Search fallback."""
    if brand_name:
        results = _parallel_search_raw(f"{brand_name} whole foods", 8)
        content = " ".join(
            f"{r.title or ''} {' '.join(r.excerpts or [])}" for r in results
        )
        brands = _extract_brands_from_text(content, "Whole Foods")
        sources = [r.url for r in results[:3]]
        for b in brands:
            b["source_urls"] = sources
        return brands or [{"error": f"No brands found for '{brand_name}' at Whole Foods"}]

    content = parallel_extract(
        "https://www.wholefoodsmarket.com/products/new-arrivals",
        "Extract all brand names and product names from new arrivals listings",
    )
    if "extract_error" in content:
        content = parallel_search_text("whole foods new arrivals 2026 new food beverage brands", 8)
    brands = _extract_brands_from_text(content, "Whole Foods")
    return brands if brands else [{"error": "No brand names extracted from Whole Foods"}]


def scrape_target_new_arrivals(brand_name: str = "") -> list[dict[str, Any]]:
    """Discover new Target food/beverage brands via Parallel Extract, with Search fallback."""
    if brand_name:
        results = _parallel_search_raw(f"{brand_name} target", 8)
        content = " ".join(
            f"{r.title or ''} {' '.join(r.excerpts or [])}" for r in results
        )
        brands = _extract_brands_from_text(content, "Target")
        sources = [r.url for r in results[:3]]
        for b in brands:
            b["source_urls"] = sources
        return brands or [{"error": f"No brands found for '{brand_name}' at Target"}]

    content = parallel_extract(
        "https://www.target.com/c/food/-/N-5xt1a?Nrpp=24&sortBy=newest",
        "Extract all brand names from new food and beverage product listings",
    )
    if "extract_error" in content:
        content = parallel_search_text("target new food beverage brands 2026", 8)
    brands = _extract_brands_from_text(content, "Target")
    return brands if brands else [{"error": "No brand names extracted from Target"}]


def scrape_walmart_new_arrivals() -> list[dict[str, Any]]:
    """Discover new Walmart food/beverage brands via Parallel Search."""
    content = parallel_search_text("walmart new food beverage brands 2026 new arrivals", 8)
    brands = _extract_brands_from_text(content, "Walmart")
    return brands if brands else []


def scrape_sprouts_new_arrivals(brand_name: str = "") -> list[dict[str, Any]]:
    """Discover new Sprouts brands via Parallel Extract, with Search fallback."""
    if brand_name:
        results = _parallel_search_raw(f"{brand_name} sprouts", 8)
        content = " ".join(
            f"{r.title or ''} {' '.join(r.excerpts or [])}" for r in results
        )
        brands = _extract_brands_from_text(content, "Sprouts")
        sources = [r.url for r in results[:3]]
        for b in brands:
            b["source_urls"] = sources
        return brands or [{"error": f"No brands found for '{brand_name}' at Sprouts"}]

    content = parallel_extract(
        "https://www.sprouts.com/new-products/",
        "Extract all brand names from new product listings",
    )
    if "extract_error" in content:
        content = parallel_search_text("sprouts farmers market new products 2026", 8)
    brands = _extract_brands_from_text(content, "Sprouts")
    return brands if brands else [{"error": "No brand names extracted from Sprouts"}]


# ── Brand research ────────────────────────────────────────────────────────────

def scrape_brand_website(url: str) -> dict[str, Any]:
    """Extract brand signals with fallback chain for cart-template failures."""
    if not url:
        return {"error": "no_url_provided"}
    if not url.startswith("http"):
        url = "https://" + url
    base = url.rstrip("/")

    def _is_bad_extract(content: str) -> bool:
        if not content or len(content) < 200:
            return True
        bad_signals = ["cart", "checkout", "your bag", "shopping bag", "add to cart"]
        return sum(1 for s in bad_signals if s in content.lower()) >= 2

    objective = (
        "Extract: brand tagline and description, hero product name and format, "
        "target consumer, retail partners listed, all product names and prices, "
        "certifications (USDA Organic, Non-GMO, Keto, Paleo, B Corp, Gluten Free), "
        "subscription or DTC purchase option, Instagram handle, TikTok handle"
    )

    def _get_homepage() -> str:
        content = parallel_extract(base, objective)
        if _is_bad_extract(content):
            for path in ["/about", "/about-us", "/our-story", "/pages/about", "/pages/our-story"]:
                result = parallel_extract(base + path, objective)
                if not _is_bad_extract(result):
                    return result
            # All page extractions failed — fall back to search
            brand_slug = base.replace("https://", "").replace("http://", "").replace("www.", "").split(".")[0]
            return parallel_search_text(
                f'"{brand_slug}" brand story mission products certifications', 5
            )
        return content

    def _get_retail_page() -> str:
        for path in ["/pages/where-to-buy", "/stockists", "/where-to-buy", "/find-us"]:
            result = parallel_extract(
                base + path,
                "Extract all retailer names and store counts mentioned",
            )
            if not _is_bad_extract(result):
                return result[:1000]
        return ""

    with ThreadPoolExecutor(max_workers=2) as pool:
        hp_future = pool.submit(_get_homepage)
        rp_future = pool.submit(_get_retail_page)
        homepage    = hp_future.result()
        retail_page = rp_future.result()

    return {
        "homepage":    homepage[:3000],
        "retail_page": retail_page,
        "source":      "parallel_extract_website",
        "url":         base,
    }


def scrape_amazon_listing(brand_name: str) -> dict[str, Any]:
    """Get Amazon signals via targeted search queries — Amazon blocks direct extraction."""
    queries = {
        "reviews":   f"{brand_name} amazon.com reviews rating stars \"global ratings\"",
        "product":   f"{brand_name} amazon.com price subscribe save best seller rank",
        "presence":  f"site:amazon.com {brand_name} grocery snack",
    }
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(parallel_search_text, q, 4): k for k, q in queries.items()}
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    return {
        "review_data":   results.get("reviews", "")[:600],
        "product_data":  results.get("product", "")[:600],
        "presence_data": results.get("presence", "")[:400],
        "source":        "parallel_search_amazon",
        "brand":         brand_name,
    }


def scrape_faire_listing(brand_name: str) -> dict[str, Any]:
    """Extract Faire wholesale presence for a brand using Parallel Extract."""
    faire_url = f"https://www.faire.com/search?q={brand_name.replace(' ', '+')}"

    content = parallel_extract(
        faire_url,
        f"For brand {brand_name}: extract whether they have a Faire presence, "
        "wholesale price, minimum order quantity, reorder rate, number of retail doors, "
        "bestseller or trending badge, retailer reviews",
    )

    if "extract_error" in content:
        content = parallel_search_text(f"{brand_name} faire.com wholesale reorder rate", 3)

    return {
        "brand_name":  brand_name,
        "raw_content": content[:1500],
        "source":      "parallel_extract_faire",
    }


# ── Web search ────────────────────────────────────────────────────────────────

def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Run a Parallel web search.
    Returns list of result dicts with keys: title, url, content.
    (Normalised for backward compatibility with graph follow-up research nodes.)
    """
    raw = _parallel_search_raw(query, num_results=max_results)
    normalized = []
    for r in raw:
        normalized.append({
            "title":   r.title or "",
            "url":     r.url or "",
            "content": " ".join(r.excerpts or []),
        })
    return normalized


def search_velocity_signals(brand_name: str) -> dict[str, Any]:
    """Check Instacart via Extract, SPINS and Faire via search — in parallel."""
    def _instacart():
        return parallel_extract(
            f"https://www.instacart.com/store/s?k={brand_name.replace(' ', '+')}",
            f"For {brand_name}: which store banners carry this product, "
            "how many stores, is it available for delivery",
        )

    def _spins():
        return parallel_search_text(
            f"{brand_name} velocity SPINS NIQ scan data units per store", 3
        )

    def _faire():
        return parallel_search_text(
            f"{brand_name} faire.com wholesale reorder rate retailers", 3
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        fi = pool.submit(_instacart)
        fs = pool.submit(_spins)
        ff = pool.submit(_faire)
        instacart_raw = fi.result()
        spins_raw     = fs.result()
        faire_raw     = ff.result()

    return {
        "instacart":    instacart_raw[:1000],
        "spins_search": spins_raw[:500],
        "faire_search": faire_raw[:500],
        "source":       "mixed_extract_search",
    }


def search_press_and_story(brand_name: str) -> dict[str, Any]:
    """Search trade press, consumer press, social, and Expo — in parallel."""
    queries = {
        "trade":    f'"{brand_name}" site:nosh.com OR site:foodnavigator-usa.com OR site:grocerydive.com',
        "consumer": f'"{brand_name}" review OR featured OR "best" food beverage 2024 OR 2025 OR 2026',
        "social":   f'"{brand_name}" instagram followers OR tiktok followers OR social media',
        "expo":     f'"{brand_name}" expo west OR expo east OR natural products',
    }
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(parallel_search_text, q, 3): k for k, q in queries.items()}
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    social_text    = results.get("social", "")
    follower_match = re.search(r"([\d.,]+[Kk]?)\s*followers", social_text)
    return {
        "trade_press":    results.get("trade", "")[:800],
        "consumer_press": results.get("consumer", "")[:800],
        "social_signals": social_text[:500],
        "expo":           results.get("expo", "")[:300],
        "source":         "parallel_search_press",
    }


def search_funding_and_team(brand_name: str) -> dict[str, Any]:
    """Search for funding rounds and founder background — in parallel."""
    queries = {
        "funding": f'"{brand_name}" raised funding million seed series investment',
        "founder": f'"{brand_name}" founder CEO co-founder background story',
    }
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(parallel_search_text, q, 3): k for k, q in queries.items()}
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    return {
        "funding": results.get("funding", "")[:600],
        "founder": results.get("founder", "")[:600],
        "source":  "parallel_search_funding",
    }


# ── Founder contact ───────────────────────────────────────────────────────────

def find_founder_contact(brand_name: str, website_url: str = "") -> dict[str, str]:
    """
    Search for founder name and email via Parallel Search.
    Returns founder_name (best guess) and founder_email (blank if not found).
    """
    results = _parallel_search_raw(f"{brand_name} founder CEO name contact LinkedIn", 5)
    content = " ".join(
        f"{r.title or ''} {' '.join(r.excerpts or [])}" for r in results
    )

    founder_name = ""
    for pattern in [
        r"([A-Z][a-z]+ [A-Z][a-z]+),?\s+(?:founder|co-founder|ceo)",
        r"(?:founder|co-founder|ceo)[,\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
    ]:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            founder_name = m.group(1).strip()
            break

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", content)
    founder_email = email_match.group(0) if email_match else ""

    return {
        "founder_name":  founder_name or f"{brand_name} Founder",
        "founder_email": founder_email,
        "source":        "parallel_search",
        "raw_content":   content[:800],
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


# ── Quick SDK smoke test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Parallel Extract...")
    result = parallel_extract(
        "https://www.chomps.com",
        "Extract brand description, products, and retail partners",
    )
    print(result[:500])

    print("\nTesting Parallel Search...")
    result = parallel_search_text("Chomps meat snacks Amazon reviews rating")
    print(result[:500])
