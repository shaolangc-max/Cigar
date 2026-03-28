#!/usr/bin/env python3
"""
Deep probe part 4: finalize remaining sites
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

def is_cf(html):
    return any(p.lower() in html.lower() for p in ["cloudflare","just a moment","cf_clearance"])


# ─── tabaklaedeli: cuba page has 0 product li — find actual product container ──
print("\n" + "="*70)
print("tabaklaedeli.ch — Cuba page structure (no WC product li)")
print("="*70)
with make_client() as c:
    r = c.get("https://www.tabaklaedeli.ch/produkt-kategorie/zigarren/cuba/")
    print(f"  status={r.status_code}  len={len(r.text)}")
    soup = BeautifulSoup(r.text, "html.parser")
    # Search broadly
    all_price = soup.find_all(class_=re.compile(r"price|amount|preis", re.I))
    print(f"  Price elements: {len(all_price)}")
    for el in all_price[:6]:
        print(f"  <{el.name} class=\"{' '.join(el.get('class',[]))}\">  text={el.get_text(strip=True)[:60]}")

    # product wrapper divs
    prod_divs = soup.find_all("div", class_=re.compile(r"product", re.I))
    print(f"\n  div.product*: {len(prod_divs)}")
    for d in prod_divs[:3]:
        print(f"  <{d.name} class=\"{' '.join(d.get('class',[]))}\">  text={d.get_text(strip=True)[:80]}")

    # articles
    articles = soup.find_all("article")
    print(f"\n  <article> elements: {len(articles)}")
    for a in articles[:2]:
        print(f"  <article class=\"{' '.join(a.get('class',[]))}\">  text={a.get_text(strip=True)[:80]}")
        price = a.find(class_=re.compile(r"price|amount"))
        if price:
            print(f"  price: {price.get_text(strip=True)[:40]}")

    # raw HTML snapshot around price (first 800)
    idx = r.text.lower().find("chf")
    if idx > 0:
        print(f"\n  HTML near CHF (first mention):\n{r.text[max(0,idx-200):idx+300]}")


# ─── vipcigars: it's an SPA with server-side render — scan for price data ──────
print("\n" + "="*70)
print("vipcigars.com — scan SSR for product data (Cohiba listing)")
print("="*70)
with make_client() as c:
    r = c.get("https://www.vipcigars.com/cuban-cigars/cohiba")
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    # Try to find product container by common tailwind patterns
    # The site uses Tailwind + Bulma (dropdown is-hoverable)
    # Look for any element with data-product / x-data attributes
    x_data = soup.find_all(attrs={"x-data": True})
    print(f"  x-data elements: {len(x_data)}")
    for el in x_data[:3]:
        print(f"  <{el.name} x-data=\"{str(el.get('x-data',''))[:80]}\">")

    # Look for Alpine.js component data containing price
    alpine_data = re.findall(r'x-data=["\'](\{[^"\']{0,400})["\']', html)
    for d in alpine_data[:3]:
        if "price" in d.lower():
            print(f"  Alpine x-data with price: {d[:200]}")

    # Look for product list in raw HTML (CHF amounts)
    chf_prices = re.findall(r'[\d,]+\.?\d*\s*(?:CHF|Fr\.)', html)
    print(f"  CHF prices in page: {chf_prices[:10]}")
    eur_prices = re.findall(r'€\s*[\d,]+\.?\d*', html)
    print(f"  EUR prices in page: {eur_prices[:10]}")

    # Try the API endpoint hint from HTML
    # Look for window.__INITIAL_STATE__ or similar
    window_data = re.findall(r'window\.\w+\s*=\s*(\{.{50,2000}?\});', html, re.DOTALL)
    for d in window_data[:2]:
        print(f"  window.X data: {d[:200]}")

    # Check script tags for price data
    inline_scripts = soup.find_all("script", src=False)
    for s in inline_scripts:
        txt = s.get_text()
        if re.search(r"CHF|EUR|price", txt, re.I) and len(txt) > 100:
            print(f"\n  Price-containing script:\n{txt[:400]}")
            break

    # Try API calls that vipcigars might use
    for api_url in [
        "https://www.vipcigars.com/api/products?category=cohiba",
        "https://www.vipcigars.com/api/v1/products?brand=cohiba",
        "https://www.vipcigars.com/cuban-cigars/cohiba?format=json",
        "https://www.vipcigars.com/cuban-cigars/cohiba.json",
    ]:
        r2 = c.get(api_url)
        ct = r2.headers.get("content-type","")
        print(f"  API {api_url.split('vipcigars.com')[1]} → {r2.status_code} {ct[:40]}")
        if r2.status_code == 200 and "json" in ct:
            print(f"  data: {r2.text[:200]}")


# ─── timecigar: /webapi/ endpoints ────────────────────────────────────────────
print("\n" + "="*70)
print("timecigar.com — probe /webapi/ endpoints")
print("="*70)
with make_client() as c:
    for url in [
        "https://www.timecigar.com/webapi/promo/special_add_buy_product_list",
        "https://www.timecigar.com/tc/webapi/product/list?limit=5",
        "https://www.timecigar.com/tc/webapi/products?limit=5",
        "https://www.timecigar.com/webapi/product/list?limit=5",
        "https://www.timecigar.com/webapi/products?limit=5",
    ]:
        try:
            r = c.get(url)
            ct = r.headers.get("content-type","")
            print(f"  {url.split('timecigar.com')[1]} → {r.status_code}  ct={ct[:40]}")
            if r.status_code == 200 and ("json" in ct or r.text.strip().startswith("{")):
                print(f"  data: {r.text[:300]}")
        except Exception as e:
            print(f"  {url} ERROR: {e}")

    # Also probe the TC products page more carefully to get product container HTML
    r = c.get("https://www.timecigar.com/tc/products")
    soup = BeautifulSoup(r.text, "html.parser")
    # find any div with product data
    product_container = soup.find(id=re.compile(r"product|catalog|shop", re.I))
    if product_container:
        print(f"\n  Product container: <{product_container.name} id={product_container.get('id')}>")
        print(f"  HTML: {str(product_container)[:500]}")
    # find eshop div
    eshop_div = soup.find(class_=re.compile(r"eshop", re.I))
    if eshop_div:
        print(f"\n  eshop div: {str(eshop_div)[:600]}")

    # complete price element structure from products page
    price_divs = soup.find_all(class_="price_box")
    if price_divs:
        print(f"\n  .price_box count: {len(price_divs)}")
        print(f"  Full price_box HTML:\n{str(price_divs[0])}")

    # Look for parent of price_box to find product card template
    if price_divs:
        parent = price_divs[0].parent
        while parent and parent.name not in ["article","li","div"] or (parent.name == "div" and len(" ".join(parent.get("class",[]))) < 5):
            parent = parent.parent
        if parent:
            print(f"\n  Product card parent: <{parent.name} class=\"{' '.join(parent.get('class',[]))}\">")
            print(f"  HTML:\n{str(parent)[:800]}")


# ─── montefortuna: shop page ──────────────────────────────────────────────────
print("\n" + "="*70)
print("montefortuna.com — shop page price DOM")
print("="*70)
with make_client() as c:
    r = c.get("https://www.montefortunacigars.com/shop/")
    soup = BeautifulSoup(r.text, "html.parser")
    woo_cards = [p for p in soup.find_all("li", class_=re.compile(r"\bproduct\b"))
                 if "menu-item" not in " ".join(p.get("class",[]))]
    print(f"  Products: {len(woo_cards)}  CF={is_cf(r.text)}")
    for card in woo_cards[:3]:
        name_el = card.find(class_=re.compile(r"woocommerce-loop-product__title|product.?title"))
        price_el = card.find(class_=re.compile(r"\bprice\b"))
        if name_el: print(f"  Name: {name_el.get_text(strip=True)[:60]}")
        if price_el:
            print(f"  Price class: {' '.join(price_el.get('class',[]))}")
            print(f"  Price text: {price_el.get_text(strip=True)[:80]}")
            amount = price_el.find(class_=re.compile(r"woocommerce-Price-amount|amount"))
            if amount:
                print(f"  Amount: <{amount.name} class=\"{' '.join(amount.get('class',[]))}\"> = {amount.get_text(strip=True)[:30]}")
        print()
    if woo_cards:
        print(f"  First card:\n{str(woo_cards[0])[:1000]}")

    # Also try direct cuban cigars URL
    r2 = c.get("https://www.montefortunacigars.com/product-category/habanos/")
    s2 = BeautifulSoup(r2.text, "html.parser")
    title2 = s2.find("title")
    woo2 = [p for p in s2.find_all("li", class_=re.compile(r"\bproduct\b"))
            if "menu-item" not in " ".join(p.get("class",[]))]
    print(f"\n  /product-category/habanos/ → {r2.status_code}  title={title2.get_text(strip=True)[:60] if title2 else '?'}  cards={len(woo2)}")


# ─── cigars-of-cuba: scan homepage nav & price structure ──────────────────────
print("\n" + "="*70)
print("cigars-of-cuba.com — homepage nav + price structure")
print("="*70)
with make_client() as c:
    r = c.get("https://www.cigars-of-cuba.com/en/")
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("title")
    print(f"  status={r.status_code}  title={title.get_text(strip=True)[:60] if title else '?'}")
    print(f"  CF={is_cf(r.text)}")

    # Nav links
    all_links = [(a.get_text(strip=True)[:40], a["href"]) for a in soup.find_all("a", href=True)
                 if "cigars" in a["href"].lower() or "habano" in a["href"].lower() or "cuban" in a["href"].lower()]
    print(f"  Cigar-related links: {all_links[:10]}")

    # Price elements
    price_els = soup.find_all(class_=re.compile(r"price|amount", re.I))
    print(f"  Price elements: {len(price_els)}")
    for el in price_els[:5]:
        print(f"  <{el.name} class=\"{' '.join(el.get('class',[]))}\"> = {el.get_text(strip=True)[:50]}")

    # Raw price in HTML
    eur_prices = re.findall(r'€[\d,]+\.?\d*|[\d,]+\.?\d*\s*€', r.text)
    chf_prices = re.findall(r'CHF\s*[\d,]+\.?\d*|Fr\.\s*[\d,]+\.?\d*', r.text)
    print(f"  EUR prices: {eur_prices[:5]}")
    print(f"  CHF prices: {chf_prices[:5]}")

    # Try to find real product listing URL
    for url in [
        "https://www.cigars-of-cuba.com/en/cigars",
        "https://www.cigars-of-cuba.com/en/habanos",
        "https://www.cigars-of-cuba.com/en/shop",
        "https://www.cigars-of-cuba.com/en/all-cuban-cigars",
    ]:
        r2 = c.get(url)
        s2 = BeautifulSoup(r2.text, "html.parser")
        t2 = s2.find("title")
        p2 = s2.find_all(class_=re.compile(r"price|amount", re.I))
        print(f"  {url} → [{r2.status_code}]  {t2.get_text(strip=True)[:40] if t2 else '?'}  prices={len(p2)}")

print("\nDONE")
