"""
爬虫基类。每个网站继承 BaseScraper 并实现 scrape() 方法。
scrape() 返回 list[ScrapedItem]。
"""
from __future__ import annotations
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ScrapedItem:
    """爬虫返回的原始数据，匹配到 cigar 后写入 prices 表"""
    source_slug:   str
    raw_name:      str          # 网站上的原始商品名
    product_url:   str
    price_single:  float | None  # 单支价格
    price_box:     float | None  # 盒装价格
    box_count:     int | None    # 盒装支数
    currency:      str
    in_stock:      bool = True
    image_url:     str | None = None


class BaseScraper(ABC):
    source_slug: str  # 子类声明，对应 sources.slug

    @abstractmethod
    async def scrape(self) -> list[ScrapedItem]:
        """抓取该网站所有古巴雪茄价格，返回 ScrapedItem 列表"""
