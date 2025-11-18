import os
import sys
import time
import json
from pathlib import Path
import statistics

# Ensure project root on path
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
HUE_PORTAL_DIR = BACKEND_DIR / "hue_portal"

for path in (HUE_PORTAL_DIR, BACKEND_DIR, ROOT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")

import django

django.setup()

from django.db import connection
from hue_portal.core.models import Procedure, Fine, Office, Advisory
from hue_portal.core.search_ml import search_with_ml


QUERIES = {
    "procedure": [
        "đăng ký cư trú",
        "thủ tục pccc",
        "giấy tờ antt",
    ],
    "fine": [
        "mức phạt nồng độ cồn",
        "vượt đèn đỏ",
        "không đội mũ bảo hiểm",
    ],
    "office": [
        "công an phường",
        "điểm tiếp dân",
    ],
    "advisory": [
        "cảnh báo lừa đảo",
        "giả mạo công an",
    ],
}


def run_benchmark(iterations: int = 3):
    results = {
        "database_vendor": connection.vendor,
        "timestamp": time.time(),
        "iterations": iterations,
        "entries": [],
    }

    datasets = {
        "procedure": (Procedure.objects.all(), ["title", "domain", "conditions", "dossier"]),
        "fine": (Fine.objects.all(), ["name", "code", "article", "decree", "remedial"]),
        "office": (Office.objects.all(), ["unit_name", "address", "district", "service_scope"]),
        "advisory": (Advisory.objects.all(), ["title", "summary"]),
    }

    for dataset, queries in QUERIES.items():
        qs, fields = datasets[dataset]
        for query in queries:
            durations = []
            counts = []
            for _ in range(iterations):
                start = time.perf_counter()
                items = list(search_with_ml(qs, query, fields, top_k=20))
                durations.append(time.perf_counter() - start)
                counts.append(len(items))

            results["entries"].append(
                {
                    "dataset": dataset,
                    "query": query,
                    "avg_duration_ms": statistics.mean(durations) * 1000,
                    "p95_duration_ms": statistics.quantiles(durations, n=20)[18] * 1000 if len(durations) >= 20 else max(durations) * 1000,
                    "min_duration_ms": min(durations) * 1000,
                    "max_duration_ms": max(durations) * 1000,
                    "avg_results": statistics.mean(counts),
                }
            )

    return results


def main():
    iterations = int(os.environ.get("BENCH_ITERATIONS", "3"))
    benchmark = run_benchmark(iterations=iterations)

    output_dir = ROOT_DIR / "logs" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"search_benchmark_{int(benchmark['timestamp'])}.json"
    output_file.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2))

    print(f"Benchmark completed. Results saved to {output_file}")


if __name__ == "__main__":
    main()
