"""
Structured legal answer helpers using LangChain output parsers.
"""

from __future__ import annotations

import json
import logging
import textwrap
from functools import lru_cache
from typing import List, Optional, Sequence

from langchain.output_parsers import PydanticOutputParser
from langchain.schema import OutputParserException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LegalCitation(BaseModel):
    """Single citation item pointing back to a legal document."""

    document_title: str = Field(..., description="Tên văn bản pháp luật.")
    section_code: str = Field(..., description="Mã điều/khoản được trích dẫn.")
    page_range: Optional[str] = Field(
        None, description="Trang hoặc khoảng trang trong tài liệu."
    )
    summary: str = Field(
        ...,
        description="1-2 câu mô tả nội dung chính của trích dẫn, phải liên quan trực tiếp câu hỏi.",
    )
    snippet: str = Field(
        ..., description="Trích đoạn ngắn gọn (≤500 ký tự) lấy từ tài liệu gốc."
    )


class LegalAnswer(BaseModel):
    """Structured answer returned by the LLM."""

    summary: str = Field(
        ...,
        description="Đoạn mở đầu tóm tắt kết luận chính, phải nhắc văn bản áp dụng (ví dụ Quyết định 69/QĐ-TW).",
    )
    details: List[str] = Field(
        ...,
        description="Tối thiểu 2 gạch đầu dòng mô tả từng hình thức/điều khoản. Mỗi gạch đầu dòng phải nhắc mã điều hoặc tên văn bản.",
    )
    citations: List[LegalCitation] = Field(
        ...,
        description="Danh sách trích dẫn; phải có ít nhất 1 phần tử tương ứng với các tài liệu đã cung cấp.",
    )


@lru_cache(maxsize=1)
def get_legal_output_parser() -> PydanticOutputParser:
    """Return cached parser to enforce structured output."""

    return PydanticOutputParser(pydantic_object=LegalAnswer)


def build_structured_legal_prompt(
    query: str,
    documents: Sequence,
    parser: PydanticOutputParser,
    prefill_summary: Optional[str] = None,
    retry_hint: Optional[str] = None,
) -> str:
    """Construct prompt instructing the LLM to return structured JSON."""

    doc_blocks = []
    for idx, doc in enumerate(documents[:5], 1):
        document = getattr(doc, "document", None)
        title = getattr(document, "title", "") or "Không rõ tên văn bản"
        code = getattr(document, "code", "") or "N/A"
        section_code = getattr(doc, "section_code", "") or "Không rõ điều"
        section_title = getattr(doc, "section_title", "") or ""
        page_range = _format_page_range(doc)
        content = getattr(doc, "content", "") or ""
        snippet = (content[:800] + "...") if len(content) > 800 else content

        block = textwrap.dedent(
            f"""
            TÀI LIỆU #{idx}
            Văn bản: {title} (Mã: {code})
            Điều/khoản: {section_code} - {section_title}
            Trang: {page_range or 'Không rõ'}
            Trích đoạn:
            {snippet}
            """
        ).strip()
        doc_blocks.append(block)

    docs_text = "\n\n".join(doc_blocks)
    reference_lines = []
    title_section_pairs = []
    for doc in documents[:5]:
        document = getattr(doc, "document", None)
        title = getattr(document, "title", "") or "Không rõ tên văn bản"
        section_code = getattr(doc, "section_code", "") or "Không rõ điều"
        reference_lines.append(f"- {title} | {section_code}")
        title_section_pairs.append((title, section_code))
    reference_text = "\n".join(reference_lines)
    prefill_block = ""
    if prefill_summary:
        prefill_block = textwrap.dedent(
            f"""
            Bản tóm tắt tiếng Việt đã có sẵn (hãy dùng lại, diễn đạt ngắn gọn hơn, KHÔNG thêm thông tin mới):
            {prefill_summary.strip()}
            """
        ).strip()
    format_instructions = parser.get_format_instructions()
    retry_hint_block = ""
    if retry_hint:
        retry_hint_block = textwrap.dedent(
            f"""
            Nhắc lại: {retry_hint.strip()}
            """
        ).strip()

    prompt = textwrap.dedent(
        f"""
        Bạn là trợ lý pháp lý của Công an Thừa Thiên Huế. Nhiệm vụ: dựa trên các trích đoạn dưới đây để trả lời câu hỏi của người dân.

        Quy tắc bắt buộc:
        - Không được bịa đặt thông tin ngoài tài liệu.
        - Phải nhắc rõ văn bản (ví dụ: Quyết định 69/QĐ-TW) và mã điều/khoản trong phần trả lời.
        - Cấu trúc trả lời: SUMMARY ngắn gọn -> DETAILS dạng bullet -> CITATIONS chứa thông tin nguồn.
        - Nếu không đủ thông tin, ghi rõ lý do ở phần summary và để danh sách citations rỗng.
        - Tuyệt đối không chép lại schema hay thêm khóa "$defs"; chỉ xuất đối tượng JSON cuối cùng theo mẫu dưới đây.
        - Chỉ in ra CHÍNH XÁC một JSON object, không được thêm chữ 'json', không dùng ``` hoặc văn bản thừa trước/sau.
        - Mỗi bullet DETAILS bắt buộc phải chứa tên văn bản và mã điều/khoản đúng như trong “Bảng tham chiếu” phía dưới.
        - Không được tạo thêm hình thức kỷ luật hoặc điều khoản không xuất hiện trong tài liệu. Nếu không thấy điều/khoản, ghi rõ “(không nêu điều cụ thể)”.
        - Ví dụ định dạng:
          {{
            "summary": "Tóm tắt ...",
            "details": ["- Điều 5 ...", "- Điều 7 ..."],
            "citations": [
              {{
                "document_title": "Quyết định 69/QĐ-TW",
                "section_code": "Điều 5",
                "page_range": "1-2",
                "summary": "Mô tả ngắn gọn",
                "snippet": "Trích dẫn ≤500 ký tự"
              }}
            ]
          }}

        Câu hỏi người dùng: {query}

        Bảng tham chiếu bắt buộc (chỉ sử dụng đúng tên/mã dưới đây):
        {reference_text}

        Các trích đoạn pháp luật:
        {docs_text}

        {prefill_block}

        {retry_hint_block}

        {format_instructions}
        """
    ).strip()

    return prompt


