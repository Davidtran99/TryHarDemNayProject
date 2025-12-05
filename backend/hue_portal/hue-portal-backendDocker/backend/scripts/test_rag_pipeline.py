#!/usr/bin/env python
"""
Script để test RAG pipeline với data mới.
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

from hue_portal.core.rag import rag_pipeline
from hue_portal.chatbot.chatbot import Chatbot


def test_rag_procedure():
    """Test RAG với queries về procedure."""
    print("="*60)
    print("Test RAG Pipeline - Procedure")
    print("="*60)
    
    test_queries = [
        "Làm thủ tục cư trú cần gì?",
        "Thủ tục đăng ký thường trú",
        "Làm thủ tục PCCC như thế nào?",
        "Thủ tục ANTT cần giấy tờ gì?",
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            result = rag_pipeline(query, 'search_procedure', top_k=3)
            print(f"   ✅ Results: {result['count']}")
            print(f"   ✅ Confidence: {result['confidence']:.4f}")
            if result['count'] > 0:
                print(f"   ✅ Answer preview: {result['answer'][:150]}...")
                print(f"   ✅ Documents:")
                for i, doc in enumerate(result['documents'][:3], 1):
                    print(f"      {i}. {doc.title} - {doc.domain}")
            else:
                print("   ⚠️ No results found")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_rag_advisory():
    """Test RAG với queries về advisory."""
    print("\n" + "="*60)
    print("Test RAG Pipeline - Advisory")
    print("="*60)
    
    test_queries = [
        "Cảnh báo lừa đảo giả danh công an",
        "Lừa đảo mạo danh cán bộ",
        "Cảnh giác lừa đảo online",
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            result = rag_pipeline(query, 'search_advisory', top_k=3)
            print(f"   ✅ Results: {result['count']}")
            print(f"   ✅ Confidence: {result['confidence']:.4f}")
            if result['count'] > 0:
                print(f"   ✅ Answer preview: {result['answer'][:150]}...")
                print(f"   ✅ Documents:")
                for i, doc in enumerate(result['documents'][:3], 1):
                    print(f"      {i}. {doc.title}")
            else:
                print("   ⚠️ No results found")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_chatbot_integration():
    """Test chatbot integration."""
    print("\n" + "="*60)
    print("Test Chatbot Integration")
    print("="*60)
    
    chatbot = Chatbot()
    
    test_queries = [
        "Làm thủ tục cư trú cần gì?",
        "Cảnh báo lừa đảo giả danh công an",
        "Thủ tục PCCC như thế nào?",
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            response = chatbot.generate_response(query)
            print(f"   ✅ Intent: {response.get('intent', 'N/A')}")
            print(f"   ✅ Confidence: {response.get('confidence', 0):.4f}")
            print(f"   ✅ Results: {response.get('count', 0)}")
            if response.get('results'):
                first_result = response['results'][0].get('data', {})
                print(f"   ✅ First result: {first_result.get('title', 'N/A')}")
            print(f"   ✅ Message preview: {response.get('message', '')[:150]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    print("="*60)
    print("RAG Pipeline & Chatbot Integration Test")
    print("="*60)
    
    # Test RAG pipeline
    test_rag_procedure()
    test_rag_advisory()
    
    # Test chatbot integration
    test_chatbot_integration()
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)


if __name__ == "__main__":
    main()

