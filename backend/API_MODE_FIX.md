# Sửa lỗi API Mode - HF Spaces không nhận được documents

## Vấn đề
Khi backend gọi HF Spaces API, nó chỉ gửi `query` đơn giản, không gửi `prompt` đã build từ documents. Do đó HF Spaces không nhận được thông tin từ documents đã retrieve.

## Đã sửa

### 1. `llm_integration.py` - Line 309
**Trước:**
```python
elif self.provider == LLM_PROVIDER_API:
    result = self._generate_api(query, context)
```

**Sau:**
```python
elif self.provider == LLM_PROVIDER_API:
    # For API mode, send the full prompt (with documents) as the message
    # This ensures HF Spaces receives all context from retrieved documents
    result = self._generate_api(prompt, context)
```

### 2. `llm_integration.py` - `_generate_api()` method
**Trước:**
```python
def _generate_api(self, query: str, context: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    payload = {
        "message": query,  # Chỉ gửi query đơn giản
        "reset_session": False
    }
```

**Sau:**
```python
def _generate_api(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    # Send the full prompt (with documents) as the message to HF Spaces
    payload = {
        "message": prompt,  # Gửi prompt đầy đủ có documents
        "reset_session": False
    }
```

### 3. Thêm logging chi tiết
- Log khi gọi API: `[LLM] 🔗 Calling API: ...`
- Log payload: `[LLM] 📤 Payload: ...`
- Log response: `[LLM] 📥 Response status: ...`
- Log errors chi tiết

## Cách test

1. **Restart backend server:**
```bash
pkill -f "manage.py runserver"
cd backend && source venv/bin/activate && cd hue_portal
python3 manage.py runserver 0.0.0.0:8000
```

2. **Test trong UI:**
- Mở http://localhost:3000
- Gửi câu hỏi: "Mức phạt vượt đèn đỏ là bao nhiêu?"
- Xem server logs để thấy:
  - `[RAG] Using LLM provider: api`
  - `[LLM] 🔗 Calling API: ...`
  - `[LLM] 📥 Response status: 200`
  - `[LLM] ✅ Got message from API`

3. **Kiểm tra response:**
- Response phải từ LLM (có văn bản tự nhiên, không phải template)
- Response phải chứa thông tin từ documents đã retrieve

## Lưu ý

- Prompt có thể dài (có documents), nhưng HF Spaces API hỗ trợ prompt dài
- Nếu timeout, có thể tăng timeout trong `_generate_api()` (hiện tại 60s)
- Nếu vẫn không hoạt động, kiểm tra:
  - HF Spaces có đang chạy không
  - Internet connection
  - Server logs để xem lỗi cụ thể




