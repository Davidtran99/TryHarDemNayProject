"""
Exact match cache for caching repeated chatbot responses.
"""
from __future__ import annotations

import copy
import time
import unicodedata
import re
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple


class ExactMatchCache:
    """LRU cache that stores full chatbot responses for exact queries."""

    def __init__(self, max_size: int = 256, ttl_seconds: Optional[int] = 43200):
        self.max_size = max(1, max_size)
        self.ttl = ttl_seconds
        self._store: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()

    def get(self, query: str, intent: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return cached response if still valid."""
        key = self._make_key(query, intent)
        record = self._store.get(key)
        if not record:
            return None

        timestamp, payload = record
        if self.ttl and (time.time() - timestamp) > self.ttl:
            self._store.pop(key, None)
            return None

        self._store.move_to_end(key)
        return copy.deepcopy(payload)

    def set(self, query: str, intent: Optional[str], response: Dict[str, Any]) -> None:
        """Store response for normalized query/int."""
        key = self._make_key(query, intent)
        self._store[key] = (time.time(), copy.deepcopy(response))
        self._store.move_to_end(key)
        if len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()

    def _make_key(self, query: str, intent: Optional[str]) -> str:
        normalized_query = self._normalize_query(query or "")
        normalized_intent = (intent or "").strip().lower()
        return f"{normalized_intent}::{normalized_query}"

    def _normalize_query(self, query: str) -> str:
        """Normalize query for stable caching."""
        text = query.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"\s+", " ", text)
        return text

