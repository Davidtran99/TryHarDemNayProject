## Lịch Cron Gợi Ý

File này mô tả ví dụ cron chạy ETL và seed synonyms hằng tuần.

### Chạy ETL mỗi ngày lúc 02:00
```
0 2 * * * /usr/bin/env bash -lc "cd /path/to/project && source venv/bin/activate && python backend/scripts/etl_load.py"
```

### Chạy ETL incremental dựa trên `updated_at` mỗi Chủ Nhật
```
30 3 * * 0 /usr/bin/env bash -lc "cd /path/to/project && source venv/bin/activate && python backend/scripts/etl_load.py --since $(date -d '7 days ago' +%Y-%m-%d)"
```

### Seed synonyms từ CSV vào thứ Hai hàng tuần
```
15 4 * * 1 /usr/bin/env bash -lc "cd /path/to/project && source venv/bin/activate && python backend/scripts/seed_synonyms.py --source tài\ nguyên/synonyms.csv"
```

> Thay `/path/to/project` và đường dẫn `venv` phù hợp môi trường triển khai.
