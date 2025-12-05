from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from django.core.management.base import BaseCommand

from hue_portal.core.models import LegalDocument, LegalSection
from hue_portal.chatbot.training.generated_qa import QAItem, DifficultyLevel


class Command(BaseCommand):
    """
    Generate synthetic legal questions from LegalDocument/LegalSection.

    This command is intentionally deterministic and lightweight so it can
    run on Hugging Face Spaces without requiring external LLM APIs.

    It creates one JSON file per legal document under:
        backend/hue_portal/chatbot/training/generated_qa/<document_code>.json

    Each JSON file contains a list[QAItem] as defined in
    `hue_portal.chatbot.training.generated_qa`.
    """

    help = "Generate synthetic legal questions for training intent models"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit-sections",
            type=int,
            default=0,
            help="Optional limit of sections per document to generate questions for (0 = all).",
        )
        parser.add_argument(
            "--max-questions-per-doc",
            type=int,
            default=400,
            help="Soft cap for questions per document (approximate).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ kiểm tra kết nối DB và thoát mà không ghi file.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        limit_sections: int = options["limit_sections"]
        max_questions_per_doc: int = options["max_questions_per_doc"]
        dry_run: bool = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: bỏ qua bước generate file, chỉ kiểm tra truy cập DB."))
            if LegalDocument.objects.exists():
                self.stdout.write(self.style.SUCCESS("Dry-run thành công: truy vấn LegalDocument OK."))
            else:
                self.stdout.write(self.style.WARNING("Dry-run: không có LegalDocument nào trong DB."))
            return

        base_dir = Path(__file__).resolve().parents[4] / "chatbot" / "training" / "generated_qa"
        base_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.MIGRATE_HEADING("Generating legal questions from DB..."))

        for document in LegalDocument.objects.all().order_by("code"):
            questions: List[QAItem] = []

            # Global, high-level questions for the document
            questions.extend(self._build_document_level_questions(document))

            sections_qs = document.sections.order_by("order")
            if limit_sections > 0:
                sections_qs = sections_qs[:limit_sections]

            for section in sections_qs:
                questions.extend(self._build_section_questions(document, section))
                if len(questions) >= max_questions_per_doc:
                    break

            # Deduplicate by question text
            unique_questions: Dict[str, QAItem] = {}
            for item in questions:
                q = item["question"].strip()
                if q not in unique_questions:
                    unique_questions[q] = item

            doc_filename = f"{document.code.replace('/', '_')}.json"
            output_path = base_dir / doc_filename
            output_path.write_text(
                json.dumps(list(unique_questions.values()), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated {len(unique_questions)} questions for document {document.code} -> {output_path.name}"
                )
            )

    def _build_document_level_questions(self, document: LegalDocument) -> List[QAItem]:
        """
        Build a small set of high-level questions about the document itself.
        """

        code = document.code
        title = document.title

        def make(question: str, difficulty: DifficultyLevel) -> QAItem:
            return QAItem(
                question=question,
                difficulty=difficulty,
                intent="search_legal",
                document_code=code,
                section_code="",
                document_title=title,
                section_title="",
            )

        questions: List[QAItem] = [
            # Basic document-level questions
            make(f"{code} quy định về vấn đề gì?", "basic"),
            make(f"Nội dung chính của văn bản {code} ({title}) là gì?", "basic"),
            make(f"Văn bản {code} quy định về điều gì?", "basic"),
            make(f"Quy định trong {code} về kỷ luật cán bộ, đảng viên là gì?", "basic"),
            make(f"{code} có những quy định gì về xử lý kỷ luật?", "basic"),
            # Medium document-level questions
            make(f"Đối tượng áp dụng của văn bản {code} là ai?", "medium"),
            make(f"Trong những trường hợp nào thì áp dụng quy định của {code}?", "medium"),
            make(f"Văn bản {code} áp dụng cho đối tượng nào?", "medium"),
            make(f"Khi nào cần áp dụng các quy định trong {code}?", "medium"),
            make(f"Quy định trong {code} về hình thức kỷ luật là gì?", "medium"),
            make(f"Theo {code}, các hình thức kỷ luật bao gồm những gì?", "medium"),
            # Advanced document-level questions
            make(
                f"Làm thế nào để tra cứu nhanh các hình thức kỷ luật trong văn bản {code}?",
                "advanced",
            ),
            make(
                f"Điểm khác biệt giữa {code} và các văn bản quy định kỷ luật khác là gì?",
                "advanced",
            ),
            make(
                f"Quy trình xử lý kỷ luật theo {code} được thực hiện như thế nào?",
                "advanced",
            ),
        ]
        return questions

    def _build_section_questions(
        self, document: LegalDocument, section: LegalSection
    ) -> List[QAItem]:
        """
        Build several template-based questions for a given section.

        These questions are deliberately simple but cover different
        phrasings and difficulty levels.
        """

        code = document.code
        title = document.title
        section_code = section.section_code
        section_title = section.section_title or ""

        display_section = section_code
        if section_title:
            display_section = f"{section_code} ({section_title})"

        def make(question: str, difficulty: DifficultyLevel) -> QAItem:
            return QAItem(
                question=question,
                difficulty=difficulty,
                intent="search_legal",
                document_code=code,
                section_code=section_code,
                document_title=title,
                section_title=section_title,
            )

        questions: List[QAItem] = [
            # Basic questions
            make(
                f"Theo {code}, {display_section} quy định nội dung gì liên quan đến kỷ luật cán bộ, đảng viên?",
                "basic",
            ),
            make(
                f"Quy định trong {code} về {display_section} là gì?",
                "basic",
            ),
            make(
                f"{display_section} của {code} quy định về vấn đề gì?",
                "basic",
            ),
            make(
                f"Nội dung của {display_section} trong {code} là gì?",
                "basic",
            ),
            # Medium questions
            make(
                f"Trong văn bản {code}, {display_section} áp dụng cho những hành vi vi phạm nào?",
                "medium",
            ),
            make(
                f"Nếu cán bộ, đảng viên vi phạm như nội dung tại {display_section} của {code} thì sẽ bị xử lý ra sao?",
                "medium",
            ),
            make(
                f"Quy định tại {display_section} của {code} về hình thức kỷ luật là gì?",
                "medium",
            ),
            make(
                f"Theo {code}, khi nào áp dụng quy định tại {display_section}?",
                "medium",
            ),
            make(
                f"Trong {code}, {display_section} quy định mức kỷ luật nào?",
                "medium",
            ),
            make(
                f"Nếu vi phạm theo {display_section} của {code} thì bị xử lý như thế nào?",
                "medium",
            ),
            # Advanced questions
            make(
                f"So với các điều khoản khác trong {code}, quy định tại {display_section} có điểm gì đặc biệt về hình thức kỷ luật?",
                "advanced",
            ),
            make(
                f"Làm thế nào để tra cứu nhanh quy định tại {display_section} trong văn bản {code}?",
                "advanced",
            ),
            make(
                f"Điểm khác biệt giữa {display_section} và các điều khoản khác trong {code} là gì?",
                "advanced",
            ),
        ]
        return questions


