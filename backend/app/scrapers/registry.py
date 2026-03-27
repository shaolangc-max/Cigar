"""
爬虫注册表 — 添加新爬虫时在这里注册即可。
"""
from .base import BaseScraper

_registry: dict[str, type[BaseScraper]] = {}


def register(cls: type[BaseScraper]) -> type[BaseScraper]:
    _registry[cls.source_slug] = cls
    return cls


def get_all() -> list[BaseScraper]:
    return [cls() for cls in _registry.values()]


def get_by_slug(slug: str) -> BaseScraper | None:
    cls = _registry.get(slug)
    return cls() if cls else None
