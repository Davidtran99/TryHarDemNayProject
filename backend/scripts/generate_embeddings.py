"""
Script to generate and store embeddings for Procedure, Fine, Office, Advisory models.
"""
import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
HUE_PORTAL_DIR = BACKEND_DIR / "hue_portal"

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

import django
django.setup()

from hue_portal.core.models import Procedure, Fine, Office, Advisory, LegalSection
from hue_portal.core.embeddings import (
    get_embedding_model,
    generate_embeddings_batch,
    get_embedding_dimension
)


def prepare_text_for_embedding(obj) -> str:
    """
    Prepare text from model instance for embedding.
    """
    if isinstance(obj, Procedure):
        fields = [obj.title, obj.domain, obj.level, obj.conditions, obj.dossier]
    elif isinstance(obj, Fine):
        fields = [obj.name, obj.code, obj.article, obj.decree, obj.remedial]
    elif isinstance(obj, Office):
        fields = [obj.unit_name, obj.address, obj.district, obj.service_scope]
    elif isinstance(obj, Advisory):
        fields = [obj.title, obj.summary]
    elif isinstance(obj, LegalSection):
        fields = [obj.section_code, obj.section_title, obj.content, getattr(obj.document, "title", "")]
    else:
        return ""
    
    # Combine non-empty fields
    text = " ".join(str(f) for f in fields if f and str(f).strip())
    return text.strip()


def generate_embeddings_for_model(model_class, model_name: str, batch_size: int = 32, dry_run: bool = False):
    """
    Generate embeddings for all instances of a model.
    
    Args:
        model_class: Django model class.
        model_name: Name of the model (for display).
        batch_size: Batch size for processing.
        dry_run: If True, only show what would be done without saving.
    """
    print(f"\n{'='*60}")
    print(f"Processing {model_name}")
    print(f"{'='*60}")
    
    # Get all instances
    instances = list(model_class.objects.all())
    total = len(instances)
    
    if total == 0:
        print(f"No {model_name} instances found. Skipping.")
        return 0, 0
    
    print(f"Found {total} {model_name} instances")
    
    # Prepare texts
    texts = []
    valid_indices = []
    for idx, instance in enumerate(instances):
        text = prepare_text_for_embedding(instance)
        if text:
            texts.append(text)
            valid_indices.append(idx)
        else:
            print(f"⚠️ Skipping {model_name} ID {instance.id}: empty text")
    
    if not texts:
        print(f"No valid texts found for {model_name}. Skipping.")
        return 0, 0
    
    print(f"Generating embeddings for {len(texts)} valid instances...")
    
    # Load model
    model = get_embedding_model()
    if model is None:
        print(f"❌ Cannot load embedding model. Skipping {model_name}.")
        return 0, 0
    
    # Generate embeddings
    embeddings = generate_embeddings_batch(texts, model=model, batch_size=batch_size)
    
    # Save embeddings (if not dry run)
    saved = 0
    failed = 0
    
    for idx, embedding in zip(valid_indices, embeddings):
        instance = instances[idx]
        
        if embedding is None:
            print(f"⚠️ Failed to generate embedding for {model_name} ID {instance.id}")
            failed += 1
            continue
        
        if not dry_run:
            # Convert numpy array to binary for storage
            try:
                import pickle
                embedding_binary = pickle.dumps(embedding)
                instance.embedding = embedding_binary
                instance.save(update_fields=['embedding'])
                print(f"✅ Generated and saved embedding for {model_name} ID {instance.id} (dim={len(embedding)})")
                saved += 1
            except Exception as e:
                print(f"❌ Error saving embedding for {model_name} ID {instance.id}: {e}")
                failed += 1
        else:
            print(f"[DRY RUN] Would save embedding for {model_name} ID {instance.id} (dim={len(embedding)})")
            saved += 1
    
    print(f"\n{model_name} Summary: {saved} saved, {failed} failed")
    return saved, failed


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for all models")
    parser.add_argument("--model", choices=["procedure", "fine", "office", "advisory", "legal", "all"], 
                       default="all", help="Which model to process")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for embedding generation")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without saving")
    parser.add_argument("--model-name", type=str, help="Override embedding model name")
    args = parser.parse_args()
    
    print("="*60)
    print("Embedding Generation Script")
    print("="*60)
    
    if args.dry_run:
        print("⚠️ DRY RUN MODE - No changes will be saved")
    
    if args.model_name:
        print(f"Using model: {args.model_name}")
        get_embedding_model(model_name=args.model_name, force_reload=True)
    else:
        print(f"Using default model: keepitreal/vietnamese-sbert-v2")
    
    # Check model dimension
    dim = get_embedding_dimension()
    if dim > 0:
        print(f"Embedding dimension: {dim}")
    else:
        print("⚠️ Could not determine embedding dimension")
    
    total_saved = 0
    total_failed = 0
    
    models_to_process = []
    if args.model == "all":
        models_to_process = [
            (Procedure, "Procedure"),
            (Fine, "Fine"),
            (Office, "Office"),
            (Advisory, "Advisory"),
            (LegalSection, "LegalSection"),
        ]
    else:
        model_map = {
            "procedure": (Procedure, "Procedure"),
            "fine": (Fine, "Fine"),
            "office": (Office, "Office"),
            "advisory": (Advisory, "Advisory"),
            "legal": (LegalSection, "LegalSection"),
        }
        if args.model in model_map:
            models_to_process = [model_map[args.model]]
    
    for model_class, model_name in models_to_process:
        saved, failed = generate_embeddings_for_model(
            model_class, model_name, 
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        total_saved += saved
        total_failed += failed
    
    print("\n" + "="*60)
    print("Final Summary")
    print("="*60)
    print(f"Total saved: {total_saved}")
    print(f"Total failed: {total_failed}")
    print("="*60)


if __name__ == "__main__":
    main()

