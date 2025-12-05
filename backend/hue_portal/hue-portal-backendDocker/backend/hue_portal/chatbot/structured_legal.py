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
    # Reduced from 5 to 3 chunks to fit within 2048 token context window
    for idx, doc in enumerate(documents[:3], 1):
        document = getattr(doc, "document", None)
        title = getattr(document, "title", "") or "Không rõ tên văn bản"
        code = getattr(document, "code", "") or "N/A"
        section_code = getattr(doc, "section_code", "") or "Không rõ điều"
        section_title = getattr(doc, "section_title", "") or ""
        page_range = _format_page_range(doc)
        content = getattr(doc, "content", "") or ""
        # Reduced snippet from 800 to 500 chars to fit context window
        snippet = (content[:500] + "...") if len(content) > 500 else content

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
    # Reduced from 5 to 3 chunks to match doc_blocks
    for doc in documents[:3]:
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
        Bạn là chuyên gia tư vấn về xử lí kỷ luật cán bộ đảng viên của Phòng Thanh Tra - Công An Thành Phố Huế. Chỉ trả lời dựa trên context được cung cấp, không suy diễn hay tạo thông tin mới.

        Câu hỏi: {query}

        Context được sắp xếp theo độ liên quan giảm dần (tài liệu #1 là liên quan nhất):
        {docs_text}

        Bảng tham chiếu (chỉ sử dụng đúng tên/mã dưới đây):
        {reference_text}

        Quy tắc bắt buộc:
        1. CHỈ trả lời dựa trên thông tin trong context ở trên, không tự tạo hoặc suy đoán.
        2. Phải nhắc rõ văn bản (ví dụ: Thông tư 02 về xử lý điều lệnh trong CAND) và mã điều/khoản chính xác (ví dụ: Điều 7, Điều 8).
        3. Nếu câu hỏi về tỷ lệ phần trăm, hạ bậc thi đua, xếp loại → phải tìm đúng điều khoản quy định về tỷ lệ đó.
        4. Nếu KHÔNG tìm thấy thông tin về tỷ lệ %, hạ bậc thi đua trong context → trả lời rõ: "Thông tư 02 không quy định xử lý đơn vị theo tỷ lệ phần trăm vi phạm trong năm" (đừng trích bừa điều khoản khác).
        5. Cấu trúc trả lời:
           - SUMMARY: Tóm tắt ngắn gọn kết luận chính, nhắc văn bản và điều khoản áp dụng
           - DETAILS: Tối thiểu 2 bullet, mỗi bullet phải có mã điều/khoản và nội dung cụ thể
           - CITATIONS: Danh sách trích dẫn với document_title, section_code, snippet ≤500 ký tự
        6. Tuyệt đối không chép lại schema hay thêm khóa "$defs"; chỉ xuất đối tượng JSON cuối cùng.
        7. Chỉ in ra CHÍNH XÁC một JSON object, không thêm chữ 'json', không dùng ``` hoặc văn bản thừa.

        Ví dụ định dạng:
        {{
          "summary": "Theo Thông tư 02 về xử lý điều lệnh trong CAND, đơn vị có 12% cán bộ vi phạm điều lệnh trong năm sẽ bị hạ 1 bậc thi đua (Điều 7).",
          "details": [
            "- Điều 7 quy định: Đơn vị có từ 10% đến dưới 20% cán bộ vi phạm điều lệnh trong năm sẽ bị hạ 1 bậc thi đua.",
            "- Điều 8 quy định: Đơn vị có từ 20% trở lên cán bộ vi phạm điều lệnh trong năm sẽ bị hạ 2 bậc thi đua."
          ],
            "citations": [
              {{
              "document_title": "Thông tư 02 về xử lý điều lệnh trong CAND",
              "section_code": "Điều 7",
              "page_range": "5-6",
              "summary": "Quy định về hạ bậc thi đua theo tỷ lệ vi phạm",
              "snippet": "Đơn vị có từ 10% đến dưới 20% cán bộ vi phạm điều lệnh trong năm sẽ bị hạ 1 bậc thi đua..."
              }}
            ]
          }}

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

