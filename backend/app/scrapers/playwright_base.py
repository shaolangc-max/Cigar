"""
基于 Playwright 的爬虫基类，用于需要 JavaScript 渲染的网站。
"""
from __future__ import annotations
from abc import abstractmethod
from playwright.async_api import async_playwright, Page, BrowserContext

from app.scrapers.base import BaseScraper, ScrapedItem


class PlaywrightScraper(BaseScraper):
    """需要 JS 渲染的网站使用此基类。"""

    # 子类可覆盖
    headless: bool = True
    timeout_ms: int = 30_000

    async def _new_context(self, playwright):
        browser = await playwright.chromium.launch(headless=self.headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 800},
        )
        context.set_default_timeout(self.timeout_ms)
        return browser, context

    async def scrape(self) -> list[ScrapedItem]:
        async with async_playwright() as pw:
            browser, context = await self._new_context(pw)
            try:
                return await self.scrape_with_context(context)
            finally:
                await context.close()
                await browser.close()

    @abstractmethod
    async def scrape_with_context(self, context: BrowserContext) -> list[ScrapedItem]:
        """子类实现：使用 context.new_page() 进行抓取"""
