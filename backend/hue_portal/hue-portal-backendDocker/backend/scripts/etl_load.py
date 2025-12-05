import argparse
import csv
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional

import django
from pydantic import BaseModel, ValidationError, field_validator


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
HUE_PORTAL_DIR = BACKEND_DIR / "hue_portal"
DEFAULT_DATA_DIR = ROOT_DIR / "tài nguyên"
DATA_DIR = Path(os.environ.get("ETL_DATA_DIR", DEFAULT_DATA_DIR))
LOG_DIR = ROOT_DIR / "backend" / "logs" / "data_quality"

# Add backend directory to sys.path so Django can find hue_portal package
# Django needs to import hue_portal.hue_portal.settings, so backend/ must be in path
# IMPORTANT: Only add BACKEND_DIR, not HUE_PORTAL_DIR, because Django needs to find
# the hue_portal package (which is in backend/hue_portal), not the hue_portal directory itself
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Add root for other imports if needed (but not HUE_PORTAL_DIR as it breaks Django imports)
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
django.setup()

from hue_portal.core.models import Fine, Office, Procedure, Advisory  # noqa: E402


LOG_DIR.mkdir(parents=True, exist_ok=True)


class OfficeRecord(BaseModel):
    unit_name: str
    address: Optional[str] = ""
    district: Optional[str] = ""
    working_hours: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    latitude: Optional[float]
    longitude: Optional[float]
    service_scope: Optional[str] = ""
    updated_at: Optional[datetime]

    @field_validator("unit_name")
    @classmethod
    def unit_name_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("unit_name is required")
        return value


class FineRecord(BaseModel):
    violation_code: str
    violation_name: Optional[str] = ""
    article: Optional[str] = ""
    decree: Optional[str] = ""
    min_fine: Optional[float]
    max_fine: Optional[float]
    license_points: Optional[str] = ""
    remedial_measures: Optional[str] = ""
    source_url: Optional[str] = ""
    updated_at: Optional[datetime]

    @field_validator("violation_code")
    @classmethod
    def code_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("violation_code is required")
        return value


class ProcedureRecord(BaseModel):
    title: str
    domain: Optional[str] = ""
    level: Optional[str] = ""
    conditions: Optional[str] = ""
    dossier: Optional[str] = ""
    fee: Optional[str] = ""
    duration: Optional[str] = ""
    authority: Optional[str] = ""
    source_url: Optional[str] = ""
    updated_at: Optional[datetime]

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("title is required")
        return value


class AdvisoryRecord(BaseModel):
    title: str
    summary: str
    source_url: Optional[str] = ""
    published_at: Optional[date]

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("title is required")
        return value

    @field_validator("summary")
    @classmethod
    def summary_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("summary is required")
        return value


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime.date object (for Advisory.published_at)"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.date()
        except ValueError:
            continue
    return None


def log_error(file_handle, dataset: str, row: Dict[str, str], error: str) -> None:
    file_handle.write(
        f"[{datetime.utcnow().isoformat()}Z] dataset={dataset} error={error} row={row}\n"
    )


def should_skip(updated_at: Optional[datetime], since: Optional[datetime]) -> bool:
    if not since or not updated_at:
        return False
    return updated_at < since


def load_offices(since: Optional[datetime], dry_run: bool, log_file) -> int:
    path = DATA_DIR / "danh_ba_diem_tiep_dan.csv"
    if not path.exists():
        log_error(log_file, "offices", {}, f"File không tồn tại: {path}")
        return 0

    processed = 0
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row = {k: (v or "").strip() for k, v in row.items()}
            for key in ["latitude", "longitude"]:
                if row.get(key) == "":
                    row[key] = None
            row["updated_at"] = parse_datetime(row.get("updated_at"))
            try:
                record = OfficeRecord(**row)
            except ValidationError as exc:
                log_error(log_file, "offices", row, str(exc))
                continue

            if should_skip(record.updated_at, since):
                continue

            processed += 1
            if dry_run:
                continue

            Office.objects.update_or_create(
                unit_name=record.unit_name,
                defaults={
                    "address": record.address or "",
                    "district": record.district or "",
                    "working_hours": record.working_hours or "",
                    "phone": record.phone or "",
                    "email": record.email or "",
                    "latitude": record.latitude,
                    "longitude": record.longitude,
                    "service_scope": record.service_scope or "",
                },
            )
    return processed


