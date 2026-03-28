"""
多米尼克西班牙 LCDH — dominiquelondon.es (Odoo, EUR)
分类: 古巴雪茄 (category_id=134)
"""
from app.scrapers.odoo_base import OdooShopScraper
from app.scrapers.registry import register


@register
class DominiqueLondonEsScraper(OdooShopScraper):
    source_slug = "dominiquelondon-es"
    base_url    = "https://www.dominiquelondon.es"
    category_id = 134
    currency    = "EUR"
