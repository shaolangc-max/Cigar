#!/usr/bin/env python3
"""
Probe cigar websites for HTML structure, price selectors, and Shopify detection.
Round 2 — fixed lambda bug, deeper price analysis per site.
"""

import httpx
import os
import re
import json
from bs4 import BeautifulSoup

# clear proxy env vars
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
        "products_json_alt": "https://www.cigars-of-cuba.com/en/cuban-cigars.json",
    },
    {
        "name": "vipcigars (VIP, CHF)",
        "main": "https://www.vipcigars.com",
        "shopify_api": "https://www.vipcigars.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": None,
    },
    {
        "name": "cigarshopworld (ESP, EUR)",
        "main": "https://cigarshopworld.com/cuban-cigars",
        "shopify_api": "https://cigarshopworld.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": "https://cigarshopworld.com/wp-json/wc/v3/products?category=cuban-cigars&per_page=5",
    },
    {
        "name": "egmcigars (GEO-2, USD)",
        "main": "https://egmcigars.com",
        "shopify_api": "https://egmcigars.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": "https://egmcigars.com/collections/all/products.json?limit=5",
    },
    {
        "name": "hitcigars (GEO-1, USD)",
        "main": "https://hitcigars.com",
        "shopify_api": "https://hitcigars.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": "https://hitcigars.com/products.json?limit=5",
    },
    {
        "name": "thecigar (EUR)",
        "main": "https://thecigar.com/cigars/cuban-cigars",
        "shopify_api": "https://thecigar.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": None,
    },
    {
        "name": "tabaklaedeli (CHF)",
        "main": "https://www.tabaklaedeli.ch/zigarren/kuba",
        "shopify_api": "https://www.tabaklaedeli.ch/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": "https://www.tabaklaedeli.ch/wp-json/wc/v3/products?per_page=5",
    },
    {
        "name": "montefortuna (EUR)",
        "main": "https://www.montefortunacigars.com/cuban-cigars",
        "shopify_api": "https://www.montefortunacigars.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": "https://www.montefortunacigars.com/wp-json/wc/v3/products?per_page=5",
    },
    {
        "name": "hyhpuro (HP, HKD)",
        "main": "https://hyhpuro.com",
        "shopify_api": "https://hyhpuro.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": None,
    },
    {
        "name": "timecigar (SO, HKD)",
        "main": "https://www.timecigar.com",
        "shopify_api": "https://www.timecigar.com/collections/cuban-cigars/products.json?limit=5",
        "products_json_alt": None,
    },
]

CF_SIGNALS = ["cloudflare", "cf-browser-verification", "cf_clearance",
              "challenge-platform", "Checking your browser", "DDoS protection by",
              "Just a moment"]


def is_cf(html: str) -> bool:
    lower = html.lower()
    return any(p.lower() in lower for p in CF_SIGNALS)


def find_price_selectors(html: str, soup: BeautifulSoup) -> list[str]:
    results = []
    # 1. class attrs containing price/amount/preis/prix/kosten
    for tag in soup.find_all(True):
        classes = tag.get("class", [])
        if isinstance(classes, list):
            class_str = " ".join(classes)
        else:
            class_str = str(classes)
        if re.search(r"price|amount|preis|prix|kosten|tarif|cost", class_str, re.I):
            results.append(f"<{tag.name} class=\"{class_str}\">  text={tag.get_text(strip=True)[:60]}")
            if len(results) >= 10:
                break

    # 2. itemprop price
    for tag in soup.find_all(attrs={"itemprop": "price"}):
        results.append(f"itemprop=price: <{tag.name}> content={tag.get('content')} text={tag.get_text(strip=True)[:60]}")

    # 3. data-price attrs (fixed: use dict comprehension, not lambda)
    for tag in soup.find_all(True):
        data_prices = {k: v for k, v in tag.attrs.items() if isinstance(k, str) and "price" in k.lower()}
        if data_prices:
            results.append(f"data-price on <{tag.name}>: {data_prices}")
            if len(results) >= 15:
                break

    return list(dict.fromkeys(results))[:12]


