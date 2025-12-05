"""
Management command to test legal question coverage end-to-end.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from django.core.management.base import BaseCommand
from hue_portal.chatbot.chatbot import get_chatbot
from hue_portal.chatbot.training.generated_qa import QAItem


class Command(BaseCommand):
    help = "Test legal question coverage using generated QA questions"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--max-per-doc",
            type=int,
            default=50,
            help="Maximum number of questions to sample per document JSON file.",
        )
        parser.add_argument(
            "--api-url",
            type=str,
            default=None,
            help="Optional API URL to test via HTTP (e.g., https://davidtran999-hue-portal-backend.hf.space/api/chatbot/chat/). If not provided, tests locally.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        max_per_doc: int = options["max_per_doc"]
        api_url: str = options.get("api_url")

        base_dir = Path(__file__).resolve().parents[4] / "chatbot" / "training" / "generated_qa"
        if not base_dir.exists():
            self.stdout.write(
                self.style.WARNING(f"No generated QA directory found at {base_dir}")
            )
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING("Testing legal question coverage...")
        )

        # Load all QA questions
        all_questions: List[QAItem] = []
        for path in sorted(base_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    # Sample up to max_per_doc questions
                    sampled = payload[:max_per_doc]
                    all_questions.extend(sampled)
                    self.stdout.write(
                        f"  Loaded {len(sampled)} questions from {path.name}"
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"  Failed to load {path.name}: {e}")
                )

        if not all_questions:
            self.stdout.write(self.style.ERROR("No questions found to test"))
            return

        self.stdout.write(f"\nTesting {len(all_questions)} questions...\n")

        # Test each question
        results: List[Dict[str, Any]] = []
        correct_intent = 0
        has_rag = 0
        has_answer = 0
        has_citation = 0
        no_results = 0

        chatbot = get_chatbot()

        for idx, qa_item in enumerate(all_questions, 1):
            question = qa_item["question"]
            expected_intent = qa_item.get("intent", "search_legal")
            doc_code = qa_item.get("document_code", "")

            if api_url:
                # Test via HTTP API
                import requests

                try:
                    response = requests.post(
                        api_url,
                        json={"message": question},
                        timeout=30,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        detected_intent = data.get("intent", "")
                        answer = data.get("message", "")
                        count = data.get("count", 0)
                    else:
                        detected_intent = "error"
                        answer = f"HTTP {response.status_code}"
                        count = 0
                except Exception as e:
                    detected_intent = "error"
                    answer = str(e)
                    count = 0
            else:
                # Test locally
                response = chatbot.generate_response(question)
                detected_intent = response.get("intent", "")
                answer = response.get("message", "")
                count = response.get("count", 0)

            # Analyze results
            intent_correct = detected_intent == expected_intent
            has_documents = count > 0
            answer_has_content = bool(answer and len(answer.strip()) > 20)
            answer_has_denial = any(
                phrase in answer.lower()
                for phrase in [
                    "không tìm thấy",
                    "chưa có dữ liệu",
                    "không có thông tin",
                    "xin lỗi",
                ]
            )
            answer_has_citation = any(
                marker in answer
                for marker in [doc_code, "Trích dẫn", "Nguồn:", "điều", "khoản"]
            )

            result = {
                "question": question,
                "expected_intent": expected_intent,
                "detected_intent": detected_intent,
                "intent_correct": intent_correct,
                "count": count,
                "has_documents": has_documents,
                "answer_length": len(answer) if answer else 0,
                "has_denial": answer_has_denial,
                "has_citation": answer_has_citation,
                "doc_code": doc_code,
            }
            results.append(result)

            # Update counters
            if intent_correct:
                correct_intent += 1
            if has_documents:
                has_rag += 1
            if answer_has_content and not answer_has_denial:
                has_answer += 1
            if answer_has_citation:
                has_citation += 1
            if answer_has_denial or not answer_has_content:
                no_results += 1

            # Progress indicator
            if idx % 10 == 0:
                self.stdout.write(f"  Processed {idx}/{len(all_questions)} questions...")

        # Print summary
        total = len(all_questions)
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Coverage Test Summary"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total questions tested: {total}")
        self.stdout.write(f"Intent accuracy: {correct_intent}/{total} ({100*correct_intent/total:.1f}%)")
        self.stdout.write(f"RAG retrieval success: {has_rag}/{total} ({100*has_rag/total:.1f}%)")
        self.stdout.write(f"Answer generated (no denial): {has_answer}/{total} ({100*has_answer/total:.1f}%)")
        self.stdout.write(f"Answer has citations: {has_citation}/{total} ({100*has_citation/total:.1f}%)")
        self.stdout.write(f"Failed (denial or empty): {no_results}/{total} ({100*no_results/total:.1f}%)")

        # Show some examples of failures
        failures = [r for r in results if r["has_denial"] or not r["has_documents"]]
        if failures:
            self.stdout.write("\n" + self.style.WARNING("Sample failures:"))
            for failure in failures[:5]:
                self.stdout.write(f"  Q: {failure['question'][:60]}...")
                self.stdout.write(f"    Intent: {failure['detected_intent']} (expected: {failure['expected_intent']})")
                self.stdout.write(f"    Count: {failure['count']}, Has denial: {failure['has_denial']}")

        # Calculate coverage percentage (questions that got valid answers)
        coverage = (has_answer / total) * 100 if total > 0 else 0
        self.stdout.write("\n" + "=" * 60)
        if coverage >= 90:
            self.stdout.write(self.style.SUCCESS(f"✅ Coverage: {coverage:.1f}% (EXCELLENT)"))
        elif coverage >= 75:
            self.stdout.write(self.style.WARNING(f"⚠️ Coverage: {coverage:.1f}% (GOOD)"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Coverage: {coverage:.1f}% (NEEDS IMPROVEMENT)"))
        self.stdout.write("=" * 60)

