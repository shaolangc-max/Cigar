#!/usr/bin/env python3
"""
Deep probe part 5: final cleanup
- cigars-of-cuba: /en/shop price structure
- tabaklaedeli: product rows div structure
- vipcigars: extract dataLayer items with price
- timecigar: product list endpoint + price element parent
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


# ─── cigars-of-cuba: /en/shop price + product structure ──────────────────────
print("\n" + "="*70)
print("cigars-of-cuba.com — /en/shop price structure")
print("="*70)
with make_client() as c:
    r = c.get("https://www.cigars-of-cuba.com/en/shop")
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"  status={r.status_code}  len={len(r.text)}")

    # Product card containers
    for selector in [".product-item", ".product_item", "[class*=product-card]", "[class*=product_card]"]:
        items = soup.select(selector)
        if items:
            print(f"  '{selector}': {len(items)} items")
            break

    # Find price containers
    price_boxes = soup.find_all(class_=re.compile(r"prices-box|price-box|price_box", re.I))
    print(f"\n  .prices-box count: {len(price_boxes)}")
    if price_boxes:
        print(f"  First prices-box HTML:\n{str(price_boxes[0])[:400]}")

    # price divs
    price_divs = soup.find_all(class_="price")
    print(f"\n  .price count: {len(price_divs)}")
    if price_divs:
        print(f"  First .price HTML:\n{str(price_divs[0])[:300]}")

    # Find a full product card
    # Look for a common ancestor of price + title
    price_el = price_boxes[0] if price_boxes else None
    if price_el:
        # Walk up to find product card
        parent = price_el.parent
        for _ in range(5):
            if parent is None:
                break
            classes = " ".join(parent.get("class", []))
            if "product" in classes.lower() or "item" in classes.lower() or "card" in classes.lower():
                print(f"\n  Product card ancestor: <{parent.name} class=\"{classes}\">")
                print(f"  HTML:\n{str(parent)[:1000]}")
                break
            parent = parent.parent

    # Also look for JSON-LD product data
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data[:2]:
                    print(f"  JSON-LD: {json.dumps(item)[:200]}")
            elif isinstance(data, dict):
                print(f"  JSON-LD: {json.dumps(data)[:200]}")
        except Exception:
            pass

    # Check if there's a JSON API
    r2 = c.get("https://www.cigars-of-cuba.com/en/shop.json?limit=3")
    print(f"\n  /en/shop.json: {r2.status_code}  ct={r2.headers.get('content-type','')[:40]}")
    if r2.status_code == 200 and "json" in r2.headers.get("content-type",""):
        print(f"  data: {r2.text[:300]}")

    # Check /en/cigars page
    r3 = c.get("https://www.cigars-of-cuba.com/en/cigars")
    soup3 = BeautifulSoup(r3.text, "html.parser")
    pb3 = soup3.find_all(class_=re.compile(r"prices-box|price-box", re.I))
    print(f"\n  /en/cigars prices-box count: {len(pb3)}")
    if pb3:
        # get a full product card from this page
        parent = pb3[0].parent
        for _ in range(5):
            if parent is None: break
            classes = " ".join(parent.get("class", []))
            if any(w in classes.lower() for w in ["product", "item", "card", "thumb"]):
                print(f"  Product card: <{parent.name} class=\"{classes}\">")
                print(f"  HTML:\n{str(parent)[:1000]}")
                break
            parent = parent.parent


# ─── tabaklaedeli: products row div structure ─────────────────────────────────
print("\n" + "="*70)
print("tabaklaedeli.ch — product row div structure")
print("="*70)
with make_client() as c:
    r = c.get("https://www.tabaklaedeli.ch/produkt-kategorie/zigarren/cuba/")
    soup = BeautifulSoup(r.text, "html.parser")

    # We know there are div.products rows
    prod_row = soup.find("div", class_=re.compile(r"\bproducts\b"))
    if prod_row:
        print(f"  Found .products div: class={' '.join(prod_row.get('class',[]))}")
        # Find children
        children = prod_row.find_all(recursive=False)
        print(f"  Direct children: {len(children)}")
        for child in children[:2]:
            print(f"  <{child.name} class=\"{' '.join(child.get('class',[]))}\"  id={child.get('id','?')}")
            price = child.find(class_=re.compile(r"price|amount", re.I))
            if price:
                print(f"    price: {price.get_text(strip=True)[:50]}")
        print(f"\n  Full first product HTML:\n{str(children[0])[:800] if children else 'NONE'}")

    # Also try to find product div-based cards (not li)
    product_divs_with_price = []
    for div in soup.find_all("div", class_=re.compile(r"\bproduct\b")):
        if div.find(class_=re.compile(r"price|amount")):
            product_divs_with_price.append(div)
    print(f"\n  div.product with price: {len(product_divs_with_price)}")
    if product_divs_with_price:
        el = product_divs_with_price[0]
        print(f"  First: <{el.name} class=\"{' '.join(el.get('class',''))}\">")
        print(f"  HTML:\n{str(el)[:800]}")

    # Check for WooCommerce's archive product list via AJAX
    r2 = c.get("https://www.tabaklaedeli.ch/produkt-kategorie/zigarren/cuba/?paged=1")
    print(f"\n  ?paged=1: {r2.status_code}  same_len={len(r.text)==len(r2.text)}")

    # Look at the product-wrapper classes in the HTML
    wrappers = soup.find_all(class_=re.compile(r"product-wrapper|product-inner|product-loop", re.I))
    print(f"  product-wrapper elements: {len(wrappers)}")
    if wrappers:
        print(f"  First wrapper HTML:\n{str(wrappers[0])[:600]}")


# ─── vipcigars: extract dataLayer GTM data ────────────────────────────────────
print("\n" + "="*70)
print("vipcigars.com — extract dataLayer items with price data")
print("="*70)
with make_client() as c:
    r = c.get("https://www.vipcigars.com/cuban-cigars/cohiba")
    html = r.text

    # Extract the dataLayer push with items
    dl_match = re.search(r'event:\s*"view_item_list".*?items:\s*(\[.*?\])\s*\}', html, re.DOTALL)
    if dl_match:
        items_str = dl_match.group(1)
        # try to parse it
        try:
            items = json.loads(items_str)
            print(f"  GTM items: {len(items)}")
            for item in items[:3]:
                print(f"  item: {json.dumps(item)[:200]}")
        except Exception as e:
            print(f"  Parse error: {e}")
            print(f"  Raw items (first 500):\n{items_str[:500]}")
    else:
        # Try broader match
        dl_matches = re.findall(r'dataLayer\.push\((\{.{50,2000}?\})\)', html, re.DOTALL)
        print(f"  dataLayer.push calls: {len(dl_matches)}")
        for m in dl_matches[:3]:
            if "item" in m.lower() or "price" in m.lower():
                print(f"  match: {m[:300]}")

    # Try to find the actual product list rendered in HTML
    soup = BeautifulSoup(html, "html.parser")
    # The catalog ul has dropdown items, but the actual products should be below
    # look for div/section with many anchor children leading to product pages
    links_to_products = [a for a in soup.find_all("a", href=re.compile(r"/cuban-cigars/cohiba/"))]
    print(f"\n  Links to cohiba product pages: {len(links_to_products)}")
    if links_to_products:
        print(f"  First few: {[a['href'] for a in links_to_products[:5]]}")

    # Check a single product page for price
    r2 = c.get("https://www.vipcigars.com/cuban-cigars/cohiba/cohiba-behike-bhk-52")
    s2 = BeautifulSoup(r2.text, "html.parser")
    print(f"\n  Product page: {r2.status_code}")
    # Find structured price data
    price_els = s2.find_all(class_=re.compile(r"price|amount", re.I))
    print(f"  Price elements: {len(price_els)}")
    for el in price_els[:5]:
        print(f"  <{el.name} class=\"{' '.join(el.get('class',[]))}\"> = {el.get_text(strip=True)[:60]}")

    # Check itemprop
    itemprop = s2.find_all(attrs={"itemprop": True})
    pricedata = [(el.get("itemprop"), el.get("content"), el.get_text(strip=True)[:30]) for el in itemprop
                 if "price" in str(el.get("itemprop","")).lower() or "offer" in str(el.get("itemprop","")).lower()]
    print(f"  itemprop price/offer: {pricedata}")

    # dataLayer on PDP
    dl_pdp = re.search(r'event:\s*"view_item".*?price["\s]*:["\s]*([\d.]+)', r2.text, re.DOTALL)
    if dl_pdp:
        print(f"  GTM price on PDP: {dl_pdp.group(1)}")
    else:
        # broad price search in scripts
        prices = re.findall(r'"price"\s*:\s*"?([\d.]+)"?', r2.text)
        print(f"  'price' in page scripts: {prices[:5]}")

    # check JSON-LD on PDP
    for script in s2.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            print(f"  JSON-LD on PDP: {json.dumps(data)[:300]}")
        except Exception:
            pass


# ─── timecigar: find product list API ────────────────────────────────────────
print("\n" + "="*70)
print("timecigar.com — find product list API from App.bundle.js")
print("="*70)
with make_client() as c:
    r = c.get("https://www.timecigar.com/web/dist/App.bundle.js?214")
    js = r.text

    # Look for fetch/axios calls with product paths
    api_calls = re.findall(r'(?:fetch|axios|get|post)\(["\`]([^"\'`]+)["\`]', js)
    print(f"  API call patterns ({len(api_calls)}):")
    for call in api_calls[:20]:
        print(f"    {call}")

    # Look for route/path patterns
    routes = re.findall(r'["\'](/(?:api|webapi|v\d)/[^"\']+)["\']', js)
    print(f"\n  Route patterns:")
    for r_p in sorted(set(routes))[:20]:
        print(f"    {r_p}")

    # Look for product_list or catalog API
    product_apis = re.findall(r'["\']([^"\']*(?:product|catalog|item)[^"\']*(?:list|search|index)[^"\']*)["\']', js, re.I)
    print(f"\n  Product API patterns: {product_apis[:10]}")

print("\nDONE")
