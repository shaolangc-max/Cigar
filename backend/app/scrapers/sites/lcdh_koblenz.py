"""
德国科布伦茨 LCDH — la-casa-del-habano-koblenz.de (WooCommerce, EUR)
"""
from app.scrapers.woocommerce_base import WooCommerceScraper
from app.scrapers.registry import register


@register
class LcdhKoblenzScraper(WooCommerceScraper):
    source_slug = "lcdh-koblenz"
    base_url    = "https://la-casa-del-habano-koblenz.de"
    currency    = "EUR"
    categories  = ["kubanische-zigarren"]
