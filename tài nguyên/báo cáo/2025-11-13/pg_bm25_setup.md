## Kiểm tra môi trường PostgreSQL cho BM25

- **Bước 1 – Kiểm tra phiên bản**
  - Chạy `psql --version` hoặc `SELECT version();` để đảm bảo PostgreSQL ≥ 12 (khuyến nghị ≥ 13).

- **Bước 2 – Kiểm tra quyền bật extension**
  - Đăng nhập `psql` bằng user dự định chạy ứng dụng.
  - Chạy `SHOW rds.extensions;` (nếu dùng RDS) hoặc `SELECT * FROM pg_available_extensions WHERE name IN ('pg_trgm','unaccent');`.
  - Nếu chưa thấy, cần quyền `SUPERUSER` hoặc nhờ DBA bật sẵn.

- **Bước 3 – Bật extension ở database dự án**
  - `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
  - `CREATE EXTENSION IF NOT EXISTS unaccent;`
  - Ghi chú bước này vào migration đầu tiên để tự động hóa.

- **Bước 4 – Kiểm tra cấu hình ngôn ngữ**
  - `SHOW default_text_search_config;` • nên là `simple` để tránh tách dấu tiếng Việt sai.
  - Nếu cần, dùng `ALTER DATABASE <dbname> SET default_text_search_config TO 'simple';`

- **Bước 5 – Xác nhận quyền tạo trigger**
  - User chạy migration phải có quyền `CREATE` trên schema chứa bảng.
  - Thử `CREATE FUNCTION test_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$;` và drop ngay sau đó.

- **Bước 6 – Lưu lại thông tin**
  - Ghi nhận kết quả từng câu lệnh tại `docs/pg_bm25_setup.log` hoặc wiki nội bộ để tham chiếu.
  - Nếu gặp lỗi, lưu lỗi và phương án xử lý (ví dụ nhờ DBA cấp quyền, update engine, …).
