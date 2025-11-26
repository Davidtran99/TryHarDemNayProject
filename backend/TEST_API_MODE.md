# Hướng dẫn Test API Mode

## Vấn đề hiện tại
- HF Spaces không nhận được request từ project local
- Response vẫn là template-based (không phải từ LLM)

## Đã sửa
1. ✅ API mode giờ gửi `prompt` (có documents) thay vì chỉ `query`
2. ✅ Đã thêm logging chi tiết: `[LLM] 🔗 Calling API`, `[RAG] Using LLM provider`

## Cách test

### 1. Fix database error (nếu cần)
```bash
# Kiểm tra PostgreSQL có đang chạy không
psql -h localhost -p 5543 -U hue -d hue_portal

# Hoặc dùng SQLite tạm thời (sửa settings.py)
```

### 2. Start server với env đúng
```bash
cd /Users/davidtran/Downloads/TryHarDemNayProject/backend
source venv/bin/activate
cd hue_portal

# Kiểm tra env
cat ../.env | grep LLM

# Start server
python3 manage.py runserver 0.0.0.0:8000
```

### 3. Test API mode
```bash
# Test với câu hỏi có documents
curl -X POST http://localhost:8000/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Mức phạt vượt đèn đỏ là bao nhiêu?", "reset_session": false}'
```

### 4. Xem server logs
Tìm các logs sau:
- `[RAG] Using LLM provider: api` - LLM được gọi
- `[LLM] 🔗 Calling API: https://davidtran999-hue-portal-backend.hf.space/api/chatbot/chat/` - Đang gọi HF Spaces
- `[LLM] 📥 Response status: 200` - HF Spaces trả về response
- `[LLM] ✅ Got message from API` - Nhận được message từ API

Nếu KHÔNG thấy logs này:
- LLM không được gọi (check `use_llm=True`)
- LLM generation fail (xem error logs)
- LLM not available (check `get_llm_generator()`)

## Debug checklist

- [ ] Server start thành công (không có database error)
- [ ] `.env` có `LLM_PROVIDER=api` và `HF_API_BASE_URL=...`
- [ ] Server load đúng env (restart sau khi sửa `.env`)
- [ ] Test với câu hỏi có documents (không phải greeting)
- [ ] Xem server logs để tìm `[LLM]` và `[RAG]` logs
- [ ] Kiểm tra HF Spaces có đang chạy không

## Nếu vẫn không hoạt động

1. **Kiểm tra LLM có được gọi không:**
   - Xem logs `[RAG] Using LLM provider: api`
   - Nếu không có, check `use_llm=True` trong `rag_pipeline()`

2. **Kiểm tra API call:**
   - Xem logs `[LLM] 🔗 Calling API: ...`
   - Nếu không có, check `_generate_api()` có được gọi không

3. **Kiểm tra response:**
   - Xem logs `[LLM] 📥 Response status: ...`
   - Nếu 200, check response content
   - Nếu error, xem error message

4. **Test trực tiếp API:**
```bash
curl -X POST https://davidtran999-hue-portal-backend.hf.space/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Test", "reset_session": false}'
```
