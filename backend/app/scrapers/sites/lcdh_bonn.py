"""
德国波恩 LCDH — lcdh-bonn.de (WooCommerce, EUR)
"""
from app.scrapers.woocommerce_base import WooCommerceScraper
from app.scrapers.registry import register


@register
class LcdhBonnScraper(WooCommerceScraper):
    source_slug = "lcdh-bonn"
    base_url    = "https://www.lcdh-bonn.de"
    currency    = "EUR"
    categories  = ["169"]   # category ID for "Cuba" on this store
