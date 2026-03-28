"""瑞士补漏站 — tabaklaedeli.ch (WooCommerce, CHF)"""
from app.scrapers.registry import register
from app.scrapers.woocommerce_base import WooCommerceScraper


@register
class TabaklaedeliScraper(WooCommerceScraper):
    source_slug = "tabaklaedeli"
    base_url    = "https://www.tabaklaedeli.ch"
    currency    = "CHF"
    categories  = ["cuba"]
