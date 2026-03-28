"""德国烟屋 HS — pipehouse.de (WooCommerce, EUR)"""
from app.scrapers.registry import register
from app.scrapers.woocommerce_base import WooCommerceScraper


@register
class PipehouseScraper(WooCommerceScraper):
    source_slug = "pipehouse"
    base_url    = "https://pipehouse.de"
    currency    = "EUR"
    categories  = ["kubanische-zigarren"]
