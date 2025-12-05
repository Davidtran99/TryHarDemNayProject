#!/usr/bin/env python3
"""
Script to set embedding model to 1024 dim (multilingual-e5-large) on Hugging Face Spaces.
This fixes the dimension mismatch: query=768, stored=1024.
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

def set_secret(api, repo_id, key, value):
    """Set a secret on Hugging Face Space."""
    try:
        # Delete existing secret first
        try:
            api.delete_space_secret(repo_id=repo_id, key=key, token=api.token)
            print(f"🗑️  Deleted existing secret: {key}")
        except Exception:
            pass  # Secret doesn't exist, continue
        
        # Add new secret
        api.add_space_secret(repo_id=repo_id, key=key, value=value, token=api.token)
        print(f"✅ Set secret: {key}={value}")
        return True
    except Exception as e:
        print(f"❌ Error setting secret {key}: {e}")
        return False

def main():
    repo_id = "davidtran999/hue-portal-backend"
    
    print("🔧 Setting embedding model to 1024 dim (multilingual-e5-large)")
    print(f"📦 Repository: {repo_id}\n")
    
    # Get token
    token = get_hf_token()
    if not token:
        return
    
    api = HfApi(token=token)
    
    # Set embedding model to multilingual-e5-large (1024 dim)
    success = set_secret(api, repo_id, "EMBEDDING_MODEL", "multilingual-e5-large")
    
    if success:
        print("\n✅ Successfully set embedding model to multilingual-e5-large (1024 dim)")
        print("\n📊 This will fix dimension mismatch:")
        print("   - Before: query=768, stored=1024 ❌")
        print("   - After:  query=1024, stored=1024 ✅")
        print("\n🔄 Rebuild your HF Space to apply changes!")
        print("   → Vector search will work again after rebuild")
    else:
        print("\n❌ Failed to set embedding model")

if __name__ == "__main__":
    main()




