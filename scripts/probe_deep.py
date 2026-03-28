#!/usr/bin/env python3
"""
Deep probe on sites that returned real HTML: extract product list structure.
"""

import httpx, os, re
from bs4 import BeautifulSoup

for _v in ("ALL_PROXY","all_proxy","HTTP_PROXY","http_proxy","HTTPS_PROXY","https_proxy"):
    os.environ.pop(_v, None)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def client():
    return httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True,
                        transport=httpx.HTTPTransport(retries=1))


# ─── cigarshopworld ───────────────────────────────────────────────────────────
print("\n" + "="*70)
print("cigarshopworld.com  (WooCommerce, EUR)")
print("="*70)
with client() as c:
    r = c.get("https://cigarshopworld.com/cuban-cigars")
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"  Final URL: {r.url}  status={r.status_code}")
    # WooCommerce product cards
    products = soup.find_all("li", class_=re.compile(r"product"))[:3]
    print(f"  <li class=product> count: {len(products)}")
    for p in products[:2]:
        print(f"\n  Product card classes: {p.get('class')}")
        price_el = p.find(class_=re.compile(r"price"))
        if price_el:
            print(f"  Price element: <{price_el.name} class=\"{' '.join(price_el.get('class', []))}\">")
            print(f"  Price text: {price_el.get_text(strip=True)[:80]}")
        name_el = p.find(class_=re.compile(r"product.*title|woocommerce-loop-product__title"))
        if name_el:
            print(f"  Name: {name_el.get_text(strip=True)[:60]}")
        link = p.find("a", href=True)
        if link:
            print(f"  Link: {link['href']}")
    # Full raw HTML of first product card
    if products:
        print(f"\n  First product card raw HTML:\n{str(products[0])[:800]}")


# ─── tabaklaedeli ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("tabaklaedeli.ch  (WooCommerce, CHF)  — redirected to homepage; try direct category")
print("="*70)
with client() as c:
    # Try various possible URLs
    for url in [
        "https://www.tabaklaedeli.ch/zigarren/kuba/",
        "https://www.tabaklaedeli.ch/product-category/zigarren/kuba/",
        "https://www.tabaklaedeli.ch/?product_cat=kuba",
        "https://www.tabaklaedeli.ch/shop/?product_cat=kuba",
    ]:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        products = soup.find_all("li", class_=re.compile(r"product"))
        print(f"  {url} → {r.url} [{r.status_code}] title={title.get_text(strip=True)[:60] if title else '?'} products={len(products)}")
        if products:
            # show price structure
            for p in products[:2]:
                price_el = p.find(class_=re.compile(r"price|amount"))
                if price_el:
                    print(f"    price class: {' '.join(price_el.get('class', []))}  text: {price_el.get_text(strip=True)[:60]}")
            print(f"\n  First card HTML:\n{str(products[0])[:800]}")
            break


# ─── egmcigars — deep Shopify product page ────────────────────────────────────
print("\n" + "="*70)
print("egmcigars.com  (Shopify, CHF/USD)  — category page")
print("="*70)
with client() as c:
    # Try some collections that might contain Cuban cigars
    for url in [
        "https://egmcigars.com/collections/cuban-cigars",
        "https://egmcigars.com/collections/habanos",
        "https://egmcigars.com/collections/cigars",
        "https://egmcigars.com/collections/all",
    ]:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        # Shopify product cards
        cards = soup.find_all(class_=re.compile(r"product.?card|product.?item|grid.?item", re.I))
        print(f"  {url} → [{r.status_code}] title={title.get_text(strip=True)[:60] if title else '?'} cards={len(cards)}")
        if cards:
            # show first card with price
            for card in cards[:2]:
                price = card.find(class_=re.compile(r"price|amount", re.I))
                name = card.find(class_=re.compile(r"product.?title|card.?title", re.I))
                if price or name:
                    print(f"    name={name.get_text(strip=True)[:50] if name else '?'} price={price.get_text(strip=True)[:30] if price else '?'}")
            print(f"\n  First card raw HTML:\n{str(cards[0])[:800]}")
            break

    # Shopify products.json for /collections/all
    r2 = c.get("https://egmcigars.com/collections/all/products.json?limit=3")
    if r2.status_code == 200:
        try:
            data = r2.json()
            prods = data.get("products", [])
            print(f"\n  /collections/all/products.json → {len(prods)} products")
            if prods:
                p = prods[0]
                v = p["variants"][0] if p.get("variants") else {}
                print(f"  [0] title={p['title']}  price={v.get('price')}  currency hint from price")
        except Exception as e:
            print(f"  JSON parse error: {e}")


