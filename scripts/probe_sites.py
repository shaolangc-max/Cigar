#!/usr/bin/env python3
"""
Probe cigar websites for HTML structure, price selectors, and Shopify detection.
Explicitly bypasses any system proxy (ALL_PROXY etc.) by passing proxies=None / transport without proxy.
"""

import httpx
import os
import re
from bs4 import BeautifulSoup

# ---- clear proxy env vars so httpx doesn't pick them up --------------------
for _v in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
           "HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy"):
    os.environ.pop(_v, None)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SITES = [
    {
        "name": "cigars-of-cuba (COC, CHF/EUR)",
        "main": "https://www.cigars-of-cuba.com/en/cuban-cigars",
        "shopify_api": "https://www.cigars-of-cuba.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "vipcigars (VIP, CHF)",
        "main": "https://www.vipcigars.com",
        "shopify_api": "https://www.vipcigars.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "cigarshopworld (ESP, EUR)",
        "main": "https://cigarshopworld.com/cuban-cigars",
        "shopify_api": "https://cigarshopworld.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "egmcigars (GEO-2, USD)",
        "main": "https://egmcigars.com",
        "shopify_api": "https://egmcigars.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "hitcigars (GEO-1, USD)",
        "main": "https://hitcigars.com",
        "shopify_api": "https://hitcigars.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "thecigar (EUR)",
        "main": "https://thecigar.com/cigars/cuban-cigars",
        "shopify_api": "https://thecigar.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "tabaklaedeli (CHF)",
        "main": "https://www.tabaklaedeli.ch/zigarren/kuba",
        "shopify_api": "https://www.tabaklaedeli.ch/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "montefortuna (EUR)",
        "main": "https://www.montefortunacigars.com/cuban-cigars",
        "shopify_api": "https://www.montefortunacigars.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "hyhpuro (HP, HKD)",
        "main": "https://hyhpuro.com",
        "shopify_api": "https://hyhpuro.com/collections/cuban-cigars/products.json?limit=5",
    },
    {
        "name": "timecigar (SO, HKD)",
        "main": "https://www.timecigar.com",
        "shopify_api": "https://www.timecigar.com/collections/cuban-cigars/products.json?limit=5",
    },
]

# Price-related patterns to search for in HTML
PRICE_PATTERNS = [
    r'class=["\'][^"\']*price[^"\']*["\']',
    r'data-[^=]*price[^=]*=',
    r'itemprop=["\']price["\']',
    r'class=["\'][^"\']*amount[^"\']*["\']',
    r'class=["\'][^"\']*cost[^"\']*["\']',
    r'class=["\'][^"\']*preis[^"\']*["\']',   # German
    r'class=["\'][^"\']*prix[^"\']*["\']',    # French
]

CLOUDFLARE_PATTERNS = [
    "cloudflare", "cf-browser-verification", "cf_clearance",
    "challenge-platform", "Checking your browser", "DDoS protection by"
]


def detect_cloudflare(text: str) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in CLOUDFLARE_PATTERNS)


def detect_js_challenge(text: str) -> bool:
    indicators = [
        "enable javascript", "javascript is required",
        "please enable js", "browser check", "human verification",
        "__NEXT_DATA__", "window.__reactRouterManifest",  # SPA shell
    ]
    lower = text.lower()
    return sum(1 for i in indicators if i.lower() in lower) >= 2


def extract_price_snippets(html: str, soup: BeautifulSoup) -> list[str]:
    snippets = []
    # 1. regex scan
    for pat in PRICE_PATTERNS:
        matches = re.findall(pat, html, re.IGNORECASE)
        snippets.extend(matches[:3])
    # 2. BeautifulSoup: elements with "price" in class
    for tag in soup.find_all(class_=re.compile(r"price|amount|preis|prix", re.I))[:5]:
        cls = " ".join(tag.get("class", []))
        snippets.append(f"<{tag.name} class=\"{cls}\">")
    # 3. itemprop price
    for tag in soup.find_all(attrs={"itemprop": "price"})[:3]:
        snippets.append(str(tag)[:120])
    # 4. data-price
    for tag in soup.find_all(attrs=lambda k, v: k and "price" in k.lower() and v)[:3]:
        attrs = {k: v for k, v in tag.attrs.items() if "price" in k.lower()}
        snippets.append(f"<{tag.name} {attrs}>")
    return list(dict.fromkeys(snippets))  # deduplicate preserving order


def probe_site(site: dict) -> None:
    name = site["name"]
    print(f"\n{'='*70}")
    print(f"SITE: {name}")
    print(f"{'='*70}")

    transport = httpx.HTTPTransport(retries=1)
    with httpx.Client(
        headers=HEADERS,
        timeout=15,
        follow_redirects=True,
        transport=transport,
    ) as client:

        # --- Main page ---
        print(f"\n[MAIN PAGE] {site['main']}")
        try:
            r = client.get(site["main"])
            print(f"  Status : {r.status_code}")
            print(f"  Final URL: {r.url}")
            print(f"  Content-Type: {r.headers.get('content-type', 'n/a')}")
            html = r.text
            is_cf = detect_cloudflare(html)
            is_js = detect_js_challenge(html)
            print(f"  Cloudflare challenge: {is_cf}")
            print(f"  JS-only shell: {is_js}")

            # Shopify detection via meta generator or CDN asset
            is_shopify_meta = "shopify" in html.lower()
            is_shopify_cdn = "cdn.shopify.com" in html
            print(f"  Shopify signals: meta={is_shopify_meta}, cdn={is_shopify_cdn}")

            soup = BeautifulSoup(html, "html.parser")

            # Page title
            title_tag = soup.find("title")
            print(f"  Page title: {title_tag.get_text(strip=True)[:80] if title_tag else 'N/A'}")

            # Price snippets
            price_snippets = extract_price_snippets(html, soup)
            if price_snippets:
                print(f"  Price selectors found:")
                for s in price_snippets[:8]:
                    print(f"    • {s[:120]}")
            else:
                print("  No price selectors found in HTML")

            # Body text snippet (first 300 chars of visible text)
            body = soup.find("body")
            if body:
                visible = " ".join(body.get_text(" ", strip=True).split())[:300]
                print(f"  Visible text (first 300): {visible}")

        except Exception as e:
            print(f"  ERROR: {e}")

        # --- Shopify products.json ---
        print(f"\n[SHOPIFY API] {site['shopify_api']}")
        try:
            r2 = client.get(site["shopify_api"])
            print(f"  Status: {r2.status_code}")
            if r2.status_code == 200:
                ct = r2.headers.get("content-type", "")
                print(f"  Content-Type: {ct}")
                if "json" in ct or r2.text.strip().startswith("{"):
                    data = r2.json()
                    products = data.get("products", [])
                    print(f"  Products returned: {len(products)}")
                    if products:
                        p = products[0]
                        print(f"  First product: {p.get('title', '?')}")
                        variants = p.get("variants", [])
                        if variants:
                            v = variants[0]
                            print(f"    price={v.get('price')}, compare_at={v.get('compare_at_price')}")
                else:
                    print(f"  Non-JSON response (first 200 chars): {r2.text[:200]}")
            elif r2.status_code == 404:
                print("  → 404 (not Shopify or collection doesn't exist)")
            else:
                print(f"  → {r2.status_code}")
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    for site in SITES:
        probe_site(site)
    print(f"\n{'='*70}")
    print("DONE")
