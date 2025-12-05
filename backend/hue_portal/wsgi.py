import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
application = get_wsgi_application()

# Preload models in worker process (Gunicorn workers are separate processes)
# This ensures models are loaded when worker starts, not on first request
print('[WSGI] 🔄 Preloading models in worker process...', flush=True)
try:
    # 1. Preload Embedding Model (BGE-M3)
    try:
        print('[WSGI] 📦 Preloading embedding model (BGE-M3)...', flush=True)
        from hue_portal.core.embeddings import get_embedding_model
        embedding_model = get_embedding_model()
        if embedding_model:
            print('[WSGI] ✅ Embedding model preloaded successfully', flush=True)
        else:
            print('[WSGI] ⚠️ Embedding model not loaded', flush=True)
    except Exception as e:
        print(f'[WSGI] ⚠️ Embedding model preload failed: {e}', flush=True)
    
    # 2. Preload LLM Model (llama.cpp)
    llm_provider = os.environ.get('DEFAULT_LLM_PROVIDER') or os.environ.get('LLM_PROVIDER', '')
    if llm_provider.lower() == 'llama_cpp':
        try:
            print('[WSGI] 📦 Preloading LLM model (llama.cpp)...', flush=True)
            from hue_portal.chatbot.llm_integration import get_llm_generator
            llm_gen = get_llm_generator()
            if llm_gen and hasattr(llm_gen, 'llama_cpp') and llm_gen.llama_cpp:
                print('[WSGI] ✅ LLM model preloaded successfully', flush=True)
            else:
                print('[WSGI] ⚠️ LLM model not loaded (may load on first request)', flush=True)
        except Exception as e:
            print(f'[WSGI] ⚠️ LLM model preload failed: {e} (will load on first request)', flush=True)
    else:
        print(f'[WSGI] ⏭️ Skipping LLM preload (provider is {llm_provider or "not set"}, not llama_cpp)', flush=True)
    
    # 3. Preload Reranker Model
    try:
        print('[WSGI] 📦 Preloading reranker model...', flush=True)
        from hue_portal.core.reranker import get_reranker
        reranker = get_reranker()
        if reranker:
            print('[WSGI] ✅ Reranker model preloaded successfully', flush=True)
        else:
            print('[WSGI] ⚠️ Reranker model not loaded (may load on first request)', flush=True)
    except Exception as e:
        print(f'[WSGI] ⚠️ Reranker preload failed: {e} (will load on first request)', flush=True)
    
    print('[WSGI] ✅ Model preload completed in worker process', flush=True)
except Exception as e:
    print(f'[WSGI] ⚠️ Model preload error: {e} (models will load on first request)', flush=True)

