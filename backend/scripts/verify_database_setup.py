"""
Script to verify database setup and migrations.
"""
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

from django.db import connection
from hue_portal.core.models import Procedure, Fine, Office, Advisory, AuditLog, MLMetrics, Synonym


def verify_extensions():
    """Verify PostgreSQL extensions are enabled."""
    print("\n" + "="*60)
    print("Verifying PostgreSQL Extensions")
    print("="*60)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname IN ('pg_trgm', 'unaccent')
            ORDER BY extname;
        """)
        results = cursor.fetchall()
        
        if results:
            print("✅ Extensions enabled:")
            for extname, extversion in results:
                print(f"   - {extname}: {extversion}")
        else:
            print("❌ No extensions found")
        return len(results) == 2


def verify_tables():
    """Verify all tables exist."""
    print("\n" + "="*60)
    print("Verifying Tables")
    print("="*60)
    
    tables = [
        ("core_procedure", Procedure),
        ("core_fine", Fine),
        ("core_office", Office),
        ("core_advisory", Advisory),
        ("core_auditlog", AuditLog),
        ("core_mlmetrics", MLMetrics),
        ("core_synonym", Synonym),
    ]
    
    all_ok = True
    for table_name, model_class in tables:
        try:
            count = model_class.objects.count()
            print(f"✅ {table_name}: {count} records")
        except Exception as e:
            print(f"❌ {table_name}: Error - {e}")
            all_ok = False
    
    return all_ok


def verify_fields():
    """Verify BM25 and embedding fields exist."""
    print("\n" + "="*60)
    print("Verifying Fields")
    print("="*60)
    
    models_to_check = [
        ("Procedure", Procedure),
        ("Fine", Fine),
        ("Office", Office),
        ("Advisory", Advisory),
    ]
    
    all_ok = True
    for model_name, model_class in models_to_check:
        has_tsv = hasattr(model_class, 'tsv_body')
        has_embedding = hasattr(model_class, 'embedding')
        
        if has_tsv and has_embedding:
            print(f"✅ {model_name}: tsv_body ✓, embedding ✓")
        else:
            print(f"❌ {model_name}: tsv_body={has_tsv}, embedding={has_embedding}")
            all_ok = False
    
    # Check AuditLog fields
    has_intent = hasattr(AuditLog, 'intent')
    has_confidence = hasattr(AuditLog, 'confidence')
    has_latency = hasattr(AuditLog, 'latency_ms')
    
    if has_intent and has_confidence and has_latency:
        print(f"✅ AuditLog: intent ✓, confidence ✓, latency_ms ✓")
    else:
        print(f"❌ AuditLog: intent={has_intent}, confidence={has_confidence}, latency_ms={has_latency}")
        all_ok = False
    
    # Check MLMetrics
    if hasattr(MLMetrics, 'date'):
        print(f"✅ MLMetrics: model exists")
    else:
        print(f"❌ MLMetrics: model not found")
        all_ok = False
    
    return all_ok


def verify_indexes():
    """Verify GIN indexes for tsv_body."""
    print("\n" + "="*60)
    print("Verifying Indexes")
    print("="*60)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE '%_tsv_idx'
            ORDER BY tablename;
        """)
        results = cursor.fetchall()
        
        if results:
            print("✅ GIN indexes found:")
            for indexname, tablename in results:
                print(f"   - {indexname} on {tablename}")
        else:
            print("⚠️ No GIN indexes found (may need to run migrations)")
        
        return len(results) >= 4


def test_bm25_search():
    """Test BM25 search functionality."""
    print("\n" + "="*60)
    print("Testing BM25 Search")
    print("="*60)
    
    try:
        from hue_portal.core.search_ml import search_with_ml
        
        # Test with Fine model
        from hue_portal.core.models import Fine
        
        if Fine.objects.count() > 0:
            results = search_with_ml(
                Fine.objects.all(),
                query="vượt đèn đỏ",
                text_fields=["name", "code", "article"],
                top_k=5,
                use_hybrid=False  # Test BM25 only
            )
            print(f"✅ BM25 search test: Found {len(results)} results")
            if results:
                print(f"   First result: {results[0].name[:50]}...")
            return True
        else:
            print("⚠️ No Fine records to test with")
            return True  # Not an error, just no data
    except Exception as e:
        print(f"❌ BM25 search test failed: {e}")
        return False


def main():
    print("="*60)
    print("Database Setup Verification")
    print("="*60)
    
    results = {
        "extensions": verify_extensions(),
        "tables": verify_tables(),
        "fields": verify_fields(),
        "indexes": verify_indexes(),
        "bm25_search": test_bm25_search(),
    }
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
    
    if all_passed:
        print("\n🎉 All checks passed! Database is ready.")
    else:
        print("\n⚠️ Some checks failed. Please review above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

