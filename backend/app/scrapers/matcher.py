"""
商品名匹配 — 将爬取的 raw_name 匹配到数据库中的 Cigar。

匹配策略（按优先级）：
1. 精确匹配 cigar.name
2. 品牌 + 系列关键词 + 规格关键词
3. 相似度 > 阈值
"""
from __future__ import annotations
import re
from difflib import SequenceMatcher

BRAND_ALIASES: dict[str, str] = {
    "cohiba":       "cohiba",
    "montecristo":  "montecristo",
    "romeo y julieta": "romeo-y-julieta",
    "romeo":        "romeo-y-julieta",
    "bolivar":      "bolivar",
    "partagas":     "partagas",
    "h.upmann":     "h-upmann",
    "upmann":       "h-upmann",
    "punch":        "punch",
    "hoyo de monterrey": "hoyo-de-monterrey",
    "hoyo":         "hoyo-de-monterrey",
    "trinidad":     "trinidad",
    "por larrañaga": "por-larranaga",
    "saint luis rey": "saint-luis-rey",
    "quai d'orsay": "quai-dorsay",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def extract_brand(raw: str) -> str | None:
    norm = normalize(raw)
    for alias, slug in BRAND_ALIASES.items():
        if alias in norm:
            return slug
    return None


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def best_match(raw_name: str, candidates: list[dict]) -> dict | None:
    """
    candidates: list of {"id": int, "name": str, "slug": str}
    返回相似度最高且 > 0.75 的候选，或 None。
    """
    if not candidates:
        return None
    scored = [(similarity(raw_name, c["name"]), c) for c in candidates]
    scored.sort(key=lambda x: -x[0])
    score, match = scored[0]
    return match if score > 0.75 else None


def best_match_with_aliases(
    raw_name: str,
    source_slug: str,
    aliases: dict[tuple[str, str], int],
    candidates: list[dict],
) -> tuple[dict | None, float, str | None]:
    """
    先查别名表，命中直接返回（score=1.0）；否则走模糊匹配。
    aliases: {(source_slug, raw_name): cigar_id}
    """
    cigar_id = aliases.get((source_slug, raw_name))
    if cigar_id is not None:
        cigar = next((c for c in candidates if c["id"] == cigar_id), None)
        if cigar:
            return cigar, 1.0, cigar["name"]

    return best_match_with_score(raw_name, candidates)


def best_match_with_score(raw_name: str, candidates: list[dict]) -> tuple[dict | None, float, str | None]:
    """
    返回 (匹配结果, 最高得分, 最接近的候选名)
    供记录未匹配原因使用。
    """
    if not candidates:
        return None, 0.0, None
    scored = [(similarity(raw_name, c["name"]), c) for c in candidates]
    scored.sort(key=lambda x: -x[0])
    score, top = scored[0]
    if score > 0.75:
        return top, score, top["name"]
    return None, score, top["name"]
