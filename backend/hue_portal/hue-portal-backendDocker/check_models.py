#!/usr/bin/env python3
"""
Script to check which models are currently being used on Hugging Face Space.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def check_embedding_model():
    """Check embedding model configuration."""
    from hue_portal.core.embeddings import (
        DEFAULT_MODEL_NAME,
        FALLBACK_MODEL_NAME,
        AVAILABLE_MODELS,
        get_embedding_model
    )
    
    print("=" * 60)
    print("🔍 EMBEDDING MODEL CONFIGURATION")
    print("=" * 60)
    
    # Check environment variable
    env_model = os.environ.get("EMBEDDING_MODEL")
    if env_model:
        print(f"📌 EMBEDDING_MODEL env var: {env_model}")
    else:
        print(f"📌 EMBEDDING_MODEL env var: Not set (using default)")
    
    print(f"📌 Default model: {DEFAULT_MODEL_NAME}")
    print(f"📌 Fallback model: {FALLBACK_MODEL_NAME}")
    
    # Try to load model
    print("\n🔄 Attempting to load embedding model...")
    try:
        model = get_embedding_model()
        if model:
            # Get dimension
            test_embedding = model.encode("test", show_progress_bar=False)
            dim = len(test_embedding)
            print(f"✅ Model loaded successfully!")
            print(f"   Model name: {DEFAULT_MODEL_NAME}")
            print(f"   Dimension: {dim}")
            print(f"   Status: ✅ GOOD")
            
            # Evaluate
            if dim >= 768:
                print(f"   Quality: ⭐⭐⭐⭐ High quality (768+ dim)")
            elif dim >= 384:
                print(f"   Quality: ⭐⭐⭐ Good quality (384 dim)")
            else:
                print(f"   Quality: ⭐⭐ Basic quality")
        else:
            print("❌ Failed to load model")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n📊 Available models:")
    for key, value in AVAILABLE_MODELS.items():
        marker = "⭐" if value == DEFAULT_MODEL_NAME else "  "
        print(f"   {marker} {key}: {value}")


def check_llm_model():
    """Check LLM model configuration."""
    from hue_portal.chatbot.llm_integration import (
        LLM_PROVIDER,
        LLM_PROVIDER_NONE,
        LLM_PROVIDER_OPENAI,
        LLM_PROVIDER_ANTHROPIC,
        LLM_PROVIDER_OLLAMA,
        LLM_PROVIDER_HUGGINGFACE,
        LLM_PROVIDER_LOCAL,
        get_llm_generator
    )
    
    print("\n" + "=" * 60)
    print("🔍 LLM MODEL CONFIGURATION")
    print("=" * 60)
    
    print(f"📌 LLM_PROVIDER: {LLM_PROVIDER}")
    
    if LLM_PROVIDER == LLM_PROVIDER_NONE:
        print("⚠️  No LLM provider configured!")
        print("   Status: ❌ NOT USING LLM (template-based only)")
        print("   Quality: ⭐⭐ Basic (no LLM generation)")
        print("\n💡 To enable LLM, set LLM_PROVIDER to one of:")
        print("   - ollama (for local Qwen)")
        print("   - openai (for GPT)")
        print("   - anthropic (for Claude)")
        print("   - huggingface (for HF Inference API)")
        print("   - local (for local Transformers)")
    elif LLM_PROVIDER == LLM_PROVIDER_OPENAI:
        model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        print(f"✅ Using OpenAI")
        print(f"   Model: {model}")
        print(f"   Status: ✅ GOOD")
        print(f"   Quality: ⭐⭐⭐⭐⭐ Excellent")
    elif LLM_PROVIDER == LLM_PROVIDER_ANTHROPIC:
        model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        print(f"✅ Using Anthropic Claude")
        print(f"   Model: {model}")
        print(f"   Status: ✅ EXCELLENT")
        print(f"   Quality: ⭐⭐⭐⭐⭐ Best for Vietnamese")
    elif LLM_PROVIDER == LLM_PROVIDER_OLLAMA:
        model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        print(f"✅ Using Ollama (local)")
        print(f"   Model: {model}")
        print(f"   Base URL: {base_url}")
        print(f"   Status: ✅ GOOD (if Ollama running)")
        print(f"   Quality: ⭐⭐⭐⭐ Very good for Vietnamese")
    elif LLM_PROVIDER == LLM_PROVIDER_HUGGINGFACE:
        model = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        print(f"✅ Using Hugging Face Inference API")
        print(f"   Model: {model}")
        print(f"   Status: ✅ GOOD")
        print(f"   Quality: ⭐⭐⭐⭐ Good for Vietnamese")
    elif LLM_PROVIDER == LLM_PROVIDER_LOCAL:
        model = os.environ.get("LOCAL_MODEL_PATH", "Qwen/Qwen2.5-1.5B-Instruct")
        device = os.environ.get("LOCAL_MODEL_DEVICE", "auto")
        print(f"✅ Using Local Transformers")
        print(f"   Model: {model}")
        print(f"   Device: {device}")
        print(f"   Status: ✅ GOOD (if model loaded)")
        print(f"   Quality: ⭐⭐⭐⭐ Good for Vietnamese")
    
    # Try to get LLM generator
    print("\n🔄 Checking LLM availability...")
    try:
        llm = get_llm_generator()
        if llm and llm.is_available():
            print("✅ LLM is available and ready!")
        else:
            print("⚠️  LLM is not available")
    except Exception as e:
        print(f"❌ Error checking LLM: {e}")


def main():
    """Main function."""
    print("\n" + "=" * 60)
    print("📊 MODEL STATUS CHECK")
    print("=" * 60)
    print()
    
    check_embedding_model()
    check_llm_model()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    
    # Embedding summary
    from hue_portal.core.embeddings import DEFAULT_MODEL_NAME
    embedding_model = os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL_NAME)
    print(f"Embedding: {embedding_model}")
    
    # LLM summary
    from hue_portal.chatbot.llm_integration import LLM_PROVIDER, LLM_PROVIDER_NONE
    if LLM_PROVIDER == LLM_PROVIDER_NONE:
        print("LLM: None (template-based only)")
    else:
        print(f"LLM: {LLM_PROVIDER}")
    
    print("\n💡 Recommendations:")
    print("   - Embedding: multilingual-mpnet (current) is good ✅")
    print("   - LLM: Consider adding Qwen 2.5 for better answers")
    print()


if __name__ == "__main__":
    main()




