"""西站 — cigarshopworld.com (WooCommerce, EUR)"""
from app.scrapers.registry import register
from app.scrapers.woocommerce_base import WooCommerceScraper


@register
class CigarShopWorldScraper(WooCommerceScraper):
    source_slug = "cigarshopworld"
    base_url    = "https://cigarshopworld.com"
    currency    = "EUR"
    categories  = ["cuban-cigars"]
