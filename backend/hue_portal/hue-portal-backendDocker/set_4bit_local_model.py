#!/usr/bin/env python3
"""
Script to set up Qwen 2.5 32B with 4-bit quantization on Hugging Face Spaces.
"""

import os
from huggingface_hub import HfApi
from huggingface_hub.utils import HfFolder

def get_hf_token():
    """Get Hugging Face token from cache."""
    token = HfFolder.get_token()
    if not token:
        print("❌ No Hugging Face token found!")
        print("💡 Run: huggingface-cli login")
        return None
    return token

def set_secrets(api, repo_id, secrets):
    """Set secrets on Hugging Face Space."""
    try:
        # Delete existing secrets first to avoid collisions
        existing_secrets = api.get_space_variables(repo_id=repo_id, token=api.token)
        existing_secret_names = [s.key for s in existing_secrets if hasattr(s, 'key')]
        
        for secret_name in secrets.keys():
            if secret_name in existing_secret_names:
                try:
                    api.delete_space_variable(repo_id=repo_id, key=secret_name, token=api.token)
                    print(f"🗑️  Deleted existing secret: {secret_name}")
                except Exception as e:
                    print(f"⚠️  Could not delete {secret_name}: {e}")
        
        # Add new secrets
        for key, value in secrets.items():
            api.add_space_secret(repo_id=repo_id, key=key, value=value, token=api.token)
            print(f"✅ Set secret: {key}")
        
        return True
    except Exception as e:
        print(f"❌ Error setting secrets: {e}")
        return False

def main():
    repo_id = "davidtran999/hue-portal-backend"
    
    print("🚀 Setting up Qwen 2.5 32B with 4-bit quantization on HF Space")
    print(f"📦 Repository: {repo_id}\n")
    
    # Get token
    token = get_hf_token()
    if not token:
        return
    
    api = HfApi(token=token)
    
    # Configuration for 4-bit Qwen 2.5 32B
    secrets = {
        "LLM_PROVIDER": "local",
        "LOCAL_MODEL_PATH": "Qwen/Qwen2.5-32B-Instruct",
        "LOCAL_MODEL_DEVICE": "cuda",
        "LOCAL_MODEL_4BIT": "true"
    }
    
    print("📋 Configuration:")
    for key, value in secrets.items():
        print(f"   {key}={value}")
    print()
    
    # Set secrets
    if set_secrets(api, repo_id, secrets):
        print("\n✅ Successfully configured 4-bit Qwen 2.5 32B!")
        print("\n📊 Expected Memory Usage:")
        print("   - VRAM: ~8-10GB")
        print("   - RAM: ~16GB+")
        print("   - Quality: ⭐⭐⭐⭐ (very good)")
        print("\n⚠️  Note: Model will be downloaded on first run (~70GB)")
        print("   First load may take several minutes.")
        print("\n🔄 Rebuild your HF Space to apply changes!")
    else:
        print("\n❌ Failed to set secrets")

if __name__ == "__main__":
    main()




