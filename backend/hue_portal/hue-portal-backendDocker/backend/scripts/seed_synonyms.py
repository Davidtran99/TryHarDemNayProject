"""
Seed synonyms for search query expansion.
"""
import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

import django


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
DATA_DIR = ROOT_DIR / "tài nguyên"
LOG_DIR = BACKEND_DIR / "logs" / "data_quality"

HUE_PORTAL_DIR = BACKEND_DIR / "hue_portal"

for path in (HUE_PORTAL_DIR, BACKEND_DIR, ROOT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
django.setup()

from hue_portal.core.models import Synonym

DEFAULT_SEEDS: List[Tuple[str, str]] = [
    ("đèn đỏ", "vượt đèn đỏ"),
    ("vượt đèn", "vượt đèn đỏ"),
    ("nồng độ cồn", "rượu bia"),
    ("nồng độ cồn", "say xỉn"),
    ("nồng độ cồn", "uống rượu"),
    ("mũ bảo hiểm", "nón bảo hiểm"),
    ("mũ bảo hiểm", "mũ"),
    ("giấy phép lái xe", "bằng lái"),
    ("giấy phép lái xe", "GPLX"),
    ("giấy phép lái xe", "bằng"),
    ("đăng ký xe", "đăng ký"),
    ("đăng ký xe", "giấy đăng ký"),
    ("dừng đỗ", "đỗ xe"),
    ("dừng đỗ", "dừng xe"),
    ("dây an toàn", "thắt dây an toàn"),
    ("tốc độ", "vượt tốc độ"),
    ("tốc độ", "quá tốc độ"),
    ("sai làn", "sai đường"),
    ("sai làn", "đi sai làn"),
    ("điện thoại", "sử dụng điện thoại"),
    ("điện thoại", "gọi điện"),
    ("cư trú", "thủ tục cư trú"),
    ("cư trú", "đăng ký cư trú"),
    ("cư trú", "tạm trú"),
    ("cư trú", "thường trú"),
    ("ANTT", "an ninh trật tự"),
    ("ANTT", "an ninh"),
    ("PCCC", "phòng cháy chữa cháy"),
    ("PCCC", "cháy nổ"),
    ("thủ tục", "hành chính"),
    ("thủ tục", "TTHC"),
    ("công an", "CA"),
    ("công an", "cảnh sát"),
    ("tiếp dân", "tiếp công dân"),
    ("tiếp dân", "một cửa"),
    ("đơn vị", "cơ quan"),
    ("đơn vị", "phòng ban"),
]


def load_from_csv(path: Path) -> List[Tuple[str, str]]:
    if not path.exists():
        return []
    pairs: List[Tuple[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            keyword = (row.get("keyword") or "").strip()
            alias = (row.get("alias") or "").strip()
            if keyword and alias:
                pairs.append((keyword, alias))
    return pairs


def seed_synonyms(pairs: Iterable[Tuple[str, str]], log_path: Path) -> None:
    created = 0
    updated = 0
    skipped = 0
    
    with log_path.open("a", encoding="utf-8") as log_file:
        for keyword, alias in pairs:
        try:
            synonym, was_created = Synonym.objects.get_or_create(
                keyword=keyword,
                defaults={"alias": alias}
            )
            if was_created:
                created += 1
                    log_file.write(f"{datetime.utcnow().isoformat()}Z CREATED {keyword} -> {alias}\n")
            else:
                if synonym.alias != alias:
                    synonym.alias = alias
                        synonym.save(update_fields=["alias"])
                        updated += 1
                        log_file.write(f"{datetime.utcnow().isoformat()}Z UPDATED {keyword} -> {alias}\n")
                else:
                    skipped += 1
            except Exception as exc:
                log_file.write(f"{datetime.utcnow().isoformat()}Z ERROR {keyword} -> {alias} :: {exc}\n")

    total = Synonym.objects.count()
    print(f"✅ Seeded {created} mới, cập nhật {updated}, bỏ qua {skipped}. Tổng: {total}")
    print(f"Log chi tiết: {log_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Seed synonyms cho chatbot")
    parser.add_argument("--source", type=Path, default=DATA_DIR / "synonyms.csv", help="Đường dẫn CSV synonyms")
    parser.add_argument("--include-default", action="store_true", help="Bao gồm seed mặc định trong script")
    return parser.parse_args()


def main():
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"synonyms_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.log"

    pairs: List[Tuple[str, str]] = []
    csv_pairs = load_from_csv(args.source)
    if csv_pairs:
        pairs.extend(csv_pairs)
    if args.include_default or not pairs:
        pairs.extend(DEFAULT_SEEDS)

    seed_synonyms(pairs, log_path)


if __name__ == "__main__":
    main()

