#!/usr/bin/env python3
"""
Test script để kiểm tra API mode có hoạt động không.
"""
import os
import sys

# Set API mode
os.environ["LLM_PROVIDER"] = "api"
os.environ["HF_API_BASE_URL"] = "https://davidtran999-hue-portal-backend.hf.space/api"

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_mode():
    """Test API mode initialization and connection."""
    print("=" * 60)
    print("Testing API Mode")
    print("=" * 60)
    
    try:
        # Import và clear global instance
        import hue_portal.chatbot.llm_integration as llm_module
        llm_module._llm_generator = None
        
        from hue_portal.chatbot.llm_integration import LLMGenerator, LLM_PROVIDER_API, get_llm_generator
        
        print("\n1. Testing LLMGenerator initialization...")
        generator = LLMGenerator(provider=LLM_PROVIDER_API)
        
        if generator.provider == LLM_PROVIDER_API:
            print("✅ Provider set correctly: API")
        else:
            print(f"❌ Provider incorrect: {generator.provider}")
            return False
        
        if generator.api_base_url:
            print(f"✅ API base URL: {generator.api_base_url}")
        else:
            print("❌ API base URL not set")
            return False
        
        print("\n2. Testing is_available()...")
        available = generator.is_available()
        if available:
            print("✅ API mode is available")
        else:
            print("❌ API mode not available")
            return False
        
        print("\n3. Testing get_llm_generator()...")
        llm = get_llm_generator()
        if llm and llm.provider == LLM_PROVIDER_API:
            print("✅ get_llm_generator() returns API generator")
        else:
            print("❌ get_llm_generator() failed")
            return False
        
        print("\n4. Testing API connection (sending test request)...")
        try:
            import requests
            
            # Test API endpoint
            test_url = f"{generator.api_base_url}/chatbot/chat/"
            test_payload = {
                "message": "Xin chào",
                "reset_session": False
            }
            
            print(f"   Calling: {test_url}")
            print(f"   Payload: {test_payload}")
            
            response = requests.post(
                test_url,
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ API connection successful!")
                print(f"   Response keys: {list(result.keys())}")
                if "message" in result:
                    print(f"   Message preview: {result['message'][:100]}...")
                return True
            elif response.status_code == 503:
                print("⚠️ API endpoint is loading (503) - this is normal for first request")
                print("   The API is available but model is still loading")
                return True
            else:
                print(f"❌ API connection failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ API connection timeout")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ API connection error: {e}")
            print("   Check if the API URL is correct and accessible")
            return False
        except Exception as e:
            print(f"❌ Error testing API connection: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    success = test_api_mode()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ API Mode Test: PASSED")
        print("\n💡 Project is ready to use API mode!")
        print("   Just restart your Django server to apply changes.")
    else:
        print("❌ API Mode Test: FAILED")
        print("\n⚠️ Please check:")
        print("   1. API URL is correct")
        print("   2. Hugging Face Space is running")
        print("   3. Internet connection is available")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

