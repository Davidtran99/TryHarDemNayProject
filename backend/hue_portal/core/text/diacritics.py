"""
Vietnamese diacritic restoration helpers for OCR text.

The approach combines:
- Phrase-level overrides for the most common legal headers.
- Word-level overrides for high-value legal terms (Điều, Khoản, Quyết...).
- A fallback dictionary (74k Vietnamese words) when a token maps to a single
  unambiguous candidate with diacritics.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Set

logger = logging.getLogger(__name__)

WORD_PATTERN = re.compile(r"[A-Za-zÀ-ỹĐđ]+", re.UNICODE)

# Common legal phrases that frequently appear in uppercase without diacritics.
LEGAL_PHRASE_OVERRIDES: Dict[str, str] = {
    "BAN CHAP HANH TRUNG UONG": "BAN CHẤP HÀNH TRUNG ƯƠNG",
    "DANG CONG SAN VIET NAM": "ĐẢNG CỘNG SẢN VIỆT NAM",
    "QUYET DINH": "QUYẾT ĐỊNH",
    "NGHI QUYET": "NGHỊ QUYẾT",
    "THONG TU": "THÔNG TƯ",
    "CHI THI": "CHỈ THỊ",
    "LUAT": "LUẬT",
}

# Word-level overrides for high-frequency legal vocabulary.
LEGAL_WORD_OVERRIDES: Dict[str, str] = {
    "CHAP": "CHẤP",
    "HANH": "HÀNH",
    "UONG": "ƯƠNG",
    "DANG": "ĐẢNG",
    "CONG": "CỘNG",
    "SAN": "SẢN",
    "NGHI": "NGHỊ",
    "QUYET": "QUYẾT",
    "DINH": "ĐỊNH",
    "DIEU": "ĐIỀU",
    "KHOAN": "KHOẢN",
    "DIEM": "ĐIỂM",
    "PHAP": "PHÁP",
    "KY": "KỶ",
    "KYLUAT": "KỶ LUẬT",
    "KY LUAT": "KỶ LUẬT",
}

ACCENT_REPLACEMENTS = str.maketrans({"Đ": "D", "đ": "d"})


def strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics while keeping ASCII characters."""
    normalized = unicodedata.normalize("NFD", text).translate(ACCENT_REPLACEMENTS)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


@lru_cache(maxsize=1)
def _accent_index() -> Dict[str, Set[str]]:
    """Build mapping from accent-less uppercase tokens to candidate words."""
    vocab_path = Path(__file__).with_name("vietnamese_words.txt")
    if not vocab_path.exists():
        logger.warning("Vietnamese vocab file missing at %s", vocab_path)
        return {}

    mapping: Dict[str, Set[str]] = {}
    with vocab_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            word = line.strip()
            if not word or " " in word or "\t" in word:
                continue
            key = strip_diacritics(word).upper()
            mapping.setdefault(key, set()).add(word)
    return mapping


def _apply_case(reference: str, candidate: str) -> str:
    """Match the casing style of the reference token."""
    if reference.isupper():
        return candidate.upper()
    if reference.islower():
        return candidate.lower()
    if reference.istitle():
        return candidate.title()
    return candidate


def _restore_word(token: str) -> str:
    key = strip_diacritics(token).upper()
    if not key or len(key) < 2:
        return token

    if key in LEGAL_WORD_OVERRIDES:
        return _apply_case(token, LEGAL_WORD_OVERRIDES[key])

    candidates = _accent_index().get(key)
    if not candidates or len(candidates) != 1:
        return token

    candidate = next(iter(candidates))
    if candidate == token:
        return token
    return _apply_case(token, candidate)


def _apply_phrase_overrides(text: str) -> str:
    result = text
    for raw, corrected in LEGAL_PHRASE_OVERRIDES.items():
        result = result.replace(raw, corrected)
        # Handle Title Case variant
        result = result.replace(raw.title(), corrected.title())
    return result


def restore_vietnamese_text(text: str) -> str:
    """Restore diacritics for a given OCR text snippet."""
    text = _apply_phrase_overrides(text)

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        restored = _restore_word(token)
        return restored

    return WORD_PATTERN.sub(replace, text)


def restore_lines(lines: Iterable[str]) -> List[str]:
    """Restore diacritics for a list of text lines."""
    return [restore_vietnamese_text(line) for line in lines]

