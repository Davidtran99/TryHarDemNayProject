"""
Routing utilities that decide whether a query should hit RAG or stay in small-talk.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class IntentRoute(str, Enum):
    """High-level route for the chatbot pipeline."""

    GREETING = "greeting"
    SMALL_TALK = "small_talk"
    SEARCH = "search"


DOCUMENT_CODE_PATTERNS = [
    r"264[-\s]?QD[-\s]?TW",
    r"QD[-\s]?69[-\s]?TW",
    r"TT[-\s]?02[-\s]?CAND",
    r"TT[-\s]?02[-\s]?BIEN[-\s]?SOAN",
    r"QUYET[-\s]?DINH[-\s]?69",
    r"QUYET[-\s]?DINH[-\s]?264",
    r"THONG[-\s]?TU[-\s]?02",
]

SMALL_TALK_PHRASES = [
    "mệt quá",
    "nhàm chán",
    "tâm sự",
    "chém gió",
    "đang làm gì",
    "chuyện trò",
    "trò chuyện",
    "hỏi chơi thôi",
]


def _has_document_code(query: str) -> bool:
    normalized = query.upper()
    return any(re.search(pattern, normalized) for pattern in DOCUMENT_CODE_PATTERNS)


def _flag_keywords(query_lower: str) -> Dict[str, bool]:
    return {
        "greeting": any(
            phrase in query_lower for phrase in ["xin chào", "xin chao", "chào", "chao", "hello", "hi"]
        ),
        "fine": any(
            kw in query_lower
            for kw in ["mức phạt", "phạt", "vi phạm", "đèn đỏ", "nồng độ cồn", "mũ bảo hiểm", "tốc độ"]
        ),
        "procedure": any(
            kw in query_lower for kw in ["thủ tục", "thu tuc", "hồ sơ", "ho so", "điều kiện", "dieu kien", "cư trú", "cu tru"]
        ),
        "advisory": any(kw in query_lower for kw in ["cảnh báo", "lua dao", "lừa đảo", "scam", "mạo danh", "thủ đoạn"]),
        "office": any(kw in query_lower for kw in ["địa chỉ", "dia chi", "công an", "cong an", "điểm tiếp dân", "số điện thoại"]),
        "legal": any(
            kw in query_lower
            for kw in [
                "quyết định",
                "quyet dinh",
                "thông tư",
                "thong tu",
                "nghị quyết",
                "nghi quyet",
                "nghị định",
                "nghi dinh",
                "luật",
                "luat",
                "điều ",
                "dieu ",
                "kỷ luật",
                "qd 69",
                "qd 264",
                "thông tư 02",
                "điều lệnh",
                "văn bản pháp luật",
            ]
        ),
        "small_talk": any(phrase in query_lower for phrase in SMALL_TALK_PHRASES),
    }


@dataclass
class RouteDecision:
    route: IntentRoute
    intent: str
    confidence: float
    rationale: str
    forced_intent: Optional[str] = None
    keyword_flags: Dict[str, bool] = field(default_factory=dict)


def decide_route(query: str, intent: str, confidence: float) -> RouteDecision:
    """
    Decide how the chatbot should handle the query before invoking RAG.
    """
    query_lower = query.lower().strip()
    words = query_lower.split()
    keyword_flags = _flag_keywords(query_lower)
    has_doc_code = _has_document_code(query_lower)

    route = IntentRoute.SEARCH
    rationale = "default-search"
    forced_intent: Optional[str] = None

    doc_code_override = False
    if has_doc_code and intent != "search_legal":
        forced_intent = "search_legal"
        rationale = "doc-code-detected"
        route = IntentRoute.SEARCH
        doc_code_override = True

    greeting_candidate = (
        len(words) <= 3 and keyword_flags["greeting"] and not any(
            keyword_flags[key] for key in ["fine", "procedure", "advisory", "office", "legal"]
        )
    )
    if greeting_candidate and intent == "greeting" and not doc_code_override:
        route = IntentRoute.GREETING
        rationale = "simple-greeting"
        forced_intent = "greeting"
    elif (
        not doc_code_override
        and keyword_flags["small_talk"]
        and not any(keyword_flags[key] for key in ["fine", "procedure", "advisory", "office", "legal"])
    ):
        route = IntentRoute.SMALL_TALK
        rationale = "small-talk-keywords"
        forced_intent = "general_query"
    elif not doc_code_override and (intent == "general_query" or confidence < 0.55):
        # Generic small talk / low confidence
        route = IntentRoute.SMALL_TALK
        rationale = "general-or-low-confidence"

    if route != IntentRoute.GREETING and not doc_code_override:
        keyword_force_map = [
            ("legal", "search_legal"),
            ("fine", "search_fine"),
            ("procedure", "search_procedure"),
            ("advisory", "search_advisory"),
            ("office", "search_office"),
        ]
        for flag, target_intent in keyword_force_map:
            if forced_intent:
                break
            if keyword_flags.get(flag) and intent != target_intent:
                forced_intent = target_intent
                route = IntentRoute.SEARCH
                rationale = f"keyword-override-{flag}"
                break

    return RouteDecision(
        route=route,
        intent=intent,
        confidence=confidence,
        rationale=rationale,
        forced_intent=forced_intent,
        keyword_flags=keyword_flags,
    )

