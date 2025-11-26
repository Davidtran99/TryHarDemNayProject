# API Mode - Trạng thái sẵn sàng

## ✅ Project đã sẵn sàng để test với API mode!

### Đã hoàn thành:

1. **Code Integration** ✅
   - `llm_integration.py` đã có method `_generate_api()`
   - API mode được support đầy đủ
   - Error handling và timeout được xử lý

2. **Configuration** ✅
   - File `.env` đã được tạo với `LLM_PROVIDER=api`
   - API URL đã được set: `https://davidtran999-hue-portal-backend.hf.space/api`

3. **Scripts** ✅
   - `switch_llm_provider.py` - để switch giữa các providers
   - `test_api_mode.py` - để test API connection

### Cách sử dụng:

#### 1. Kiểm tra cấu hình hiện tại:
```bash
python3 switch_llm_provider.py show
```

#### 2. Đảm bảo đang dùng API mode:
```bash
python3 switch_llm_provider.py api
```

#### 3. Test API connection:
```bash
python3 test_api_mode.py
```

#### 4. Restart Django server:
```bash
# Nếu dùng manage.py
python manage.py runserver

# Nếu dùng gunicorn
systemctl restart gunicorn
# hoặc
pkill -f gunicorn && gunicorn your_app.wsgi:application
```

### Lưu ý:

1. **API Endpoint phải đang chạy**
   - Hugging Face Space phải được deploy và running
   - URL: `https://davidtran999-hue-portal-backend.hf.space/api`
   - Endpoint: `/api/chatbot/chat/`

2. **Model Loading Time**
   - Lần đầu gọi API có thể mất thời gian (model đang load)
   - Có thể nhận 503 (Service Unavailable) - đây là bình thường
   - Đợi vài phút rồi thử lại

3. **Request Format**
   - API expect: `{"message": "text", "reset_session": false}`
   - Không cần `session_id` (sẽ được generate tự động)

### Troubleshooting:

#### API timeout:
- Kiểm tra internet connection
- Kiểm tra Hugging Face Space có đang running không
- Kiểm tra URL có đúng không

#### API trả về 503:
- Model đang loading, đợi vài phút rồi thử lại
- Đây là bình thường cho lần đầu tiên

#### API trả về 400:
- Kiểm tra request format
- Đảm bảo `message` field có giá trị

### Test thủ công:

```python
import requests

url = "https://davidtran999-hue-portal-backend.hf.space/api/chatbot/chat/"
payload = {
    "message": "Xin chào",
    "reset_session": False
}

response = requests.post(url, json=payload, timeout=60)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### Kết luận:

**Project đã sẵn sàng về mặt code!** 

Chỉ cần:
1. Đảm bảo Hugging Face Space đang chạy
2. Restart Django server
3. Test với một câu hỏi đơn giản

Code sẽ tự động:
- Gọi API endpoint đúng
- Xử lý errors
- Return response message

