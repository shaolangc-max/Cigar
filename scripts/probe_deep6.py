#!/usr/bin/env python3
"""
Deep probe part 6: timecigar webapi product list + vipcigars PDP price
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
JSON_HEADERS = {**HEADERS, "Accept": "application/json, */*", "X-Requested-With": "XMLHttpRequest"}

def make_client(extra_headers=None):
    h = {**HEADERS, **(extra_headers or {})}
    return httpx.Client(headers=h, timeout=20, follow_redirects=True,
                        transport=httpx.HTTPTransport(retries=1))


# ─── timecigar: probe all webapi routes ──────────────────────────────────────
print("\n" + "="*70)
print("timecigar.com — webapi product routes")
print("="*70)
with make_client(JSON_HEADERS) as c:
    # From App.bundle.js we know it uses /webapi/* — try product listing routes
    routes_to_try = [
        "/webapi/product/list",
        "/webapi/product/index",
        "/webapi/product/search",
        "/webapi/products",
        "/webapi/catalog/list",
        "/webapi/catalog/product_list",
        "/webapi/shop/product_list",
        "/webapi/product/category_list",
        "/webapi/category/product_list",
        "/webapi/eshop/product_list",
        "/webapi/eshop/list",
    ]
    for path in routes_to_try:
        try:
            r = c.get(f"https://www.timecigar.com{path}?limit=5")
            ct = r.headers.get("content-type","")
            text = r.text.strip()
            is_json = "json" in ct or text.startswith("{") or text.startswith("[")
            print(f"  {path} → {r.status_code}  json={is_json}  len={len(text)}")
            if is_json and r.status_code == 200:
                print(f"  data: {text[:200]}")
        except Exception as e:
            print(f"  {path} ERROR: {e}")

    # Also look at product page for price structure — click into a product
    r = c.get("https://www.timecigar.com/tc/products")
    soup = BeautifulSoup(r.text, "html.parser")
    # find any anchor leading to a product detail
    prod_links = [a["href"] for a in soup.find_all("a", href=re.compile(r"/tc/product/|/tc/item/|/tc/shop/", re.I))]
    print(f"\n  Product detail links: {prod_links[:5]}")

    # from the eshop div we saw product-id=56, option-id=56
    # try webapi with product id
    for path in [
        "/webapi/product/detail?product_id=56",
        "/webapi/eshop/product_detail?id=56",
        "/webapi/product/56",
    ]:
        try:
            r2 = c.get(f"https://www.timecigar.com{path}")
            ct = r2.headers.get("content-type","")
            text = r2.text.strip()
            is_json = "json" in ct or text.startswith("{")
            print(f"  {path} → {r2.status_code}  json={is_json}")
            if is_json:
                print(f"  data: {text[:200]}")
        except Exception as e:
            print(f"  ERROR: {e}")

    # get full App.bundle.js and grep for webapi + product together
    r_js = c.get("https://www.timecigar.com/web/dist/App.bundle.js?214")
    js = r_js.text
    # find patterns like /webapi/xxx near "product"
    contexts = re.findall(r'.{0,60}["\'](/webapi/[^"\']+)["\'].{0,60}', js)
    print(f"\n  All /webapi/ paths in App.bundle.js:")
    for ctx in sorted(set(m.strip() for m in re.findall(r'["\'](/webapi/[^"\']+)["\']', js)))[:40]:
        print(f"    {ctx}")


# ─── vipcigars: PDP structured price data ─────────────────────────────────────
print("\n" + "="*70)
print("vipcigars.com — PDP full price structure")
print("="*70)
with make_client() as c:
    r = c.get("https://www.vipcigars.com/cuban-cigars/cohiba/bhk-52-box-of-10.html")
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    print(f"  status={r.status_code}  len={len(html)}")

    # Find price section
    price_section = soup.find(class_=re.compile(r"price|amount|cost", re.I))
    if price_section:
        # walk to parent with meaningful class
        p = price_section
        for _ in range(6):
            classes = " ".join(p.get("class", []))
            if any(w in classes.lower() for w in ["product", "item", "detail"]):
                print(f"  Product section: <{p.name} class={classes[:60]}>")
                print(f"  HTML:\n{str(p)[:800]}")
                break
            p = p.parent
            if p is None: break

    # itemprop data
    itemprop_els = soup.find_all(attrs={"itemprop": True})
    print(f"\n  itemprop elements: {len(itemprop_els)}")
    for el in itemprop_els[:8]:
        print(f"  itemprop={el.get('itemprop')}  content={el.get('content')}  text={el.get_text(strip=True)[:40]}")

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            print(f"\n  JSON-LD:\n{json.dumps(data, indent=2)[:500]}")
        except Exception:
            pass

    # dataLayer price on PDP
    dl_matches = re.findall(r'dataLayer\.push\((\{.{20,3000}?\})\s*\)', html, re.DOTALL)
    print(f"\n  dataLayer pushes: {len(dl_matches)}")
    for m in dl_matches:
        if "price" in m.lower():
            # extract price
            prices = re.findall(r'"?price"?\s*:\s*"?([\d.]+)"?', m)
            item_name = re.findall(r'"?item_name"?\s*:\s*"([^"]+)"', m)
            currency = re.findall(r'"?currency"?\s*:\s*"([^"]+)"', m)
            print(f"  currency={currency}  item={item_name[:1]}  prices={prices[:3]}")
            break

    # Check for hidden input with price
    hidden_inputs = soup.find_all("input", type="hidden", attrs={"name": re.compile(r"price", re.I)})
    print(f"\n  hidden input[name=price*]: {[(i.get('name'), i.get('value')) for i in hidden_inputs[:3]]}")

    # Full raw HTML snippet around price (CHF/EUR)
    idx = html.find("priceCurrency")
    if idx > 0:
        print(f"\n  HTML around priceCurrency:\n{html[max(0,idx-100):idx+400]}")


# ─── COC: /en/cigars product structure ────────────────────────────────────────
print("\n" + "="*70)
print("cigars-of-cuba.com — /en/cigars full product card + price")
print("="*70)
with make_client() as c:
    r = c.get("https://www.cigars-of-cuba.com/en/cigars?cur=EUR")
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"  status={r.status_code}  len={len(r.text)}")

    items = soup.select(".product-item")
    print(f"  .product-item count: {len(items)}")
    if items:
        item = items[0]
        print(f"\n  First .product-item HTML:\n{str(item)[:1000]}")

    # Full price structure
    prices_boxes = soup.select(".prices-box")
    if prices_boxes:
        print(f"\n  First .prices-box HTML:\n{str(prices_boxes[0])}")

    # Check currency
    eur_prices = re.findall(r'content="EUR"', r.text)
    usd_prices = re.findall(r'content="USD"', r.text)
    chf_prices = re.findall(r'content="CHF"', r.text)
    print(f"\n  Currency meta counts: EUR={len(eur_prices)} USD={len(usd_prices)} CHF={len(chf_prices)}")

    # Check the cuban-cigars page specifically
    r2 = c.get("https://www.cigars-of-cuba.com/en/cuban-cigars?cur=EUR")
    s2 = BeautifulSoup(r2.text, "html.parser")
    t2 = s2.find("title")
    items2 = s2.select(".product-item")
    print(f"\n  /en/cuban-cigars?cur=EUR → {r2.status_code}  title={t2.get_text(strip=True)[:60] if t2 else '?'}")
    print(f"  .product-item: {len(items2)}")

    # maybe the URL structure is different — check home page nav
    r3 = c.get("https://www.cigars-of-cuba.com/en/")
    s3 = BeautifulSoup(r3.text, "html.parser")
    # get all nav/menu links
    all_hrefs = sorted(set(a["href"] for a in s3.find_all("a", href=re.compile(r"cigars-of-cuba\.com/en/"))))
    print(f"\n  /en/* links on homepage: {all_hrefs[:15]}")


print("\nDONE")
