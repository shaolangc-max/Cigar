#!/usr/bin/env python3
"""
Deep probe part 3: remaining gaps
- tabaklaedeli: correct URL is /produkt-kategorie/zigarren/cuba/
- vipcigars: find actual product item DOM structure (CF passes HTML)
- timecigar: look at App.bundle.js for API base URL
- montefortuna: extract price selectors on shop page
- hitcigars: extract any product data from CF-obfuscated page
- cigars-of-cuba: find real product URL structure
"""

import httpx, os, re, json
from bs4 import BeautifulSoup

for _v in ("ALL_PROXY","all_proxy","HTTP_PROXY","http_proxy","HTTPS_PROXY","https_proxy"):
    os.environ.pop(_v, None)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def make_client():
    return httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True,
                        transport=httpx.HTTPTransport(retries=1))


# ─── tabaklaedeli: correct URL /produkt-kategorie/zigarren/cuba/ ──────────────
print("\n" + "="*70)
print("tabaklaedeli.ch — /produkt-kategorie/zigarren/cuba/")
print("="*70)
with make_client() as c:
    r = c.get("https://www.tabaklaedeli.ch/produkt-kategorie/zigarren/cuba/")
    print(f"  status={r.status_code}  url={r.url}")
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("title")
    print(f"  title: {title.get_text(strip=True)[:80] if title else '?'}")

    # All product li items
    woo_cards = [p for p in soup.find_all("li", class_=re.compile(r"\bproduct\b"))
                 if "menu-item" not in " ".join(p.get("class",[]))]
    print(f"  WooCommerce product cards: {len(woo_cards)}")
    for card in woo_cards[:3]:
        name_el = card.find(class_=re.compile(r"woocommerce-loop-product__title|product.?title"))
        price_el = card.find(class_=re.compile(r"\bprice\b"))
        link_el = card.find("a", href=True)
        if name_el: print(f"  Name: {name_el.get_text(strip=True)[:60]}")
        if price_el:
            print(f"  Price class: {' '.join(price_el.get('class',[]))}  text: {price_el.get_text(strip=True)[:60]}")
            # get woocommerce-Price-amount
            amount_el = price_el.find(class_=re.compile(r"woocommerce-Price-amount|amount"))
            if amount_el:
                print(f"  Amount el: <{amount_el.name} class=\"{' '.join(amount_el.get('class',[]))}\">"
                      f"  content={amount_el.get('content')}  text={amount_el.get_text(strip=True)[:30]}")
        if link_el: print(f"  URL: {link_el['href']}")
        print()

    if woo_cards:
        print(f"  First card raw HTML:\n{str(woo_cards[0])[:1000]}")


# ─── vipcigars: find product item DOM ────────────────────────────────────────
print("\n" + "="*70)
print("vipcigars.com — decode product item structure")
print("="*70)
with make_client() as c:
    r = c.get("https://www.vipcigars.com/cuban-cigars/cohiba")
    print(f"  status={r.status_code}  url={r.url}")
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("title")
    print(f"  title: {title.get_text(strip=True)[:80] if title else '?'}")
    print(f"  page len: {len(r.text)}")

    # Tailwind-based custom platform (bg-gray-300, catalog, dropdown, etc.)
    # Try to find product article or div with price-related content
    # scan for CHF / EUR patterns in the text
    price_pattern = re.findall(r'(?:CHF|EUR|USD|HKD)\s*[\d,]+\.?\d*', r.text)
    print(f"  Currency+price patterns: {price_pattern[:10]}")

    # itemprop
    micro_prices = soup.find_all(attrs={"itemprop": "price"})
    print(f"  itemprop=price: {len(micro_prices)}")
    for el in micro_prices[:3]:
        print(f"  {el}")

    # find data-product or similar
    data_attrs = []
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            if "product" in str(attr).lower() and "data-" in str(attr):
                data_attrs.append((tag.name, attr, str(tag.get(attr))[:60]))
    print(f"  data-product attrs: {data_attrs[:5]}")

    # Check for JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            print(f"  JSON-LD type={data.get('@type')} name={data.get('name','?')[:40]}")
            if "offers" in data:
                print(f"  offers: {data['offers']}")
        except Exception:
            pass

    # grab the catalog ul's children
    catalog = soup.find("ul", class_="catalog")
    if catalog:
        items = catalog.find_all("li", recursive=False)
        print(f"\n  catalog <ul> has {len(items)} direct <li> children")
        if items:
            # first non-dropdown item
            for item in items[:3]:
                classes = " ".join(item.get("class",[]))
                text = item.get_text(" ", strip=True)[:100]
                print(f"  <li class=\"{classes}\"> text: {text}")

    # look for a product listing at a sub-brand
    r2 = c.get("https://www.vipcigars.com/cuban-cigars/cohiba/cohiba-siglo-i")
    print(f"\n  Product detail page: status={r2.status_code} url={r2.url}")
    soup2 = BeautifulSoup(r2.text, "html.parser")
    # find price on PDP
    for el in soup2.find_all(class_=re.compile(r"price|amount", re.I))[:5]:
        print(f"  <{el.name} class=\"{' '.join(el.get('class',[]))}\"> = {el.get_text(strip=True)[:60]}")
    prices2 = re.findall(r'(?:CHF|EUR|USD|HKD|Fr\.)\s*[\d,]+\.?\d*', r2.text)
    print(f"  Prices on PDP: {prices2[:10]}")
    for script in soup2.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            print(f"  JSON-LD: {json.dumps(data)[:300]}")
        except Exception:
            pass


