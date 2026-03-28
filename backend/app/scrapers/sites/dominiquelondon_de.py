"""
德国多米尼克 LCDH — dominiquelondon.de (Odoo, EUR)
分类: 古巴雪茄 (category_id=134)
"""
from app.scrapers.odoo_base import OdooShopScraper
from app.scrapers.registry import register


@register
class DominiqueLondonDeScraper(OdooShopScraper):
    source_slug = "dominiquelondon-de"
    base_url    = "https://www.dominiquelondon.de"
    category_id = 134
    currency    = "EUR"
