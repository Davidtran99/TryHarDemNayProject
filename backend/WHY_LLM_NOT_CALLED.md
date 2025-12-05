# Tại sao LLM không được gọi?

## Vấn đề

Chatbot đã trả lời được, nhưng response là **template-based** (không phải từ LLM API).

## Nguyên nhân

### 1. Không có documents được tìm thấy
- Response cho thấy: `"count": 0`, `"results": []`
- Database chưa có tables hoặc chưa có dữ liệu

### 2. LLM chỉ được gọi khi CÓ documents

Trong `rag.py`:
```python
# Try LLM generation first if enabled and documents are available
if use_llm and documents:  # ← Cần có documents
    llm = get_llm_generator()
    if llm:
        llm_answer = llm.generate_answer(...)
```

**Logic:**
- Nếu **KHÔNG có documents** → Trả về template message ngay lập tức
- Nếu **CÓ documents** → Gọi LLM để generate answer

## Giải pháp

### 1. Chạy migrations để tạo tables
```bash
cd backend && source venv/bin/activate && cd hue_portal
python3 manage.py makemigrations
python3 manage.py migrate
```

### 2. Import/Ingest dữ liệu vào database
- Cần có dữ liệu về fines, procedures, legal sections, etc.
- Sau khi có dữ liệu, search sẽ tìm thấy documents
- Khi có documents, LLM sẽ được gọi

### 3. Test với câu hỏi có documents
- Nếu database đã có dữ liệu, test với câu hỏi chắc chắn có trong DB
- Ví dụ: "Mức phạt vượt đèn đỏ" (nếu có dữ liệu về fines)

## Flow hoạt động

1. **User gửi câu hỏi** → `chatbot/views.py`
2. **Intent classification** → Xác định loại câu hỏi
3. **RAG pipeline** → Tìm documents trong database
   - Nếu **KHÔNG có documents** → Trả về template message
   - Nếu **CÓ documents** → Gọi LLM để generate answer
4. **LLM generation** (chỉ khi có documents):
   - `get_llm_generator()` → Lấy LLM instance
   - `llm.generate_answer(query, documents=documents)` → Generate
   - Với API mode: Gọi HF Spaces API với prompt (có documents)
5. **Response** → Trả về cho user

## Để test API mode

1. **Đảm bảo database có dữ liệu**
2. **Gửi câu hỏi có documents** (ví dụ: "Mức phạt vượt đèn đỏ")
3. **Xem server logs** để thấy:
   - `[RAG] Using LLM provider: api`
   - `[LLM] 🔗 Calling API: ...`
   - `[LLM] 📥 Response status: 200`

## Lưu ý

- **API mode đã được cấu hình đúng** (`LLM_PROVIDER=api`)
- **Code đã sửa để gửi prompt (có documents)** thay vì chỉ query
- **Vấn đề hiện tại:** Database chưa có dữ liệu → Không có documents → LLM không được gọi




