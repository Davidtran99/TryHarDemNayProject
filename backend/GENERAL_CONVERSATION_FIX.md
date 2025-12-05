# Sửa Chatbot để Hỗ trợ General Conversation

## Vấn đề

Chatbot không trả lời được như một chatbot AI thông thường vì:
1. **Chỉ gọi LLM khi có documents** → Không thể trả lời general queries
2. **Trả về error message ngay khi không có documents** → Không cho LLM cơ hội trả lời

## Giải pháp đã áp dụng

### 1. Sửa `rag.py` - Cho phép LLM trả lời ngay cả khi không có documents

**File:** `backend/hue_portal/core/rag.py`

**Thay đổi:**
- Trước: Trả về error message ngay khi không có documents
- Sau: Gọi LLM ngay cả khi không có documents (general conversation mode)

```python
# Trước:
if not documents:
    return error_message  # ← Không gọi LLM

# Sau:
# Gọi LLM trước (ngay cả khi không có documents)
if use_llm:
    llm_answer = llm.generate_answer(query, context=context, documents=documents if documents else [])
    if llm_answer:
        return llm_answer

# Chỉ trả về error nếu không có LLM và không có documents
if not documents:
    return error_message
```

### 2. Sửa `llm_integration.py` - Prompt cho general conversation

**File:** `backend/hue_portal/chatbot/llm_integration.py`

**Thay đổi:**
- Nếu có documents → Yêu cầu trả lời dựa trên documents (strict mode)
- Nếu không có documents → Cho phép general conversation (friendly mode)

```python
if documents:
    # Strict mode: chỉ trả lời dựa trên documents
    prompt_parts.extend([...])
else:
    # General conversation mode
    prompt_parts.extend([
        "- Trả lời câu hỏi một cách tự nhiên và hữu ích như một chatbot AI thông thường",
        "- Nếu câu hỏi liên quan đến pháp luật nhưng không có thông tin, hãy nói rõ",
        ...
    ])
```

### 3. Sửa `rag_pipeline` - Luôn gọi generate_answer_template

**File:** `backend/hue_portal/core/rag.py`

**Thay đổi:**
- Trước: Trả về error ngay khi không có documents
- Sau: Luôn gọi `generate_answer_template` để cho LLM cơ hội trả lời

```python
# Trước:
if not documents:
    return {'answer': error_message, ...}  # ← Không gọi LLM

# Sau:
# Luôn gọi generate_answer_template (sẽ gọi LLM nếu có)
answer = generate_answer_template(query, documents, content_type, context=context, use_llm=use_llm)
```

### 4. Sửa `chatbot.py` - Sử dụng answer từ LLM ngay cả khi count=0

**File:** `backend/hue_portal/chatbot/chatbot.py`

**Thay đổi:**
- Trước: Chỉ sử dụng RAG result nếu `count > 0`
- Sau: Sử dụng answer từ LLM ngay cả khi `count = 0`

```python
# Trước:
if rag_result["count"] > 0 and rag_result["confidence"] >= confidence:
    # Sử dụng answer

# Sau:
if rag_result.get("answer") and (rag_result["count"] > 0 or rag_result.get("answer", "").strip()):
    # Sử dụng answer (kể cả khi count=0)
```

## Kết quả

✅ **LLM được gọi ngay cả khi không có documents**
- Logs cho thấy: `[RAG] Using LLM provider: api`
- Logs cho thấy: `[LLM] 🔗 Calling API: ...`

⚠️ **API trả về 500 error**
- Có thể do HF Spaces API đang gặp lỗi
- Hoặc prompt quá dài
- Cần kiểm tra HF Spaces logs

## Cách test

1. **Test với general query:**
```bash
curl -X POST http://localhost:8000/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"mấy giờ rồi","reset_session":false}'
```

2. **Xem logs:**
```bash
tail -f /tmp/django_general_conv.log | grep -E "\[RAG\]|\[LLM\]"
```

3. **Kiểm tra LLM có được gọi:**
- Tìm: `[RAG] Using LLM provider: api`
- Tìm: `[LLM] 🔗 Calling API: ...`

## Lưu ý

- **API mode cần HF Spaces hoạt động** → Nếu API trả về 500, cần kiểm tra HF Spaces
- **Local mode** sẽ hoạt động tốt hơn nếu có GPU
- **General conversation** chỉ hoạt động khi LLM available




