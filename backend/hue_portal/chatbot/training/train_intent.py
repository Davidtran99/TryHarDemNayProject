import argparse
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


DEFAULT_DATASET = Path(__file__).resolve().parent / "intent_dataset.json"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
LOG_DIR = ROOT_DIR / "logs" / "intent"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    texts = []
    labels = []
    for intent in payload.get("intents", []):
        name = intent["name"]
        for example in intent.get("examples", []):
            texts.append(example)
            labels.append(name)
    return texts, labels, payload


def build_pipelines():
    vectorizer = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        lowercase=True,
        token_pattern=r"\b\w+\b",
    )

    nb_pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("clf", MultinomialNB()),
    ])

    logreg_pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("clf", LogisticRegression(max_iter=1000, solver="lbfgs")),
    ])

    return {
        "multinomial_nb": nb_pipeline,
        "logistic_regression": logreg_pipeline,
    }


def train(dataset_path: Path, test_size: float = 0.2, random_state: int = 42):
    texts, labels, meta = load_dataset(dataset_path)
    if not texts:
        raise ValueError("Dataset rỗng, không thể huấn luyện")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=test_size, random_state=random_state, stratify=labels
    )

    pipelines = build_pipelines()
    best_model = None
    best_metrics = None

    for name, pipeline in pipelines.items():
        start = time.perf_counter()
        pipeline.fit(X_train, y_train)
        train_duration = time.perf_counter() - start

        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        cm = confusion_matrix(y_test, y_pred, labels=sorted(set(labels)))

        metrics = {
            "model": name,
            "accuracy": acc,
            "train_duration_sec": train_duration,
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "labels": sorted(set(labels)),
            "dataset_version": meta.get("version"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "test_size": test_size,
            "samples": len(texts),
        }

        if best_model is None or acc > best_metrics["accuracy"]:
            best_model = pipeline
            best_metrics = metrics

    assert best_model is not None

    model_path = ARTIFACT_DIR / "intent_model.joblib"
    metrics_path = ARTIFACT_DIR / "metrics.json"
    joblib.dump(best_model, model_path)
    metrics_path.write_text(json.dumps(best_metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    log_entry = {
        "event": "train_intent",
        "model": best_metrics["model"],
        "accuracy": best_metrics["accuracy"],
        "timestamp": best_metrics["timestamp"],
        "samples": best_metrics["samples"],
        "dataset_version": best_metrics["dataset_version"],
        "artifact": str(model_path.relative_to(ROOT_DIR)),
    }

    log_file = LOG_DIR / "train.log"
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return model_path, metrics_path, best_metrics


def parse_args():
    parser = argparse.ArgumentParser(description="Huấn luyện model intent cho chatbot")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="Đường dẫn tới intent_dataset.json")
    parser.add_argument("--test-size", type=float, default=0.2, help="Tỉ lệ dữ liệu test")
    parser.add_argument("--seed", type=int, default=42, help="Giá trị random seed")
    return parser.parse_args()


def main():
    args = parse_args()
    model_path, metrics_path, metrics = train(args.dataset, test_size=args.test_size, random_state=args.seed)
    print("Huấn luyện hoàn tất:")
    print(f"  Model: {metrics['model']}")
    print(f"  Accuracy: {metrics['accuracy']:.4f}")
    print(f"  Model artifact: {model_path}")
    print(f"  Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
