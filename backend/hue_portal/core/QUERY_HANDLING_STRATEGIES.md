# Chiến lược xử lý câu hỏi khó và edge cases

## Tổng quan

Hệ thống đã được cải thiện với nhiều lớp fallback để đảm bảo chatbot luôn có thể trả lời, ngay cả với các câu hỏi khó hoặc edge cases.

## Phân loại 3 nhóm câu hỏi chính

| Nhóm câu hỏi | Cách nhận biết | Hướng xử lý |
|--------------|----------------|-------------|
| **Chào hỏi / lặt vặt** | Câu ngắn (≤3 từ) chứa các cụm “xin chào”, “hello”, “mệt quá”, “chém gió”… và **không** chứa từ khóa nghiệp vụ | Router (`router.py`) chuyển sang `IntentRoute.GREETING/SMALL_TALK`, chatbot trả template tức thì, **bỏ qua RAG** |
| **Nghiệp vụ thường gặp** (mức phạt, thủ tục, đơn vị, cảnh báo) | Từ khóa chuyên biệt (`mức phạt`, `thủ tục`, `địa chỉ`, `cảnh báo`…) hoặc ML model confidence > 0.65 | Router ép intent tương ứng (`search_fine/procedure/office/advisory`), gọi `search_by_intent` và chuẩn hóa kết quả (min/max fine, dossier…) |
| **Văn bản trong DB** | Từ khóa pháp lý (“quyết định”, “thông tư”…), mã hiệu (`264-QĐ-TW`, `TT-02-CAND`) hoặc doc-code regex | Router force `search_legal`, `retrieve_top_k_documents` mở rộng query (synonym + doc code) rồi chạy hybrid search + RAG; Guardrails đảm bảo structured answer |

> Logic chi tiết: `chatbot.py` mở rộng bộ từ khóa, `router.py` bổ sung keyword flags + override intent, `rag.py` kết hợp `expand_query_semantically` + `expand_query_with_synonyms` để không bỏ sót văn bản.

## Các chiến lược đã triển khai

### 1. Multi-step Query Reformulation (`query_reformulation.py`)

#### 1.1. Query Simplification
- Loại bỏ stopwords (là, gì, bao nhiêu, v.v.)
- Giữ lại các từ khóa quan trọng
- Ví dụ: "Theo quyết định 69 thì đảng viên bị xử lý sao?" → "quyết định 69 đảng viên xử lý"

#### 1.2. Key Terms Extraction
- Trích xuất mã văn bản (QD-69-TW, 264-QD-TW, TT-02-CAND)
- Trích xuất số điều/khoản
- Trích xuất từ khóa pháp lý (kỷ luật, đảng viên, xử lý)

#### 1.3. Multiple Reformulations
- Tạo nhiều phiên bản query:
  - Simplified version
  - Key terms only
  - Without question words
  - With expanded abbreviations

### 2. Multi-step Retrieval Fallback (`rag.py`)

#### 2.1. Primary Search
- Thử query gốc trước
- Sử dụng hybrid search (BM25 + vector)

#### 2.2. Reformulation Search
- Nếu không có kết quả, thử các reformulations
- Thứ tự ưu tiên:
  1. Simplified query
  2. Key terms only
  3. Document code search (nếu có mã văn bản)

#### 2.3. Document Code Search
- Nếu query chứa mã văn bản, tìm tất cả sections trong document đó
- Sử dụng threshold rất thấp (0.01) để đảm bảo có kết quả

### 3. LLM-based Query Reformulation

#### 3.1. Intelligent Reformulation
- Sử dụng LLM để reformulate query phức tạp
- Tạo 3-5 phiên bản đơn giản hóa
- Tập trung vào mã văn bản và từ khóa chính

#### 3.2. Fallback Answer Generation
- Nếu không tìm thấy documents, LLM vẫn có thể trả lời dựa trên general knowledge
- Kèm disclaimer rõ ràng về nguồn thông tin

### 4. User Guidance System

#### 4.1. Query Improvement Suggestions
- Phân tích query và đưa ra gợi ý cụ thể:
  - Thêm mã văn bản
  - Sử dụng từ khóa chính
  - Nhắc đến số điều/khoản

#### 4.2. Context-aware Suggestions
- Gợi ý khác nhau tùy theo intent:
  - `search_legal`: Gợi ý mã văn bản, số điều
  - `search_fine`: Gợi ý mô tả vi phạm
  - `search_procedure`: Gợi ý tên thủ tục

### 5. Answer Generation Fallbacks

#### 5.1. Structured Answer (Priority 1)
- Sử dụng Guardrails + JSON schema
- Đảm bảo format chuẩn và có citations

#### 5.2. Template-based Answer (Priority 2)
- Nếu structured answer fail, dùng template
- Vẫn có citations và format đúng

#### 5.3. LLM General Answer (Priority 3)
- Nếu không có documents, LLM vẫn trả lời
- Kèm disclaimer và suggestions

#### 5.4. Guidance Message (Priority 4)
- Nếu tất cả fail, cung cấp hướng dẫn
- Gợi ý cách cải thiện query
- Hướng dẫn liên hệ cơ quan

## Flow xử lý câu hỏi

```
User Query
    ↓
Intent Classification
    ↓
Primary Search (original query)
    ↓
[No results?] → Reformulation Search
    ↓
[No results?] → Key Terms Search
    ↓
[No results?] → Document Code Search
    ↓
[No results?] → LLM Reformulation Search
    ↓
[No results?] → LLM General Answer (with disclaimer)
    ↓
[Still no answer?] → Guidance Message
```

## Các trường hợp được xử lý

### ✅ Câu hỏi có mã văn bản
- "QD 69 quy định gì?"
- "Theo quyết định 264 thì..."
- **Xử lý**: Extract document code → Filter by code → Search within document

### ✅ Câu hỏi phức tạp, dài
- "Theo quyết định 69 thì đảng viên vi phạm kỷ luật sẽ bị xử lý như thế nào?"
- **Xử lý**: Simplify → Extract key terms → Multiple reformulations

### ✅ Câu hỏi thiếu context
- "Kỷ luật đảng viên"
- **Xử lý**: Add document codes → Expand with legal keywords → Broader search

### ✅ Câu hỏi không có trong DB
- "Quy định về nghỉ phép"
- **Xử lý**: LLM general answer + Disclaimer + Suggestions

### ✅ Câu hỏi ambiguous
- "Xử lý vi phạm"
- **Xử lý**: Try multiple interpretations → Provide guidance

## Logging và Monitoring

Tất cả các bước đều được log chi tiết:
- `[RAG] ⚠️ No results for original query, trying reformulations...`
- `[RAG] 🔄 Trying reformulated query: '...'`
- `[RAG] ✅ Reformulation found N results`
- `[RAG] 📝 Generating LLM-based general answer with disclaimer`

## Cải thiện trong tương lai

1. **Learning từ user feedback**: Ghi nhận queries fail và cải thiện reformulation
2. **Semantic expansion**: Sử dụng word embeddings để expand synonyms
3. **Context-aware reformulation**: Sử dụng conversation history để reformulate
4. **Confidence scoring**: Đánh giá confidence của từng reformulation
5. **A/B testing**: Test các strategies khác nhau để tối ưu


