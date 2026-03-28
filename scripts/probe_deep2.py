#!/usr/bin/env python3
"""
Deep probe part 2:
- cigarshopworld: actual product listing page
- tabaklaedeli: correct German category URL
- vipcigars: cuban-cigars page (CF passed for homepage)
- timecigar: find API endpoint structure
- hitcigars: WooCommerce product page probe
- montefortuna: find real product listing page
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

def make_client():
    return httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True,
                        transport=httpx.HTTPTransport(retries=1))


# ─── cigarshopworld: real product-category listing ───────────────────────────
print("\n" + "="*70)
print("cigarshopworld.com — product-category/cuban-cigars/")
print("="*70)
with make_client() as c:
    r = c.get("https://cigarshopworld.com/product-category/cuban-cigars/")
    print(f"  status={r.status_code}  url={r.url}")
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("title")
    print(f"  title: {title.get_text(strip=True)[:80] if title else '?'}")

    # WooCommerce product cards use <li class="product ...">
    prod_cards = soup.find_all("li", class_=re.compile(r"\bproduct\b"))
    woo_cards = [p for p in prod_cards if "menu-item" not in " ".join(p.get("class",[]))]
    print(f"  WooCommerce product cards: {len(woo_cards)}")
    for card in woo_cards[:3]:
        name_el = card.find(class_=re.compile(r"woocommerce-loop-product__title|product.?title"))
        price_el = card.find(class_=re.compile(r"\bprice\b"))
        link_el = card.find("a", href=True)
        print(f"\n  Card classes: {card.get('class')}")
        if name_el: print(f"  Name: {name_el.get_text(strip=True)[:60]}")
        if price_el:
            print(f"  Price class: {' '.join(price_el.get('class',[]))}")
            print(f"  Price text: {price_el.get_text(strip=True)[:60]}")
            # show inner structure
            inner = price_el.find(class_=re.compile(r"amount|woocommerce-Price-amount"))
            if inner:
                print(f"  Inner amount: <{inner.name} class=\"{' '.join(inner.get('class',[]))}\"> = {inner.get_text(strip=True)[:30]}")
        if link_el: print(f"  URL: {link_el['href']}")

    if woo_cards:
        print(f"\n  First card raw HTML:\n{str(woo_cards[0])[:1000]}")

    # Also try Holafura / a specific product
    r2 = c.get("https://cigarshopworld.com/product-category/cuban-cigars/cohiba-cuban-cigars/")
    print(f"\n  Cohiba sub-page: status={r2.status_code}")
    soup2 = BeautifulSoup(r2.text, "html.parser")
    woo2 = [p for p in soup2.find_all("li", class_=re.compile(r"\bproduct\b")) if "menu-item" not in " ".join(p.get("class",[]))]
    print(f"  Cards: {len(woo2)}")
    for card in woo2[:2]:
        price_el = card.find(class_=re.compile(r"\bprice\b"))
        name_el = card.find(class_=re.compile(r"woocommerce-loop-product__title|product.?title"))
        if name_el: print(f"  Name: {name_el.get_text(strip=True)[:60]}")
        if price_el: print(f"  Price: {price_el.get_text(strip=True)[:60]}")
    if woo2:
        print(f"\n  Cohiba first card:\n{str(woo2[0])[:800]}")


# ─── tabaklaedeli: correct German URL structure ───────────────────────────────
print("\n" + "="*70)
print("tabaklaedeli.ch — German WooCommerce, find correct Kuba/Cuba URL")
print("="*70)
with make_client() as c:
    # First check sitemap or categories
    for url in [
        "https://www.tabaklaedeli.ch/produkt-kategorie/zigarren/kuba/",
        "https://www.tabaklaedeli.ch/produkt-kategorie/zigarren/",
        "https://www.tabaklaedeli.ch/product-category/cigars/cuba/",
        "https://www.tabaklaedeli.ch/product-category/cigars/",
    ]:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        woo_cards = [p for p in soup.find_all("li", class_=re.compile(r"\bproduct\b")) if "menu-item" not in " ".join(p.get("class",[]))]
        print(f"  {url} → [{r.status_code}] title={title.get_text(strip=True)[:50] if title else '?'} cards={len(woo_cards)}")
        if woo_cards:
            for card in woo_cards[:2]:
                price_el = card.find(class_=re.compile(r"\bprice\b|amount"))
                name_el = card.find(class_=re.compile(r"product.?title|woocommerce-loop"))
                if name_el: print(f"    Name: {name_el.get_text(strip=True)[:50]}")
                if price_el: print(f"    Price ({' '.join(price_el.get('class',[]))}): {price_el.get_text(strip=True)[:50]}")
            print(f"\n  First card:\n{str(woo_cards[0])[:700]}")
            break

    # Also probe homepage for category nav links containing kuba/cuba
    r_home = c.get("https://www.tabaklaedeli.ch/")
    soup_home = BeautifulSoup(r_home.text, "html.parser")
    cuba_links = [a["href"] for a in soup_home.find_all("a", href=re.compile(r"kuba|cuba|habana|cuban", re.I))]
    print(f"\n  Cuba-related links on homepage: {cuba_links[:10]}")


# ─── vipcigars: cuban-cigars product page ────────────────────────────────────
print("\n" + "="*70)
print("vipcigars.com — /cuban-cigars listing")
print("="*70)
with make_client() as c:
    r = c.get("https://www.vipcigars.com/cuban-cigars")
    print(f"  status={r.status_code}  url={r.url}  len={len(r.text)}")
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("title")
    print(f"  title: {title.get_text(strip=True)[:80] if title else '?'}")
    print(f"  CF blocked: {'cloudflare' in r.text.lower() or 'challenge' in r.text.lower()}")

    # Look for product cards
    # vipcigars appears to be a custom platform — scan for price patterns
    price_containers = soup.find_all(class_=re.compile(r"price|tarif|amount|preis", re.I))
    print(f"  Price elements: {len(price_containers)}")
    for el in price_containers[:5]:
        print(f"  <{el.name} class=\"{' '.join(el.get('class',[]))}\"> = {el.get_text(strip=True)[:60]}")

    # find product grid / product list
    grid = soup.find(class_=re.compile(r"product.?grid|product.?list|products.?container|catalog", re.I))
    if grid:
        print(f"\n  Product grid: <{grid.name} class=\"{' '.join(grid.get('class',[]))}\">")
        print(f"  Grid HTML (first 600):\n{str(grid)[:600]}")

    # try to find individual product item patterns
    for selector in ["article", "div[class*=product]", ".product-item", "[data-product-id]"]:
        items = soup.select(selector)
        if items and len(items) < 50:
            print(f"\n  '{selector}' items: {len(items)}")
            for item in items[:2]:
                price_el = item.find(class_=re.compile(r"price|amount", re.I))
                if price_el:
                    print(f"    price class={' '.join(price_el.get('class',[]))} text={price_el.get_text(strip=True)[:50]}")
            print(f"  First item HTML:\n{str(items[0])[:600]}")
            break

    # look for JSON data in script tags
    scripts = r.text
    json_matches = re.findall(r'window\.__[A-Z_]+\s*=\s*(\{.{0,500})', scripts)
    if json_matches:
        print(f"\n  window.__X data: {json_matches[0][:200]}")

    # itemprop price
    itemprop_prices = soup.find_all(attrs={"itemprop": "price"})
    print(f"\n  itemprop=price elements: {len(itemprop_prices)}")
    for el in itemprop_prices[:3]:
        print(f"  content={el.get('content')} text={el.get_text(strip=True)[:40]}")


# ─── timecigar: find real product API ─────────────────────────────────────────
print("\n" + "="*70)
print("timecigar.com — probe API structure")
print("="*70)
with make_client() as c:
    r = c.get("https://www.timecigar.com/tc/products")
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"  /tc/products: status={r.status_code}")

    # Extract all script src to find API hints
    scripts = soup.find_all("script", src=True)
    print(f"  Script sources ({len(scripts)}):")
    for s in scripts[:8]:
        print(f"    {s['src'][:100]}")

    # Look for inline scripts with API patterns
    inline_scripts = soup.find_all("script", src=False)
    for s in inline_scripts:
        text = s.get_text()
        if "api" in text.lower() or "baseUrl" in text or "endpoint" in text.lower():
            print(f"\n  API-hint script (first 400):\n{text[:400]}")

    # Examine product_item structure
    product_items = soup.find_all(class_=re.compile(r"product.?item", re.I))
    print(f"\n  product_item elements: {len(product_items)}")
    if product_items:
        print(f"  First:\n{str(product_items[0])[:600]}")

    # Price boxes
    price_boxes = soup.find_all(class_=re.compile(r"price", re.I))
    print(f"\n  Price elements: {len(price_boxes)}")
    for el in price_boxes[:5]:
        print(f"  <{el.name} class=\"{' '.join(el.get('class',[]))}\"> parent_class={' '.join(el.parent.get('class',[]) if el.parent else [])}")
        print(f"  HTML: {str(el)[:200]}")


# ─── hitcigars: WooCommerce, find product listing ─────────────────────────────
print("\n" + "="*70)
print("hitcigars.com — WooCommerce, find Cuban cigars listing")
print("="*70)
with make_client() as c:
    for url in [
        "https://hitcigars.com/product-category/cuban-cigars/",
        "https://hitcigars.com/product-category/cigars/",
        "https://hitcigars.com/shop/",
        "https://hitcigars.com/cigars/",
    ]:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        woo_cards = [p for p in soup.find_all("li", class_=re.compile(r"\bproduct\b")) if "menu-item" not in " ".join(p.get("class",[]))]
        print(f"  {url} → [{r.status_code}] title={title.get_text(strip=True)[:50] if title else '?'} cards={len(woo_cards)} cf={'cloudflare' in r.text.lower()}")
        if woo_cards:
            for card in woo_cards[:2]:
                price_el = card.find(class_=re.compile(r"\bprice\b|amount"))
                name_el = card.find(class_=re.compile(r"product.?title|woocommerce-loop"))
                if name_el: print(f"    Name: {name_el.get_text(strip=True)[:50]}")
                if price_el: print(f"    Price ({' '.join(price_el.get('class',[]))}): {price_el.get_text(strip=True)[:50]}")
            print(f"  First card:\n{str(woo_cards[0])[:600]}")
            break


# ─── montefortuna: WooCommerce, find actual shop ──────────────────────────────
print("\n" + "="*70)
print("montefortuna.com — WooCommerce, find shop listing")
print("="*70)
with make_client() as c:
    for url in [
        "https://www.montefortunacigars.com/shop/",
        "https://www.montefortunacigars.com/product-category/cuban-cigars/",
        "https://www.montefortunacigars.com/product-category/habanos/",
    ]:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        woo_cards = [p for p in soup.find_all("li", class_=re.compile(r"\bproduct\b")) if "menu-item" not in " ".join(p.get("class",[]))]
        cf = "cloudflare" in r.text.lower() or "just a moment" in r.text.lower()
        print(f"  {url} → [{r.status_code}] cf={cf} cards={len(woo_cards)} title={title.get_text(strip=True)[:60] if title else '?'}")
        if woo_cards:
            for card in woo_cards[:2]:
                price_el = card.find(class_=re.compile(r"\bprice\b|amount"))
                name_el = card.find(class_=re.compile(r"product.?title|woocommerce-loop"))
                if name_el: print(f"    Name: {name_el.get_text(strip=True)[:50]}")
                if price_el: print(f"    Price: {price_el.get_text(strip=True)[:50]}")
            break

print("\nDONE")