def load_fines(since: Optional[datetime], dry_run: bool, log_file) -> int:
    path = DATA_DIR / "muc_phat_theo_hanh_vi.csv"
    if not path.exists():
        log_error(log_file, "fines", {}, f"File không tồn tại: {path}")
        return 0

    processed = 0
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row = {k: (v or "").strip() for k, v in row.items()}
            for key in ["min_fine", "max_fine"]:
                if row.get(key) == "":
                    row[key] = None
            row["updated_at"] = parse_datetime(row.get("updated_at"))
            try:
                record = FineRecord(**row)
            except ValidationError as exc:
                log_error(log_file, "fines", row, str(exc))
                continue

            if should_skip(record.updated_at, since):
                continue

            processed += 1
            if dry_run:
                continue

            Fine.objects.update_or_create(
                code=record.violation_code,
                defaults={
                    "name": record.violation_name or "",
                    "article": record.article or "",
                    "decree": record.decree or "",
                    "min_fine": record.min_fine,
                    "max_fine": record.max_fine,
                    "license_points": record.license_points or "",
                    "remedial": record.remedial_measures or "",
                    "source_url": record.source_url or "",
                },
            )
    return processed


def load_procedures(since: Optional[datetime], dry_run: bool, log_file) -> int:
    path = DATA_DIR / "thu_tuc_hanh_chinh.csv"
    if not path.exists():
        log_error(log_file, "procedures", {}, f"File không tồn tại: {path}")
        return 0

    processed = 0
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            # Clean row: ensure keys and values are strings
            clean_row = {}
            for k, v in row.items():
                key = str(k).strip() if k else ""
                value = (v.strip() if isinstance(v, str) else str(v or "")) if v else ""
                clean_row[key] = value
            clean_row["updated_at"] = parse_datetime(clean_row.get("updated_at"))
            try:
                record = ProcedureRecord(**clean_row)
            except ValidationError as exc:
                log_error(log_file, "procedures", clean_row, str(exc))
                continue

            if should_skip(record.updated_at, since):
                continue

            processed += 1
            if dry_run:
                continue

            Procedure.objects.update_or_create(
                title=record.title,
                domain=record.domain or "",
                defaults={
                    "level": record.level or "",
                    "conditions": record.conditions or "",
                    "dossier": record.dossier or "",
                    "fee": record.fee or "",
                    "duration": record.duration or "",
                    "authority": record.authority or "",
                    "source_url": record.source_url or "",
                },
            )
    return processed


def load_advisories(since: Optional[datetime], dry_run: bool, log_file) -> int:
    path = DATA_DIR / "canh_bao_lua_dao.csv"
    if not path.exists():
        log_error(log_file, "advisories", {}, f"File không tồn tại: {path}")
        return 0

    processed = 0
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            # Clean row: ensure keys and values are strings
            clean_row = {}
            for k, v in row.items():
                key = str(k).strip() if k else ""
                value = (v.strip() if isinstance(v, str) else str(v or "")) if v else ""
                clean_row[key] = value
            clean_row["published_at"] = parse_date(clean_row.get("published_at"))
            try:
                record = AdvisoryRecord(**clean_row)
            except ValidationError as exc:
                log_error(log_file, "advisories", clean_row, str(exc))
                continue

            # Advisory không có updated_at, chỉ check published_at nếu since được set
            if since and record.published_at:
                if record.published_at < since.date():
                    continue

            processed += 1
            if dry_run:
                continue

            Advisory.objects.update_or_create(
                title=record.title,
                defaults={
                    "summary": record.summary or "",
                    "source_url": record.source_url or "",
                    "published_at": record.published_at,
                },
            )
    return processed


def parse_args():
    parser = argparse.ArgumentParser(description="ETL dữ liệu chatbot")
    parser.add_argument("--since", help="Chỉ xử lý bản ghi có updated_at >= giá trị này (ISO date)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ kiểm tra dữ liệu, không ghi vào DB")
    parser.add_argument("--datasets", nargs="*", default=["offices", "fines"], choices=["offices", "fines", "procedures", "advisories"], help="Chọn dataset cần nạp")
    return parser.parse_args()


def main():
    args = parse_args()
    since = parse_datetime(args.since) if args.since else None
    log_path = LOG_DIR / f"etl_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.log"

    with log_path.open("a", encoding="utf-8") as log_file:
        if "offices" in args.datasets:
            total = load_offices(since, args.dry_run, log_file)
            print(f"Offices processed: {total}")
        if "fines" in args.datasets:
            total = load_fines(since, args.dry_run, log_file)
            print(f"Fines processed: {total}")
        if "procedures" in args.datasets:
            total = load_procedures(since, args.dry_run, log_file)
            print(f"Procedures processed: {total}")
        if "advisories" in args.datasets:
            total = load_advisories(since, args.dry_run, log_file)
            print(f"Advisories processed: {total}")

    print(f"Log ghi tại {log_path}")


if __name__ == "__main__":
    main()
