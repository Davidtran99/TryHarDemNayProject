# Hướng dẫn Switch LLM Provider

> **Mặc định kể từ bản cập nhật này, chatbot sẽ dùng local model Qwen/Qwen2.5-7B-Instruct (8-bit) nếu bạn không cấu hình `LLM_PROVIDER`.**  
> Bạn có thể dùng script bên dưới để chuyển sang API/OpenAI/... bất kỳ lúc nào.

Script để thay đổi LLM provider linh hoạt giữa local model, API mode, và các providers khác.

## Cách sử dụng

### Method 1: Python Script (Chi tiết)

```bash
# Xem cấu hình hiện tại
python3 switch_llm_provider.py show

# Switch sang local model
python3 switch_llm_provider.py local

# Switch sang local với custom model
python3 switch_llm_provider.py local --model Qwen/Qwen2.5-14B-Instruct --device cuda --8bit

# Switch sang API mode
python3 switch_llm_provider.py api

# Switch sang API với custom URL
python3 switch_llm_provider.py api --url https://custom-api.hf.space/api

# Switch sang OpenAI
python3 switch_llm_provider.py openai

# Switch sang Anthropic
python3 switch_llm_provider.py anthropic

# Switch sang Ollama
python3 switch_llm_provider.py ollama

# Tắt LLM (chỉ dùng template)
python3 switch_llm_provider.py none
```

### Method 2: Shell Script (Nhanh)

```bash
# Xem cấu hình hiện tại
./llm_switch.sh

# Switch sang local
./llm_switch.sh local

# Switch sang API
./llm_switch.sh api

# Switch sang OpenAI
./llm_switch.sh openai

# Tắt LLM
./llm_switch.sh none
```

## Các Providers hỗ trợ

### 1. Local Model (`local`)
Sử dụng local Hugging Face model trên máy của bạn.

**Cấu hình:**
```bash
LLM_PROVIDER=local
LOCAL_MODEL_PATH=Qwen/Qwen2.5-7B-Instruct
LOCAL_MODEL_DEVICE=cuda  # hoặc cpu, auto
LOCAL_MODEL_8BIT=true     # hoặc false
LOCAL_MODEL_4BIT=false    # hoặc true
```

**Ví dụ:**
```bash
# 7B model với 8-bit quantization
python3 switch_llm_provider.py local --model Qwen/Qwen2.5-7B-Instruct --device cuda --8bit

# 14B model với 4-bit quantization
python3 switch_llm_provider.py local --model Qwen/Qwen2.5-14B-Instruct --device cuda --4bit
```

### 2. API Mode (`api`)
Gọi API của Hugging Face Spaces.

**Cấu hình:**
```bash
LLM_PROVIDER=api
HF_API_BASE_URL=https://davidtran999-hue-portal-backend.hf.space/api
```

**Ví dụ:**
```bash
# Sử dụng default API URL
python3 switch_llm_provider.py api

# Sử dụng custom API URL
python3 switch_llm_provider.py api --url https://your-custom-api.hf.space/api
```

### 3. OpenAI (`openai`)
Sử dụng OpenAI API.

**Cấu hình:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
```

**Ví dụ:**
```bash
python3 switch_llm_provider.py openai
```

### 4. Anthropic (`anthropic`)
Sử dụng Anthropic Claude API.

**Cấu hình:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key-here
```

**Ví dụ:**
```bash
python3 switch_llm_provider.py anthropic
```

### 5. Ollama (`ollama`)
Sử dụng Ollama local server.

**Cấu hình:**
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

**Ví dụ:**
```bash
python3 switch_llm_provider.py ollama
```

### 6. None (`none`)
Tắt LLM, chỉ sử dụng template-based generation.

**Ví dụ:**
```bash
python3 switch_llm_provider.py none
```

## Lưu ý quan trọng

1. **Restart Server**: Sau khi thay đổi provider, cần restart Django server để áp dụng:
   ```bash
   # Nếu dùng manage.py
   python manage.py runserver
   
   # Nếu dùng gunicorn
   systemctl restart gunicorn
   # hoặc
   pkill -f gunicorn && gunicorn ...
   ```

2. **Local Model Requirements**:
   - Cần GPU với đủ VRAM (7B 8-bit: ~7GB, 14B 4-bit: ~8GB)
   - Cần cài đặt: `transformers`, `accelerate`, `bitsandbytes`
   - Model sẽ được download tự động lần đầu

3. **API Mode**:
   - Cần internet connection
   - API endpoint phải đang hoạt động
   - Có thể có rate limits

4. **Environment Variables**:
   - Script sẽ tự động tạo/update file `.env` trong thư mục `backend/`
   - Nếu không có file `.env`, script sẽ tạo mới

## Troubleshooting

### Local model không load được
- Kiểm tra GPU có đủ VRAM không
- Thử model nhỏ hơn: `Qwen/Qwen2.5-1.5B-Instruct`
- Thử dùng CPU: `--device cpu` (chậm hơn)

### API mode không hoạt động
- Kiểm tra internet connection
- Kiểm tra API URL có đúng không
- Kiểm tra API endpoint có đang chạy không

### Script không tìm thấy .env file
- Script sẽ tự động tạo file `.env` mới
- Hoặc tạo thủ công: `touch backend/.env`

## Examples

### Development: Dùng API mode (nhanh, không cần GPU)
```bash
./llm_switch.sh api
```

### Production: Dùng local model (tốt nhất, không tốn API cost)
```bash
./llm_switch.sh local --model Qwen/Qwen2.5-7B-Instruct --device cuda --8bit
```

### Testing: Tắt LLM (chỉ template)
```bash
./llm_switch.sh none
```

