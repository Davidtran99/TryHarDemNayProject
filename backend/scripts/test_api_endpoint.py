#!/usr/bin/env python
"""
Script để test chatbot API endpoint.
"""
import os
import requests
import json
import time
from typing import Dict, Any


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")


def test_health_endpoint():
    """Test health endpoint."""
    print("="*60)
    print("Test Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/chatbot/health/", timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status', 'N/A')}")
            print(f"Service: {data.get('service', 'N/A')}")
            print(f"Classifier Loaded: {data.get('classifier_loaded', False)}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is Django server running?")
        print("   Start server with: cd backend/hue_portal && POSTGRES_HOST=localhost POSTGRES_PORT=5433 python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_chatbot_api(query: str, expected_intent: str = None) -> Dict[str, Any]:
    """Test chatbot API with a query."""
    print(f"\n📝 Query: {query}")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat/",
            json={"message": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        latency_ms = (time.time() - start_time) * 1000
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            intent = data.get('intent', 'N/A')
            confidence = data.get('confidence', 0)
            count = data.get('count', 0)
            message_preview = data.get('message', '')[:100]
            
            print(f"   ✅ Intent: {intent}")
            print(f"   ✅ Confidence: {confidence:.4f}")
            print(f"   ✅ Results: {count}")
            print(f"   ✅ Latency: {latency_ms:.2f}ms")
            print(f"   ✅ Message preview: {message_preview}...")
            
            if expected_intent and intent != expected_intent:
                print(f"   ⚠️ Expected intent: {expected_intent}, got: {intent}")
            
            return {
                "success": True,
                "intent": intent,
                "confidence": confidence,
                "count": count,
                "latency_ms": latency_ms
            }
        else:
            print(f"   ❌ Error: {response.text}")
            return {"success": False, "error": response.text}
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to server")
        return {"success": False, "error": "Connection error"}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def main():
    print("="*60)
    print("Chatbot API Endpoint Test")
    print("="*60)
    
    # Test health endpoint first
    if not test_health_endpoint():
        print("\n⚠️ Health check failed. Please start Django server first.")
        return
    
    # Test chatbot API with various queries
    print("\n" + "="*60)
    print("Test Chatbot API Endpoint")
    print("="*60)
    
    test_cases = [
        ("Làm thủ tục cư trú cần gì?", "search_procedure"),
        ("Cảnh báo lừa đảo giả danh công an", "search_advisory"),
        ("Thủ tục PCCC như thế nào?", "search_procedure"),
        ("Mức phạt vượt đèn đỏ", "search_fine"),
        ("Địa chỉ công an tỉnh", "search_office"),
        ("Lừa đảo mạo danh cán bộ", "search_advisory"),
    ]
    
    results = []
    for query, expected_intent in test_cases:
        result = test_chatbot_api(query, expected_intent)
        results.append(result)
        time.sleep(0.5)  # Small delay between requests
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    avg_latency = sum(r.get("latency_ms", 0) for r in results if r.get("success", False)) / successful if successful > 0 else 0
    
    print(f"Successful: {successful}/{total}")
    print(f"Average Latency: {avg_latency:.2f}ms")
    
    # Intent accuracy
    correct_intents = sum(1 for i, (_, expected) in enumerate(test_cases) 
                         if results[i].get("intent") == expected)
    print(f"Intent Accuracy: {correct_intents}/{total} ({correct_intents/total*100:.1f}%)")
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)


if __name__ == "__main__":
    main()

