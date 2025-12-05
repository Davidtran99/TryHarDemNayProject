"""
Helpers and constants for generated legal QA datasets.

This package contains JSON files with automatically generated
question/answer-style prompts for legal documents stored in the DB.
Each JSON file should follow the schema documented in
`QA_ITEM_SCHEMA` below.
"""

from __future__ import annotations

from typing import TypedDict, Literal, List


DifficultyLevel = Literal["basic", "medium", "advanced"]


class QAItem(TypedDict):
    """
    Schema for a single generated QA-style training example.

    This is intentionally lightweight and independent from any
    specific ML framework so it can be reused by multiple
    training or evaluation scripts.
    """

    question: str
    difficulty: DifficultyLevel
    intent: str
    document_code: str
    section_code: str
    document_title: str
    section_title: str


QA_ITEM_SCHEMA: List[str] = [
    "question",
    "difficulty",
    "intent",
    "document_code",
    "section_code",
    "document_title",
    "section_title",
]