# ─── timecigar ────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("timecigar.com  (HKD)  — category page")
print("="*70)
with client() as c:
    for url in [
        "https://www.timecigar.com/tc",
        "https://www.timecigar.com/tc/products",
        "https://www.timecigar.com/tc/collection/cuban",
        "https://www.timecigar.com/tc/collection/all",
    ]:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        # look for price containers
        price_els = soup.find_all(class_=re.compile(r"price", re.I))
        product_items = soup.find_all(class_=re.compile(r"product.?item|product.?card", re.I))
        print(f"\n  {url} → {r.url} [{r.status_code}] title={title.get_text(strip=True)[:60] if title else '?'}")
        print(f"    price elements={len(price_els)}  product items={len(product_items)}")
        if price_els:
            for el in price_els[:3]:
                print(f"    <{el.name} class=\"{' '.join(el.get('class',[]))}\"> text={el.get_text(strip=True)[:50]}")

    # Also grab the TC homepage raw HTML around price section
    r = c.get("https://www.timecigar.com/tc")
    # find JSON-LD or window.__data
    scripts = soup.find_all("script", type=re.compile(r"application/ld\+json|json", re.I))
    print(f"\n  JSON-LD scripts: {len(scripts)}")
    for s in scripts[:2]:
        txt = s.get_text(strip=True)[:300]
        print(f"  {txt}")
    # look for API base patterns
    api_pats = re.findall(r'(api[A-Za-z/_\-]*url["\s]*:["\s]*["\']([^"\']+)["\'])', r.text)
    print(f"  API url patterns found: {api_pats[:5]}")

    # Try TC products API
    for api_url in [
        "https://www.timecigar.com/tc/api/products?limit=5",
        "https://www.timecigar.com/api/products?limit=5",
        "https://www.timecigar.com/tc/products.json",
    ]:
        try:
            r2 = c.get(api_url)
            print(f"\n  {api_url} → {r2.status_code}  ct={r2.headers.get('content-type','?')[:40]}")
            if r2.status_code == 200 and "json" in r2.headers.get("content-type",""):
                print(f"  data: {r2.text[:300]}")
        except Exception as e:
            print(f"  {api_url} ERROR: {e}")


# ─── vipcigars — deeper look (it passed CF but returned HTML) ─────────────────
print("\n" + "="*70)
print("vipcigars.com  (CHF)  — deeper inspection")
print("="*70)
with client() as c:
    r = c.get("https://www.vipcigars.com")
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    print(f"  status={r.status_code}  len={len(html)}")
    # look for platform clues
    for hint in ["prestashop","opencart","woocommerce","magento","joomla","drupal"]:
        if hint in html.lower():
            print(f"  Platform hint: {hint}")
    # price-like classes
    for tag in soup.find_all(class_=re.compile(r"price|prix|amount|preis", re.I))[:5]:
        print(f"  <{tag.name} class=\"{' '.join(tag.get('class',[]))}\"> text={tag.get_text(strip=True)[:60]}")
    # check for specific cuban section
    links = [a["href"] for a in soup.find_all("a", href=re.compile(r"cuba|habana|havana", re.I))][:10]
    print(f"  Cuban-related links: {links}")
    # raw html snippet
    print(f"\n  HTML around 'price' (first match):")
    idx = html.lower().find("price")
    if idx > 0:
        print(html[max(0,idx-100):idx+300])

print("\nDONE")
