# Hướng dẫn khởi động Backend và Frontend

## Trạng thái hiện tại

✅ **Backend đang chạy:** http://localhost:8000
✅ **Frontend đang chạy:** http://localhost:3000

## Cách khởi động thủ công

### 1. Backend (Django)

```bash
cd /Users/davidtran/Downloads/TryHarDemNayProject/backend
source venv/bin/activate
cd hue_portal
python3 manage.py runserver 0.0.0.0:8000
```

### 2. Frontend (React + Vite)

```bash
cd /Users/davidtran/Downloads/TryHarDemNayProject/frontend
npm run dev
```

### 3. Hoặc dùng script tự động

```bash
cd /Users/davidtran/Downloads/TryHarDemNayProject
./start_dev.sh
```

## Kiểm tra servers

### Backend
```bash
curl http://localhost:8000/api/chatbot/chat/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"test","reset_session":false}'
```

### Frontend
```bash
curl http://localhost:3000
```

## Lưu ý

- Backend cần chạy trước Frontend
- Nếu port bị chiếm, dùng:
  ```bash
  lsof -ti:8000 | xargs kill -9  # Kill port 8000
  lsof -ti:3000 | xargs kill -9  # Kill port 3000
  ```
- Xem logs:
  - Backend: Terminal đang chạy `manage.py runserver`
  - Frontend: Terminal đang chạy `npm run dev`

## Test API Mode

1. Mở http://localhost:3000/chat
2. Gửi câu hỏi: "Mức phạt vượt đèn đỏ là bao nhiêu?"
3. Xem backend logs để thấy:
   - `[LLM] 🔄 Recreated LLM generator with provider: api`
   - `[RAG] Using LLM provider: api`
   - `[LLM] 🔗 Calling API: ...`
   - `[LLM] 📥 Response status: 200`




