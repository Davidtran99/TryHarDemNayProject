"""
Domain-specific knowledge for clarification prompts.
"""
from __future__ import annotations

from typing import List, Dict


DOCUMENT_TOPICS: List[Dict[str, str]] = [
    {
        "code": "264-QD-TW",
        "title": "Quy định 264/QĐ-TW (sửa đổi, bổ sung Quy định 69/QĐ-TW)",
        "doc_type": "Quy định",
        "summary": "Văn bản của Ban Chấp hành Trung ương về kỷ luật tổ chức đảng, thay thế quy định 69.",
        "keywords": [
            "264",
            "quy định 264",
            "qd 264",
            "đảng",
            "tổ chức đảng",
            "kỷ luật đảng",
            "ban chấp hành trung ương",
        ],
    },
    {
        "code": "QD-69-TW",
        "title": "Quy định 69/QĐ-TW về kỷ luật tổ chức đảng, đảng viên vi phạm",
        "doc_type": "Quy định",
        "summary": "Quy định kỷ luật của Đảng ban hành năm 2022, nền tảng cho xử lý kỷ luật đảng viên.",
        "keywords": [
            "69",
            "qd 69",
            "quy định 69",
            "kỷ luật đảng viên",
            "kỷ luật cán bộ",
            "vi phạm đảng",
        ],
    },
    {
        "code": "TT-02-CAND",
        "title": "Thông tư 02/2021/TT-BCA về xử lý điều lệnh trong Công an nhân dân",
        "doc_type": "Thông tư",
        "summary": "Quy định xử lý vi phạm điều lệnh, hạ bậc thi đua đối với đơn vị thuộc CAND.",
        "keywords": [
            "thông tư 02",
            "tt 02",
            "điều lệnh",
            "công an",
            "cand",
            "thi đua",
            "đơn vị",
        ],
    },
    {
        "code": "TT-02-BIEN-SOAN",
        "title": "Thông tư 02/2018/TT-BCA (Biên soạn) về soạn thảo văn bản",
        "doc_type": "Thông tư",
        "summary": "Hướng dẫn biên soạn, trình bày văn bản thuộc Bộ Công an.",
        "keywords": [
            "biên soạn",
            "soạn thảo",
            "thông tư 02 biên soạn",
        ],
    },
]


def find_topic_by_code(code: str) -> Dict[str, str] | None:
    code_upper = code.strip().upper()
    for topic in DOCUMENT_TOPICS:
        if topic["code"].upper() == code_upper:
            return topic
    return None