def detect_platform(html: str) -> str:
    h = html.lower()
    if "cdn.shopify.com" in h or "shopify.com" in h:
        return "Shopify"
    if "woocommerce" in h or "wp-content/plugins/woocommerce" in h:
        return "WooCommerce/WordPress"
    if "prestashop" in h or "presta" in h:
        return "PrestaShop"
    if "magento" in h or "mage/cookies" in h:
        return "Magento"
    if "opencart" in h:
        return "OpenCart"
    if "drupal" in h:
        return "Drupal"
    return "Unknown"


def probe_main(client: httpx.Client, url: str) -> dict:
    result = {"url": url, "status": None, "final_url": None, "platform": None,
              "cf": False, "title": None, "price_selectors": [], "html_snippet": "", "error": None}
    try:
        r = client.get(url)
        result["status"] = r.status_code
        result["final_url"] = str(r.url)
        html = r.text
        result["cf"] = is_cf(html)
        result["platform"] = detect_platform(html)
        soup = BeautifulSoup(html, "html.parser")
        t = soup.find("title")
        result["title"] = t.get_text(strip=True)[:80] if t else None
        result["price_selectors"] = find_price_selectors(html, soup)
        # grab first product card snippet
        card = soup.find(class_=re.compile(r"product.?card|product.?item|product.?tile|wc-block-grid__product", re.I))
        if card:
            result["html_snippet"] = str(card)[:600]
    except Exception as e:
        result["error"] = str(e)
    return result


def probe_json(client: httpx.Client, url: str, label: str) -> dict:
    result = {"label": label, "url": url, "status": None, "is_json": False, "data": None, "error": None}
    try:
        r = client.get(url)
        result["status"] = r.status_code
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            text = r.text.strip()
            if "json" in ct or text.startswith("{") or text.startswith("["):
                result["is_json"] = True
                try:
                    result["data"] = r.json()
                except Exception:
                    result["data"] = text[:300]
    except Exception as e:
        result["error"] = str(e)
    return result


def print_site(site: dict) -> None:
    name = site["name"]
    print(f"\n{'='*72}")
    print(f"  {name}")
    print(f"{'='*72}")

    transport = httpx.HTTPTransport(retries=1)
    with httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True, transport=transport) as client:

        # Main page
        m = probe_main(client, site["main"])
        print(f"\n[MAIN] {site['main']}")
        print(f"  HTTP {m['status']} → {m['final_url']}")
        print(f"  Platform : {m['platform']}")
        print(f"  Cloudflare blocked : {m['cf']}")
        print(f"  Title    : {m['title']}")
        if m["error"]:
            print(f"  ERROR    : {m['error']}")
        if m["price_selectors"]:
            print("  Price selectors:")
            for s in m["price_selectors"]:
                print(f"    » {s}")
        else:
            print("  Price selectors: NONE FOUND")
        if m["html_snippet"]:
            print(f"  Product card HTML (first 600):\n{m['html_snippet']}")

        # Shopify products.json
        j1 = probe_json(client, site["shopify_api"], "Shopify /products.json")
        print(f"\n[SHOPIFY API] {j1['url']}")
        print(f"  HTTP {j1['status']}  is_json={j1['is_json']}")
        if j1["is_json"] and isinstance(j1["data"], dict):
            prods = j1["data"].get("products", [])
            print(f"  products count: {len(prods)}")
            if prods:
                p0 = prods[0]
                print(f"  [0] title={p0.get('title')}  handle={p0.get('handle')}")
                if p0.get("variants"):
                    v = p0["variants"][0]
                    print(f"      price={v.get('price')}  compare_at={v.get('compare_at_price')}")
        elif j1["error"]:
            print(f"  ERROR: {j1['error']}")

        # Alt API
        if site.get("products_json_alt"):
            j2 = probe_json(client, site["products_json_alt"], "alt API")
            print(f"\n[ALT API] {j2['url']}")
            print(f"  HTTP {j2['status']}  is_json={j2['is_json']}")
            if j2["is_json"] and j2["data"]:
                print(f"  Data snippet: {str(j2['data'])[:300]}")
            elif j2["error"]:
                print(f"  ERROR: {j2['error']}")


if __name__ == "__main__":
    for site in SITES:
        print_site(site)
    print(f"\n{'='*72}")
    print("DONE")
