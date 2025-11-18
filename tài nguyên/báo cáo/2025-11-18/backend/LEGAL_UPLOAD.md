# Luồng import tài liệu pháp lý (18/11/2025)

## Tóm tắt

- API `POST /api/legal-documents/upload/` nay chỉ cần chọn file: server sinh mã + metadata tự động (từ nội dung văn bản).
- Mọi upload chạy qua **IngestionJob** (Celery task), tiến độ theo dõi được ở API `/api/legal-ingestion-jobs/` hoặc trang `/legal-upload`.
- Tệp gốc lưu tại `MEDIA_ROOT/legal_uploads/<code>/`; ảnh trích xuất ở `MEDIA_ROOT/legal_images/<code>/`.
- Bộ trích xuất mới:
  - Ưu tiên text gốc; nếu PDF chỉ có ảnh, tự OCR (Tesseract) và lưu text OCR riêng.
  - Chunking “hybrid”: Điều/Mục truyền thống + semantic chunk (cấu hình `LEGAL_CHUNK_STRATEGY=hybrid`).
- CLI sẵn có: `load_legal_document`, `retry_ingestion_job`, `rechunk_legal_document`, script manifest, v.v.
- Frontend `/legal-upload` hiển thị job status (pending/running/completed/failed) và trả link tải file khi xong.

## Bảo mật

- Endpoint yêu cầu một trong hai:
  - Người dùng đã đăng nhập (session Django).
  - Hoặc gửi header `X-Upload-Token` khớp với biến môi trường `LEGAL_UPLOAD_TOKEN`.
- Token cấu hình trong `.env` (ví dụ `LEGAL_UPLOAD_TOKEN=supersecret`).

## Hướng dẫn sử dụng

1. Mở `http://localhost:5173/legal-upload`.
2. Chọn file PDF/DOCX (khuyến nghị < 50MB). UI tự sinh mã (dựa trên tên file).
3. Nếu server yêu cầu token, nhập vào field “Upload token” (hoặc login admin).
4. Nhấn “Import tài liệu” → hệ thống trả về `job_id`.
5. Trang tự poll `/api/legal-ingestion-jobs/<job_id>/` tới khi `status=completed`.
6. Khi xong sẽ hiển thị:
   - Tổng số đoạn/ảnh (`job.stats`),
   - Link tải file gốc,
   - Bất kỳ lỗi nào (nếu `status=failed`).

## Ghi chú kỹ thuật

- **OCR & Chunking**
  - PyMuPDF + python-docx đọc text; nếu `page.get_text()` rỗng → render ảnh và OCR bằng `pytesseract` (ngôn ngữ `vie+eng`, cấu hình `OCR_LANGS`).
  - Text OCR lưu vào `LegalDocument.raw_text_ocr`; từng `LegalSection` có flag `is_ocr`.
  - Semantic chunk (mặc định tắt): bật `LEGAL_CHUNK_STRATEGY=hybrid`, tinh chỉnh `LEGAL_CHUNK_SIZE`, `LEGAL_CHUNK_OVERLAP`.
- **Dedup & Metadata**
  - Hệ thống tính `content_checksum` từ text chuẩn hoá; nếu trùng văn bản khác → reject upload.
  - Tự nhận dạng ngày ban hành, cơ quan, loại văn bản (regex “QUYẾT ĐỊNH…”, “ngày dd/mm/yyyy”, “BỘ …”).
- **Background jobs**
  - Model `IngestionJob` lưu status/progress/stats, file tạm `MEDIA_ROOT/ingestion_jobs/<job_id>/`.
  - Celery cấu hình qua `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (mặc định dùng cùng Redis `REDIS_URL`). Dev có thể chạy synchronous bằng `CELERY_TASK_ALWAYS_EAGER=true`.
  - Admin có dashboard `IngestionJobAdmin` với action “Retry selected ingestion jobs”.
- **CLI**
  - `python manage.py load_legal_document --file ... --code ...`
  - `python manage.py retry_ingestion_job <job_id>`
  - `python manage.py rechunk_legal_document --code <CODE>`
- **Môi trường**
  - `DJANGO_MEDIA_ROOT`, `LEGAL_UPLOAD_TOKEN`, `OCR_LANGS`, `OCR_PDF_ZOOM`, `LEGAL_CHUNK_STRATEGY`.
  - Docker compose ánh xạ Postgres `POSTGRES_EXPOSE_PORT` và Redis `REDIS_EXPOSE_PORT` để tránh xung đột port local (mặc định 5543/6380).


