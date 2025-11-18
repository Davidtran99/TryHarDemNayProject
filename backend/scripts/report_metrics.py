import argparse
import os
import sys
from datetime import datetime, date
from pathlib import Path

import django


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"

HUE_PORTAL_DIR = BACKEND_DIR / "hue_portal"

for path in (HUE_PORTAL_DIR, BACKEND_DIR, ROOT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
django.setup()

from django.db.models import Avg, Count, Q
from hue_portal.core.models import AuditLog, MLMetrics


def parse_args():
    parser = argparse.ArgumentParser(description="Tổng hợp metrics ML hàng ngày")
    parser.add_argument("--date", help="Ngày cần tổng hợp (YYYY-MM-DD), mặc định hôm nay")
    return parser.parse_args()


def target_date(arg: str) -> date:
    if not arg:
        return date.today()
    return datetime.strptime(arg, "%Y-%m-%d").date()


def compute_metrics(day: date) -> dict:
    logs = AuditLog.objects.filter(created_at__date=day)
    total = logs.count()
    if total == 0:
        return {
            "date": day.isoformat(),
            "total_requests": 0,
            "intent_accuracy": None,
            "average_latency_ms": None,
            "error_rate": None,
            "intent_breakdown": {},
        }

    latency_avg = logs.exclude(latency_ms__isnull=True).aggregate(avg=Avg("latency_ms"))["avg"]
    errors = logs.filter(status__gte=400).count()
    intents_with_conf = logs.filter(~Q(intent=""), status__lt=400)
    intent_accuracy = None
    if intents_with_conf.exists():
        confident = intents_with_conf.filter(Q(confidence__gte=0.6) | Q(confidence__isnull=True)).count()
        intent_accuracy = confident / intents_with_conf.count()

    breakdown = (
        logs.exclude(intent="")
        .values("intent")
        .annotate(count=Count("id"))
        .order_by("intent")
    )
    breakdown_dict = {row["intent"]: row["count"] for row in breakdown}

    return {
        "date": day.isoformat(),
        "total_requests": total,
        "intent_accuracy": intent_accuracy,
        "average_latency_ms": latency_avg,
        "error_rate": errors / total,
        "intent_breakdown": breakdown_dict,
    }


def save_metrics(day: date, metrics: dict) -> MLMetrics:
    obj, _ = MLMetrics.objects.update_or_create(
        date=day,
        defaults={
            "total_requests": metrics["total_requests"],
            "intent_accuracy": metrics["intent_accuracy"],
            "average_latency_ms": metrics["average_latency_ms"],
            "error_rate": metrics["error_rate"],
            "intent_breakdown": metrics["intent_breakdown"],
        },
    )
    return obj


def main():
    args = parse_args()
    day = target_date(args.date)
    metrics = compute_metrics(day)
    save_metrics(day, metrics)

    print("=== ML Metrics ===")
    print(f"Ngày: {metrics['date']}")
    print(f"Tổng request: {metrics['total_requests']}")
    print(f"Độ chính xác (ước tính): {metrics['intent_accuracy']}")
    print(f"Latency trung bình (ms): {metrics['average_latency_ms']}")
    print(f"Tỉ lệ lỗi: {metrics['error_rate']}")
    print(f"Phân bổ intent: {metrics['intent_breakdown']}")


if __name__ == "__main__":
    main()
