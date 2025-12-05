# Fix: Server đang dùng Local LLM thay vì API Mode

## Vấn đề
Khi test chat trên web, server đang chạy local LLM trên máy thay vì gọi HF Spaces API.

## Nguyên nhân
1. **Global instance cache:** `get_llm_generator()` sử dụng global instance `_llm_generator` chỉ tạo một lần
2. **Server start với env cũ:** Nếu server start với `LLM_PROVIDER=local`, instance sẽ giữ provider=local
3. **Không reload khi env thay đổi:** Khi `.env` được update, server không tự động reload instance

## Đã sửa

### File: `backend/hue_portal/chatbot/llm_integration.py`

**Trước:**
```python
_llm_generator: Optional[LLMGenerator] = None

def get_llm_generator() -> Optional[LLMGenerator]:
    global _llm_generator
    if _llm_generator is None:
        _llm_generator = LLMGenerator()
    return _llm_generator if _llm_generator.is_available() else None
```

**Sau:**
```python
_llm_generator: Optional[LLMGenerator] = None
_last_provider: Optional[str] = None

def get_llm_generator() -> Optional[LLMGenerator]:
    """Get or create LLM generator instance.
    
    Recreates instance if provider changed (e.g., from local to api).
    """
    global _llm_generator, _last_provider
    
    # Get current provider from env
    current_provider = os.environ.get("LLM_PROVIDER", LLM_PROVIDER_NONE).lower()
    
    # Recreate if provider changed or instance doesn't exist
    if _llm_generator is None or _last_provider != current_provider:
        _llm_generator = LLMGenerator()
        _last_provider = current_provider
        print(f"[LLM] 🔄 Recreated LLM generator with provider: {current_provider}", flush=True)
    
    return _llm_generator if _llm_generator.is_available() else None
```

## Cách test

1. **Đảm bảo `.env` có đúng config:**
```bash
cd backend
cat .env | grep LLM
# Should show:
# LLM_PROVIDER=api
# HF_API_BASE_URL=https://davidtran999-hue-portal-backend.hf.space/api
```

2. **Restart server:**
```bash
pkill -f "manage.py runserver"
cd backend && source venv/bin/activate && cd hue_portal
python3 manage.py runserver 0.0.0.0:8000
```

3. **Test trong web UI:**
- Mở http://localhost:3000/chat
- Gửi câu hỏi: "Mức phạt vượt đèn đỏ là bao nhiêu?"
- Xem server logs để thấy:
  - `[LLM] 🔄 Recreated LLM generator with provider: api`
  - `[RAG] Using LLM provider: api`
  - `[LLM] 🔗 Calling API: https://davidtran999-hue-portal-backend.hf.space/api/chatbot/chat/`

4. **Kiểm tra response:**
- Response phải từ HF Spaces API (có văn bản tự nhiên, không phải template)
- KHÔNG thấy logs về local model loading

## Lưu ý

- Server sẽ tự động recreate LLM instance khi provider thay đổi
- Không cần restart server khi thay đổi `.env` (nhưng nên restart để đảm bảo)
- Nếu vẫn dùng local LLM, kiểm tra:
  - `.env` có `LLM_PROVIDER=api` không
  - Server có load đúng `.env` không
  - Xem server logs để biết provider nào đang được dùng




