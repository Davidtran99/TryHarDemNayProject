# Kiểm tra API Mode

## Vấn đề
Response hiện tại là template-based, không phải từ LLM API mode.

## Đã làm
1. ✅ Cấu hình đã đúng: `LLM_PROVIDER=api`
2. ✅ Test trực tiếp API mode hoạt động
3. ✅ Đã thêm logging vào RAG pipeline để debug

## Cách kiểm tra

### 1. Kiểm tra server logs
Khi gửi request, xem logs có:
- `[RAG] Using LLM provider: api`
- `[LLM] Generating answer with provider: api`
- `[LLM] ✅ Answer generated successfully` hoặc error

### 2. Test trực tiếp
```bash
curl -X POST http://localhost:8000/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Mức phạt vượt đèn đỏ là bao nhiêu?", "reset_session": false}'
```

### 3. Kiểm tra trong code
- RAG pipeline gọi `llm.generate_answer()` với `use_llm=True`
- LLM generator có `provider == "api"`
- `_generate_api()` được gọi với query

## Nguyên nhân có thể

1. **API timeout**: HF Spaces API có thể timeout
2. **API trả về None**: API có thể trả về None và fallback về template
3. **LLM không available**: `get_llm_generator()` có thể trả về None

## Giải pháp

Nếu API mode không hoạt động:
1. Kiểm tra Hugging Face Space có đang chạy không
2. Kiểm tra internet connection
3. Kiểm tra API URL có đúng không
4. Xem server logs để biết lỗi cụ thể




