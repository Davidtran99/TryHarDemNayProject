from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from django.core.management.base import BaseCommand

from hue_portal.chatbot.chatbot import get_chatbot


class Command(BaseCommand):
    """
    Quick smoke-test for legal intent classification & RAG retrieval.

    This command:
    - loads a sample of generated legal questions from
      backend/hue_portal/chatbot/training/generated_qa/
    - runs the intent classifier on each question
    - (best-effort) calls rag_pipeline with use_llm=False to inspect
      retrieved documents and content_type.

    It is intended for operators to run occasionally after auto-training
    to verify that:
      - most legal questions are classified as `search_legal`
      - RAG returns legal content for those questions.
    """

    help = "Run a small evaluation of legal intent & RAG using generated QA questions"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--max-per-doc",
            type=int,
            default=20,
            help="Maximum number of questions to sample per document JSON file.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        max_per_doc: int = options["max_per_doc"]

        base_dir = Path(__file__).resolve().parents[4] / "chatbot" / "training" / "generated_qa"
        if not base_dir.exists():
            self.stdout.write(self.style.WARNING(f"No generated QA directory found at {base_dir}"))
            return

        chatbot = get_chatbot()

        total = 0
        legal_intent = 0
        other_intent = 0

        # Optional RAG import
        try:
            from hue_portal.core.rag import rag_pipeline  # type: ignore
        except Exception:
            rag_pipeline = None  # type: ignore

        self.stdout.write(self.style.MIGRATE_HEADING("Evaluating legal intent & RAG on generated QA..."))

        for path in sorted(base_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self.stdout.write(self.style.WARNING(f"Skipping malformed QA file: {path.name}"))
                continue

            if not isinstance(payload, list):
                continue

            self.stdout.write(self.style.HTTP_INFO(f"File: {path.name}"))

            for item in payload[:max_per_doc]:
                if not isinstance(item, dict):
                    continue
                question = str(item.get("question") or "").strip()
                if not question:
                    continue

                intent, confidence = chatbot.classify_intent(question)
                total += 1
                if intent == "search_legal":
                    legal_intent += 1
                else:
                    other_intent += 1

                rag_info: Tuple[str, int] = ("n/a", 0)
                if rag_pipeline is not None:
                    try:
                        rag_result: Dict[str, Any] = rag_pipeline(
                            question,
                            intent,
                            top_k=3,
                            min_confidence=confidence,
                            context=None,
                            use_llm=False,
                        )
                        rag_info = (
                            str(rag_result.get("content_type") or "n/a"),
                            int(rag_result.get("count") or 0),
                        )
                    except Exception:
                        rag_info = ("error", 0)

                self.stdout.write(
                    f"- Q: {question[:80]}... | intent={intent} ({confidence:.2f}) "
                    f"| RAG type={rag_info[0]} count={rag_info[1]}"
                )

        self.stdout.write("")
        if total == 0:
            self.stdout.write(self.style.WARNING("No questions evaluated."))
            return

        pct_legal = (legal_intent / total) * 100.0
        self.stdout.write(
            self.style.SUCCESS(
                f"Total questions: {total} | search_legal: {legal_intent} ({pct_legal:.1f}%) "
                f"| other intents: {other_intent}"
            )
        )


