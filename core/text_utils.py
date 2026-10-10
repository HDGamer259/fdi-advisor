"""Tiện ích xử lý văn bản tiếng Việt (có dấu / không dấu)."""
from __future__ import annotations

import re
import unicodedata

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def lower_clean(text: str) -> str:
    """Chữ thường, NFC, bỏ dấu câu, gộp khoảng trắng (GIỮ dấu tiếng Việt)."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt: 'Bắc Ninh' -> 'bac ninh'."""
    text = lower_clean(text).replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def has_diacritics(text: str) -> bool:
    cleaned = lower_clean(text)
    return cleaned != strip_accents(cleaned)


def contains_phrase(haystack: str, phrase: str) -> bool:
    """So khớp cụm từ theo ranh giới từ (haystack & phrase đã chuẩn hóa)."""
    if not phrase:
        return False
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", haystack) is not None


def remove_phrase(haystack: str, phrase: str) -> str:
    out = re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", " ", haystack)
    return _SPACE_RE.sub(" ", out).strip()


def tokenize(text: str) -> list[str]:
    """Token không dấu, dùng cho embedding/retrieval."""
    return strip_accents(text).split()


def format_vnd(amount: int) -> str:
    return f"{amount:,}".replace(",", ".")
