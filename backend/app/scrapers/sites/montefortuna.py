"""蒙特站 — montefortunacigars.com (WooCommerce, USD)"""
from app.scrapers.registry import register
from app.scrapers.woocommerce_base import WooCommerceScraper


@register
class MontefortunaScraper(WooCommerceScraper):
    source_slug = "montefortuna"
    base_url    = "https://www.montefortunacigars.com"
    currency    = "USD"
    categories  = ["cuban-cigars"]
