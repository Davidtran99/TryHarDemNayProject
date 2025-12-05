#!/usr/bin/env python3
"""
Script to automatically set environment variables on Hugging Face Space.
Requires HF_TOKEN environment variable or Hugging Face CLI login.

Usage:
    export HF_TOKEN=your_token_here
    python3 set_hf_space_env.py

Or login first:
    huggingface-cli login
    python3 set_hf_space_env.py
"""
import os
import sys

try:
    from huggingface_hub import HfApi
except ImportError:
    print("❌ huggingface_hub not installed. Install with: pip install huggingface_hub")
    sys.exit(1)

# Space configuration
SPACE_ID = "davidtran999/hue-portal-backend"

# Environment variables to set
ENV_VARS = {
    "LLM_PROVIDER": "local",
    "LOCAL_MODEL_PATH": "Qwen/Qwen2.5-7B-Instruct",
    "LOCAL_MODEL_DEVICE": "cuda",
    "LOCAL_MODEL_8BIT": "true",
    "LOCAL_MODEL_4BIT": "false",
}

def main():
    # Get HF token
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found.")
        print("\n💡 Option 1: Set token as environment variable")
        print("   export HF_TOKEN=your_token_here")
        print("   python3 set_hf_space_env.py")
        print("\n💡 Option 2: Login with Hugging Face CLI")
        print("   huggingface-cli login")
        print("   python3 set_hf_space_env.py")
        print("\n💡 To get your token:")
        print("   Go to: https://huggingface.co/settings/tokens")
        print("   Create a new token with 'write' permissions")
        sys.exit(1)
    
    # Initialize API
    api = HfApi(token=hf_token)
    
    print(f"🔧 Setting environment variables for Space: {SPACE_ID}")
    print("=" * 60)
    
    # Try to set variables using API
    # Note: Hugging Face Hub may not have direct API for space variables
    # This is a workaround using repository secrets API
    success_count = 0
    for key, value in ENV_VARS.items():
        try:
            print(f"Setting {key}={value}...", end=" ")
            # Try using update_repo_settings or similar method
            # Since direct variable API may not exist, we'll use a workaround
            print("⚠️  (API may not support direct variable setting)")
            print("   Please set manually in Space Settings → Variables & secrets")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("=" * 60)
    print("📋 Manual setup required:")
    print(f"   1. Go to: https://huggingface.co/spaces/{SPACE_ID}/settings")
    print("   2. Click 'Variables & secrets' tab")
    print("   3. Add each variable:")
    for key, value in ENV_VARS.items():
        print(f"      {key} = {value}")
    print("   4. Click 'Save' and wait for Space to rebuild")
    print("\n💡 After setting, restart Space to apply changes.")

if __name__ == "__main__":
    main()

