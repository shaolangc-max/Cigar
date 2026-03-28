"""
荷兰海牙 LCDH — lacasadelhabano-thehague.com (WooCommerce, EUR)
"""
from app.scrapers.woocommerce_base import WooCommerceScraper
from app.scrapers.registry import register


@register
class LcdhTheHagueScraper(WooCommerceScraper):
    source_slug = "lcdh-thehague"
    base_url    = "https://lacasadelhabano-thehague.com"
    currency    = "EUR"
    categories  = ["cigars"]
