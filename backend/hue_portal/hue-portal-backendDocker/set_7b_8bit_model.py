#!/usr/bin/env python3
"""
Set Hugging Face Space secrets for Qwen2.5-7B-Instruct with 8-bit quantization.
"""
import os
from huggingface_hub import HfApi, HfFolder

def set_7b_8bit_model():
    """Set model to 7B with 8-bit quantization on Hugging Face Space."""
    
    # Get HF token
    token = os.environ.get("HF_TOKEN") or HfFolder.get_token()
    if not token:
        print("❌ Error: HF_TOKEN not found. Set it as environment variable or login with: huggingface-cli login")
        return False
    
    api = HfApi(token=token)
    space_id = "davidtran999/hue-portal-backend"
    
    print(f"🔧 Setting model to Qwen2.5-7B-Instruct with 8-bit quantization...")
    print(f"   Space: {space_id}")
    
    try:
        # Use add_space_secret method
        api.add_space_secret(
            repo_id=space_id,
            key="LOCAL_MODEL_PATH",
            value="Qwen/Qwen2.5-7B-Instruct"
        )
        print("   ✅ LOCAL_MODEL_PATH = Qwen/Qwen2.5-7B-Instruct")
        
        api.add_space_secret(
            repo_id=space_id,
            key="LOCAL_MODEL_8BIT",
            value="true"
        )
        print("   ✅ LOCAL_MODEL_8BIT = true")
        
        api.add_space_secret(
            repo_id=space_id,
            key="LOCAL_MODEL_4BIT",
            value="false"
        )
        print("   ✅ LOCAL_MODEL_4BIT = false")
        
        print()
        print("✅ Đã set model 7B với 8-bit quantization thành công!")
        print("   Hugging Face Space sẽ tự động rebuild.")
        print()
        print("📊 CONFIG:")
        print("   Model: Qwen/Qwen2.5-7B-Instruct")
        print("   Quantization: 8-bit (~7GB VRAM)")
        print("   Thinking: ⭐⭐⭐⭐ (~98% accuracy)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    set_7b_8bit_model()

