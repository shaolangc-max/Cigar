"""
多米尼克比利时 LCDH — lacasadelhabano-dl.be (Odoo, EUR)
分类: 古巴雪茄 (category_id=134)
"""
from app.scrapers.odoo_base import OdooShopScraper
from app.scrapers.registry import register


@register
class LcdhBeScraper(OdooShopScraper):
    source_slug = "lcdh-be"
    base_url    = "https://www.lacasadelhabano-dl.be"
    category_id = 134
    currency    = "EUR"
