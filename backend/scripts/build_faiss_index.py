"""
Script to build FAISS indexes for all models.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
HUE_PORTAL_DIR = BACKEND_DIR / "hue_portal"

for path in (HUE_PORTAL_DIR, BACKEND_DIR, ROOT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")

import django
django.setup()

from hue_portal.core.models import Procedure, Fine, Office, Advisory
from hue_portal.core.faiss_index import build_faiss_index_for_model


def main():
    parser = argparse.ArgumentParser(description="Build FAISS indexes for models")
    parser.add_argument("--model", choices=["procedure", "fine", "office", "advisory", "all"],
                       default="all", help="Which model to process")
    parser.add_argument("--index-type", choices=["Flat", "IVF", "HNSW"], default="IVF",
                       help="Type of FAISS index")
    args = parser.parse_args()
    
    print("="*60)
    print("FAISS Index Builder")
    print("="*60)
    
    models_to_process = []
    if args.model == "all":
        models_to_process = [
            (Procedure, "Procedure"),
            (Fine, "Fine"),
            (Office, "Office"),
            (Advisory, "Advisory"),
        ]
    else:
        model_map = {
            "procedure": (Procedure, "Procedure"),
            "fine": (Fine, "Fine"),
            "office": (Office, "Office"),
            "advisory": (Advisory, "Advisory"),
        }
        if args.model in model_map:
            models_to_process = [model_map[args.model]]
    
    for model_class, model_name in models_to_process:
        try:
            build_faiss_index_for_model(model_class, model_name, index_type=args.index_type)
        except Exception as e:
            print(f"❌ Error building index for {model_name}: {e}")
    
    print("\n" + "="*60)
    print("Index building complete")
    print("="*60)


if __name__ == "__main__":
    main()

