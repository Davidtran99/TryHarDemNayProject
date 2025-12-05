# Vấn đề: HF Spaces không nhận được request từ project local

## Phân tích

Từ logs HF Spaces:
- HF Spaces đang load **local model** (Qwen/Qwen2.5-7B-Instruct)
- HF Spaces **KHÔNG** nhận được request từ project local
- Khi project local gọi API, response vẫn là **template-based**

## Nguyên nhân có thể

1. **LLM không được gọi khi có documents:**
   - RAG pipeline có `use_llm=True` nhưng LLM generation có thể fail
   - Fallback về template khi LLM fail

2. **LLM generation fail:**
   - API timeout
   - API trả về None
   - Error trong quá trình generate

3. **Server local không load đúng env:**
   - Server khởi động trước khi `.env` được update
   - Cần restart server

## Giải pháp

### 1. Đảm bảo server load đúng env
```bash
# Stop server
pkill -f "manage.py runserver"

# Start lại với env mới
cd backend && source venv/bin/activate && cd hue_portal
python3 manage.py runserver 0.0.0.0:8000
```

### 2. Kiểm tra logs khi test
Khi gửi request với documents, xem logs có:
- `[RAG] Using LLM provider: api`
- `[LLM] 🔗 Calling API: ...`
- `[LLM] 📥 Response status: 200`

Nếu không thấy logs này, có nghĩa là:
- LLM không được gọi
- Hoặc LLM generation fail trước khi gọi API

### 3. Test trực tiếp API mode
```bash
cd backend && source venv/bin/activate
python3 -c "
import os
os.environ['LLM_PROVIDER'] = 'api'
os.environ['HF_API_BASE_URL'] = 'https://davidtran999-hue-portal-backend.hf.space/api'
import sys
sys.path.insert(0, 'hue_portal')
from chatbot.llm_integration import LLMGenerator, LLM_PROVIDER_API
llm = LLMGenerator(provider=LLM_PROVIDER_API)
result = llm._generate_api('Test prompt with documents')
print(f'Result: {result}')
"
```

## Debug steps

1. **Kiểm tra env variables:**
```bash
cd backend && cat .env | grep LLM
```

2. **Restart server:**
```bash
pkill -f "manage.py runserver"
cd backend && source venv/bin/activate && cd hue_portal
python3 manage.py runserver 0.0.0.0:8000
```

3. **Test với câu hỏi có documents:**
```bash
curl -X POST http://localhost:8000/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Mức phạt vượt đèn đỏ là bao nhiêu?", "reset_session": false}'
```

4. **Xem server logs:**
- Tìm `[RAG]` logs
- Tìm `[LLM]` logs
- Tìm error messages

## Lưu ý

- HF Spaces logs cho thấy nó đang dùng **local model**, không phải API mode
- Điều này có nghĩa là HF Spaces đang chạy độc lập, không nhận request từ project local
- Project local cần gọi HF Spaces API để nhận response từ model trên HF Spaces




