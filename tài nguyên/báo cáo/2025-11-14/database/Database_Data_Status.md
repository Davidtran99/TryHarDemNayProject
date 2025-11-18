# Tình trạng Database và Data

## ✅ Database đã được setup

- **PostgreSQL 15.14** đang chạy trong Docker
- **Port:** 5433 (external) → 5432 (internal)
- **Database:** hue_portal
- **Users:** hue, admin
- **Migrations:** 6 files đã chạy thành công

## ✅ Tables đã tạo

1. `core_fine` - Mức phạt
2. `core_office` - Địa chỉ điểm tiếp dân
3. `core_procedure` - Thủ tục
4. `core_advisory` - Cảnh báo
5. `core_synonym` - Từ đồng nghĩa
6. `core_auditlog` - Log requests
7. `core_mlmetrics` - ML metrics

## 📊 Tình trạng Data

### ✅ Đã có data:

| Table | Records | Status |
|-------|---------|--------|
| `core_fine` | 20 | ✅ |
| `core_office` | 12 | ✅ |
| `core_synonym` | 18 | ✅ |
| `core_auditlog` | 198 | ✅ |

### ❌ Chưa có data:

| Table | Records | Status |
|-------|---------|--------|
| `core_procedure` | 0 | ❌ Cần load |
| `core_advisory` | 0 | ❌ Cần load |
| `core_mlmetrics` | 0 | ⚠️ Bình thường (sẽ có sau khi có requests) |

## 📁 CSV Files có sẵn

1. **`tài nguyên/danh_ba_diem_tiep_dan.csv`**
   - Dùng cho: `core_office`
   - Status: ✅ Đã load (12 records)

2. **`tài nguyên/muc_phat_theo_hanh_vi.csv`**
   - Dùng cho: `core_fine`
   - Status: ✅ Đã load (20 records)

3. **CSV cho `core_procedure`**
   - Status: ❌ Chưa có file

4. **CSV cho `core_advisory`**
   - Status: ❌ Chưa có file

## 🔧 ETL Script

**File:** `backend/scripts/etl_load.py`

**Chức năng:**
- Load data từ CSV vào `core_fine` và `core_office`
- Validation với Pydantic
- Incremental loading với `--since`
- Dry-run mode với `--dry-run`

**Cách chạy:**
```bash
cd backend/hue_portal
python ../../scripts/etl_load.py
```

## 📝 Cần làm gì tiếp theo?

### 1. Load thêm data cho `core_procedure`

**Option A: Tạo CSV file**
- Tạo file `tài nguyên/thu_tuc.csv` với format:
  ```csv
  title,domain,level,conditions,dossier,processing_time,fee,location,updated_at
  ```

**Option B: Load từ API/Web scraping**
- Scrape từ website Công an Thừa Thiên Huế
- Parse và import vào database

### 2. Load thêm data cho `core_advisory`

**Option A: Tạo CSV file**
- Tạo file `tài nguyên/canh_bao.csv` với format:
  ```csv
  title,summary,content,published_at
  ```

**Option B: Load từ nguồn có sẵn**
- Sử dụng data từ `tài nguyên/báo cáo/2025-11-11/THU_VIEN_CANH_BAO.md`

### 3. Kiểm tra data quality

```bash
# Xem data hiện tại
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT * FROM core_fine LIMIT 5;"
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT * FROM core_office LIMIT 5;"
```

## 🎯 Kết luận

**Database:**
- ✅ Đã setup hoàn chỉnh
- ✅ Tables đã tạo
- ✅ Migrations đã chạy
- ✅ Extensions đã enable (pg_trgm, unaccent)

**Data:**
- ✅ 50% đã load (fine, office, synonym, auditlog)
- ❌ 50% chưa có (procedure, advisory)

**Cần:**
- 📝 Tạo/load data cho `core_procedure`
- 📝 Tạo/load data cho `core_advisory`

---

**Tóm lại: Database đã setup xong, nhưng cần thêm data cho procedure và advisory! 📊**

