"""
瑞士蒙特勒 HS — tabashop.ch (Odoo, CHF)
分类: Cigares Cubains (category_id=480)
URL 格式: /en_US/shop/category/cigares-cubains-480
"""
from app.scrapers.odoo_base import OdooShopScraper
from app.scrapers.registry import register


@register
class TabashopScraper(OdooShopScraper):
    source_slug    = "tabashop"
    base_url       = "https://tabashop.ch"
    category_id    = 480
    currency       = "CHF"
    lang_prefix    = "en_US"
    category_slug  = "cigares-cubains"
