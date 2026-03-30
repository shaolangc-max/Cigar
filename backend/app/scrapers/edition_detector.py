"""
从雪茄名称中检测特别版类型。
返回 (edition_type, edition_label) 或 (None, None)。

edition_type 枚举：
  reserva          — Reserva / Cosecha 陈年烟叶版
  gran_reserva     — Gran Reserva 超陈年版
  edicion_limitada — Edición Limitada 年度限定
  aniversario      — 周年纪念版
  regional         — Regional Edition 地区限定
  lcdh             — LCDH / Habanos Specialist 专卖店版
"""
from __future__ import annotations
import re


_PATTERNS: list[tuple[str, str, str | None]] = [
    # (regex, edition_type, label_template)  {year} / {text} 为占位符

    # Gran Reserva YYYY（优先于普通 Reserva）
    (r"gran\s+reserva\s+(\d{4})", "gran_reserva", "Gran Reserva {year}"),
    (r"gran\s+reserva", "gran_reserva", "Gran Reserva"),

    # Reserva Cosecha YYYY（优先匹配，比单独 Cosecha 更具体）
    (r"reserva\s+cosecha\s+(\d{4})", "reserva", "Reserva Cosecha {year}"),
    # Cosecha YYYY
    (r"\bcosecha\s+(\d{4})", "reserva", "Cosecha {year}"),
    # Reserva YYYY
    (r"\breserva\s+(\d{4})", "reserva", "Reserva {year}"),

    # Edición Limitada YYYY / Edicion Limitada YYYY
    (r"edici[oó]n\s+limitada\s+(\d{4})", "edicion_limitada", "Edición Limitada {year}"),
    # EL YYYY（独立单词）
    (r"\bel\s+(\d{4})\b", "edicion_limitada", "Edición Limitada {year}"),

    # XX Aniversario / Conmemorativo
    (r"(\d+)\s+aniversario", "aniversario", "{year} Aniversario"),
    (r"conmemorativo", "aniversario", "Conmemorativo"),

    # Year of the XXX
    (r"year\s+of\s+the\s+(\w+)", "edicion_limitada", "Year of the {year}"),
    # Año del / Año de la
    (r"a[ñn]o\s+de(?:l|la)?\s+(\w+)", "edicion_limitada", "Año del {year}"),

    # Regional Edition / Edición Regional
    (r"regional\s+edition", "regional", "Regional Edition"),
    (r"edici[oó]n\s+regional", "regional", "Regional Edition"),

    # LCDH / Habanos Specialist
    (r"\blcdh\b", "lcdh", "LCDH"),
    (r"habanos\s+specialist", "lcdh", "Habanos Specialist"),
]


def detect_edition(name: str) -> tuple[str | None, str | None]:
    """
    输入雪茄名，返回 (edition_type, edition_label)。
    未检测到特别版时返回 (None, None)。

    示例：
      "Cohiba Siglo VI Reserva Cosecha 2014" → ("reserva", "Reserva Cosecha 2014")
      "Cohiba 1966 Edición Limitada 2021"    → ("edicion_limitada", "Edición Limitada 2021")
      "Cohiba 55 Aniversario EL 2021"        → ("aniversario", "55 Aniversario")
      "Cohiba Gran Reserva 2009"             → ("gran_reserva", "Gran Reserva 2009")
      "Cohiba Siglo VI"                      → (None, None)
    """
    lower = name.lower()
    for pattern, edition_type, label_tpl in _PATTERNS:
        m = re.search(pattern, lower)
        if m:
            if label_tpl is None:
                label = m.group(0).title()
            else:
                captured = m.group(1).title() if m.lastindex else ""
                label = label_tpl.replace("{year}", captured).replace("{text}", captured)
            return edition_type, label
    return None, None