def format_structured_legal_answer(answer: LegalAnswer) -> str:
    """Convert structured answer into human-friendly text with citations."""

    lines: List[str] = []
    if answer.summary:
        lines.append(answer.summary.strip())

    if answer.details:
        lines.append("")
        lines.append("Chi tiết chính:")
        for bullet in answer.details:
            lines.append(f"- {bullet.strip()}")

    if answer.citations:
        lines.append("")
        lines.append("Trích dẫn chi tiết:")
        for idx, citation in enumerate(answer.citations, 1):
            page_text = f" (Trang: {citation.page_range})" if citation.page_range else ""
            lines.append(
                f"{idx}. {citation.document_title} – {citation.section_code}{page_text}"
            )
            lines.append(f"   Tóm tắt: {citation.summary.strip()}")
            lines.append(f"   Trích đoạn: {citation.snippet.strip()}")

    return "\n".join(lines).strip()


def _format_page_range(doc: object) -> Optional[str]:
    start = getattr(doc, "page_start", None)
    end = getattr(doc, "page_end", None)
    if start and end:
        if start == end:
            return str(start)
        return f"{start}-{end}"
    if start:
        return str(start)
    if end:
        return str(end)
    return None


def parse_structured_output(
    parser: PydanticOutputParser, raw_output: str
) -> Optional[LegalAnswer]:
    """Parse raw LLM output to LegalAnswer if possible."""

    if not raw_output:
        return None
    try:
        return parser.parse(raw_output)
    except OutputParserException:
        snippet = raw_output.strip().replace("\n", " ")
        logger.warning(
            "[LLM] Structured parse failed. Preview: %s",
            snippet[:400],
        )
        json_candidate = _extract_json_block(raw_output)
        if json_candidate:
            try:
                return parser.parse(json_candidate)
            except OutputParserException:
                logger.warning("[LLM] JSON reparse also failed.")
                return None
        return None


def _extract_json_block(text: str) -> Optional[str]:
    """
    Best-effort extraction of the first JSON object within text.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.lstrip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip("`").strip()

    start = text.find("{")
    if start == -1:
        return None

    stack = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "{":
            stack += 1
        elif char == "}":
            stack -= 1
            if stack == 0:
                payload = text[start : idx + 1]
                # Remove code fences if present
                payload = payload.strip()
                if payload.startswith("```"):
                    payload = payload.strip("`").strip()
                try:
                    json.loads(payload)
                    return payload
                except json.JSONDecodeError:
                    return None
    return None

