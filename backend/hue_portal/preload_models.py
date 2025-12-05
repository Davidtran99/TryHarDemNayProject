"""
Preload all models when worker process starts.
This module is imported to ensure models are loaded before first request.
"""
import os


def preload_all_models() -> None:
    """Preload embedding, LLM, and reranker models in the worker process."""
    print("[PRELOAD] 🔄 Starting model preload in worker process...", flush=True)
    try:
        # 1) Embedding model
        try:
            print("[PRELOAD] 📦 Preloading embedding model (BGE-M3)...", flush=True)
            from hue_portal.core.embeddings import get_embedding_model

            embedding_model = get_embedding_model()
            if embedding_model:
                print("[PRELOAD] ✅ Embedding model preloaded successfully", flush=True)
            else:
                print("[PRELOAD] ⚠️ Embedding model not loaded", flush=True)
        except Exception as e:
            print(f"[PRELOAD] ⚠️ Embedding model preload failed: {e}", flush=True)

        # 2) LLM model (llama.cpp)
        llm_provider = os.environ.get("DEFAULT_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "")
        if llm_provider.lower() == "llama_cpp":
            try:
                print("[PRELOAD] 📦 Preloading LLM model (llama.cpp)...", flush=True)
                from hue_portal.chatbot.llm_integration import get_llm_generator

                llm_gen = get_llm_generator()
                if llm_gen and hasattr(llm_gen, "llama_cpp") and llm_gen.llama_cpp:
                    print("[PRELOAD] ✅ LLM model preloaded successfully", flush=True)
                else:
                    print("[PRELOAD] ⚠️ LLM model not loaded (may load on first request)", flush=True)
            except Exception as e:
                print(f"[PRELOAD] ⚠️ LLM model preload failed: {e} (will load on first request)", flush=True)
        else:
            print(f"[PRELOAD] ⏭️ Skipping LLM preload (provider is {llm_provider or 'not set'}, not llama_cpp)", flush=True)

        # 3) Reranker model
        try:
            print("[PRELOAD] 📦 Preloading reranker model...", flush=True)
            from hue_portal.core.reranker import get_reranker

            reranker = get_reranker()
            if reranker:
                print("[PRELOAD] ✅ Reranker model preloaded successfully", flush=True)
            else:
                print("[PRELOAD] ⚠️ Reranker model not loaded (may load on first request)", flush=True)
        except Exception as e:
            print(f"[PRELOAD] ⚠️ Reranker preload failed: {e} (will load on first request)", flush=True)

        print("[PRELOAD] ✅ Model preload completed in worker process", flush=True)
    except Exception as e:
        print(f"[PRELOAD] ⚠️ Model preload error: {e} (models will load on first request)", flush=True)
        import traceback

        traceback.print_exc()


