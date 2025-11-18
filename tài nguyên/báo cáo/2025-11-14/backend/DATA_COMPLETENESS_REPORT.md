# Data Completeness Review — 2025-11-14

## 1. Scope
- `core_procedure`: 15 records from `thu_tuc_hanh_chinh.csv`
- `core_advisory`: 15 records from `canh_bao_lua_dao.csv`
- Focus fields: `source_url`, `authority`, `conditions`, `dossier`, `fee`, `duration`, `summary`, `published_at`

## 2. Findings
| Model | Total | Missing Fields |
|-------|-------|----------------|
| Procedure | 15 | All tracked fields populated |
| Advisory | 15 | **Initial:** `published_at` missing for 14/14 records due to CSV parsing | 

Root cause for advisories:
1. CSV summaries were not quoted, so commas inside text shifted the `published_at` column during ETL parsing.
2. `AdvisoryRecord.published_at` expected `datetime`, rejecting the `datetime.date` objects returned by `parse_date`.
3. One legacy record (`Lừa đảo đầu tư "lợi nhuận cao`) remained from the first faulty import.

## 3. Fixes Implemented
1. Rebuilt `tài nguyên/canh_bao_lua_dao.csv` with proper CSV quoting/escaping so embedded commas no longer break columns.
2. Updated `backend/scripts/etl_load.py` to accept `date` values for `AdvisoryRecord.published_at`.
3. Re-ran `scripts/etl_load.py --datasets advisories` (log: `etl_20251114080239.log`).
4. Removed the obsolete truncated advisory record so only the corrected entry remains.

## 4. Verification
```
python manage.py shell <<'PY'
from hue_portal.core.models import Procedure, Advisory
# ... summary script ...
PY
```
Output:
```
[
  {"model": "Procedure", "total": 15, "missing": {"source_url": 0, "authority": 0, "conditions": 0, "dossier": 0, "fee": 0, "duration": 0}},
  {"model": "Advisory", "total": 15, "missing": {"source_url": 0, "summary": 0, "published_at": 0}}
]
```
Random spot-check:
```
Advisory.objects.values_list("title", "published_at")[:3]
=> [
  ("Chiếm đoạt tài khoản mạng xã hội qua link xác minh/xanh tích", datetime.date(2025, 11, 14)),
  ("Lừa mua bán tài khoản ngân hàng/thuê KYC", datetime.date(2025, 11, 14)),
  ("Mạo danh toà án/viện kiểm sát/hải quan qua email công vụ giả", datetime.date(2025, 11, 14))
]
```

## 5. Next Actions
- Keep CSV summaries quoted going forward (see `SHELL_COMMANDS` rule for heredoc usage when regenerating files).
- If new advisory data uses other dates, re-run `scripts/etl_load.py --datasets advisories` (script now handles `date`).