# ─── timecigar: probe App.bundle.js for API ───────────────────────────────────
print("\n" + "="*70)
print("timecigar.com — check App.bundle.js for API base URL")
print("="*70)
with make_client() as c:
    r = c.get("https://www.timecigar.com/web/dist/App.bundle.js?214")
    print(f"  status={r.status_code}  len={len(r.text)}")
    # Find API URL patterns
    api_matches = re.findall(r'["\'](?:https?://[^"\']+api[^"\']*|/api/[^"\']+)["\']', r.text)
    print(f"  API url patterns: {api_matches[:10]}")
    # baseURL patterns
    base_matches = re.findall(r'baseURL?\s*[=:]\s*["\']([^"\']+)["\']', r.text)
    print(f"  baseURL patterns: {base_matches[:5]}")
    # endpoint patterns
    endpoint_matches = re.findall(r'(?:endpoint|apiUrl|api_url)\s*[=:]\s*["\']([^"\']+)["\']', r.text)
    print(f"  endpoint patterns: {endpoint_matches[:5]}")
    # Look for product-list related endpoints
    prod_endpoints = re.findall(r'["\']([^"\']*product[^"\']*)["\']', r.text)
    print(f"  Product endpoint patterns: {prod_endpoints[:10]}")


# ─── montefortuna: shop page price structure ─────────────────────────────────
print("\n" + "="*70)
print("montefortuna.com — shop page price DOM")
print("="*70)
with make_client() as c:
    r = c.get("https://www.montefortunacigars.com/shop/")
    soup = BeautifulSoup(r.text, "html.parser")
    woo_cards = [p for p in soup.find_all("li", class_=re.compile(r"\bproduct\b"))
                 if "menu-item" not in " ".join(p.get("class",[]))]
    print(f"  Products: {len(woo_cards)}  CF={is_cf(r.text)}")
    for card in woo_cards[:2]:
        name_el = card.find(class_=re.compile(r"woocommerce-loop-product__title|product.?title"))
        price_el = card.find(class_=re.compile(r"\bprice\b"))
        if name_el: print(f"  Name: {name_el.get_text(strip=True)[:60]}")
        if price_el:
            print(f"  Price class: {' '.join(price_el.get('class',[]))}")
            print(f"  Price text: {price_el.get_text(strip=True)[:80]}")
            amount = price_el.find(class_=re.compile(r"woocommerce-Price-amount|amount"))
            if amount:
                print(f"  Amount: <{amount.name} class=\"{' '.join(amount.get('class',[]))}\"> = {amount.get_text(strip=True)}")
        print()
    if woo_cards:
        print(f"  First card:\n{str(woo_cards[0])[:800]}")


def is_cf(html):
    return any(p.lower() in html.lower() for p in ["cloudflare","just a moment","cf_clearance"])


# ─── cigars-of-cuba: find real URL structure ──────────────────────────────────
print("\n" + "="*70)
print("cigars-of-cuba.com — find real Cuban cigars listing URL")
print("="*70)
with make_client() as c:
    # Try different potential URL structures
    for url in [
        "https://www.cigars-of-cuba.com/en/",
        "https://www.cigars-of-cuba.com/en/shop",
        "https://www.cigars-of-cuba.com/en/habanos",
        "https://www.cigars-of-cuba.com/en/cuban",
    ]:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        price_els = soup.find_all(class_=re.compile(r"price|amount|preis", re.I))
        print(f"  {url} → [{r.status_code}] title={title.get_text(strip=True)[:50] if title else '?'} price_els={len(price_els)}")

    # Homepage to find nav links
    r_home = c.get("https://www.cigars-of-cuba.com/en/")
    soup_home = BeautifulSoup(r_home.text, "html.parser")
    # all nav links
    nav = soup_home.find("nav")
    if nav:
        links = [(a.get_text(strip=True), a["href"]) for a in nav.find_all("a", href=True)][:20]
        print(f"\n  Nav links: {links}")
    # find price structure on homepage
    price_els = soup_home.find_all(class_=re.compile(r"price|amount", re.I))
    print(f"\n  Price elements on homepage: {len(price_els)}")
    for el in price_els[:5]:
        print(f"  <{el.name} class=\"{' '.join(el.get('class',[]))}\"> = {el.get_text(strip=True)[:50]}")
    if price_els:
        print(f"\n  First price el raw:\n{str(price_els[0])[:400]}")

print("\nDONE")
