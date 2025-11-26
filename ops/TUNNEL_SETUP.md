# PostgreSQL Tunnel & HF Sync

Tài liệu này tổng hợp các bước thiết lập tunnel tới PostgreSQL, đồng bộ dữ
liệu và giám sát chatbot khi chạy trên Hugging Face Space.

## 1. Chuẩn bị

1. Cài `ngrok`, `pg_isready` (thường đi kèm PostgreSQL client) và login
   `huggingface-cli login`.
2. Sao chép file `ops/env.tunnel.example` thành `ops/.env.tunnel` rồi cập nhật
   các thông tin local (POSTGRES_HOST/PORT/USER/PASSWORD/DB).

## 2. Tạo tunnel + cập nhật HF Space

- Chạy `python hue-portal-backend/start_ngrok_and_set_db.py`
  - Script sẽ start hoặc tái sử dụng ngrok TCP tunnel, lưu metadata vào
    `ops/.env.tunnel` và (nếu có token) đẩy `DATABASE_URL` lên HF Space.
- Nếu muốn chỉ cập nhật secrets (không restart tunnel), dùng:
  `python hue-portal-backend/set_database_secrets.py --space-id <space>`.

## 3. Giữ tunnel ổn định

- `ops/pg_tunnel_watchdog.py --interval 300`:
  - Mỗi 5 phút chạy `pg_isready`, nếu lỗi sẽ tự động gọi lại
    `start_ngrok_and_set_db.py`.
  - Log được lưu tại `ops/logs/tunnel_watchdog.log`.
- `ops/monitor_tunnel.sh`: script thủ công để xem trạng thái hiện tại
  (process ngrok, pg_isready, thông tin host/port).

## 4. Đồng bộ dữ liệu + embeddings

- Dùng `./ops/sync_data_to_hf.sh` để chạy tuần tự:
  1. `backend/scripts/etl_load.py`
  2. `backend/scripts/generate_embeddings.py`
  3. `backend/scripts/build_faiss_index.py`
- Có thể bỏ qua từng bước bằng flag `--skip-etl`, `--skip-embeddings`,
  `--skip-faiss`.
- Sau khi chạy xong, commit & push lại thư mục
  `backend/hue_portal/artifacts/` để HF Space dùng được dữ liệu mới.

## 5. Kiểm thử

- Local: `./ops/test_postgres_tunnel.sh`
  - Set `DATABASE_URL` từ tunnel rồi chạy `manage.py check`,
    `pytest core/tests/test_legal_ingestion.py` (nếu có) và `pg_isready`.
- HF Space: `./ops/test_hf_space_db.sh`
  - Gọi `/api/chatbot/health/`, `/api/chatbot/model-status/`,
    `/api/chatbot/chat/` với câu hỏi dữ liệu (`"Mức phạt vượt đèn đỏ"`).
  - Xem log HF Space để chắc chắn `[RAG] Using LLM provider: api` +
    truy vấn SQL thành công.

## 6. Giám sát định kỳ

- Cron gợi ý (mỗi 5 phút):

  ```cron
  */5 * * * * /usr/local/bin/bash /path/to/project/ops/monitor_health.sh
  */5 * * * * /usr/local/bin/python3 /path/to/project/ops/pg_tunnel_watchdog.py --once
  ```

## 7. Troubleshooting nhanh

| Tình huống | Gợi ý xử lý |
|------------|-------------|
| `pg_isready` fail | Chạy `ops/pg_tunnel_watchdog.py --once`, kiểm tra log ngrok. |
| HF Space vẫn dùng SQLite | Đảm bảo đã chạy `set_database_secrets.py` sau khi thay tunnel. |
| Chatbot trả lời “Xin lỗi…” | Kiểm tra `backend/hue_portal/core/rag.py` log `[RAG] Using LLM provider`. Nếu không xuất hiện => kiểm tra LLM provider / HF API. |
| Embeddings cũ | Chạy `ops/sync_data_to_hf.sh`, commit lại artifacts. |

# Hướng dẫn vận hành tunnel PostgreSQL + HF Space

## 1. Chuẩn bị môi trường

- Điền thông tin chung vào `.env` (xem `env.example`)
- Không lưu mật khẩu tunnel trong git – script sẽ ghi vào `ops/.env.tunnel`
- Đăng nhập Hugging Face: `huggingface-cli login`
- Cài ngrok và pg_isready (PostgreSQL client)

## 2. Khởi tạo tunnel & cập nhật HF Space

```bash
python hue-portal-backend/start_ngrok_and_set_db.py
# Script sẽ:
#   - start/reuse ngrok tcp <PG_TUNNEL_LOCAL_PORT>
#   - lưu host/port vào ops/.env.tunnel
#   - đẩy DATABASE_URL lên Space (nếu tìm thấy HF token)
```

Muốn set đầy đủ POSTGRES_* trên Space sau khi có tunnel:

```bash
python hue-portal-backend/set_database_secrets.py
```

## 3. Watchdog & giám sát

- `python ops/pg_tunnel_watchdog.py --interval 60` (hoặc thêm vào cron/systemd)
- `bash ops/monitor_tunnel.sh` để xem nhanh trạng thái ngrok + pg_isready
- `bash ops/monitor_health.sh` (xem thêm script trong thư mục ops) để ping API ở HF Space

## 4. Đồng bộ dữ liệu & chỉ số tìm kiếm

```bash
bash ops/sync_data_to_hf.sh
python backend/scripts/generate_embeddings.py
python backend/scripts/build_faiss_index.py
```

Commit `backend/hue_portal/artifacts/**` sau khi build lại embeddings/FAISS.

## 5. Triển khai / kiểm thử

1. Deploy code + artifacts lên GitHub => HF Space auto build
2. Sau build, chạy:
   - `bash ops/test_postgres_tunnel.sh` (local, với DATABASE_URL trỏ tunnel)
   - `bash ops/test_hf_space_db.sh` (remote, dùng curl gọi Space)
3. Theo dõi `ops/logs/tunnel_watchdog.log` và Hugging Face Space Logs khi có sự cố.


