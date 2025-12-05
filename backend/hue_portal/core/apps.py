from django.apps import AppConfig
import os
import logging

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "hue_portal.core"

    def ready(self):
        print('[CoreConfig] 🔔 ready() method called', flush=True)
        logger.info('[CoreConfig] ready() method called')
        
        from . import signals  # noqa: F401
        
        # Preload models in worker process (Gunicorn workers are separate processes)
        # This ensures models are loaded when worker starts, not on first request
        # Skip preload if running migrations or other management commands
        import sys
        if 'migrate' in sys.argv or 'collectstatic' in sys.argv or 'generate_legal_questions' in sys.argv or 'train_intent' in sys.argv or 'populate_legal_tsv' in sys.argv:
            print('[CoreConfig] ⏭️ Skipping model preload (management command)', flush=True)
            logger.info('[CoreConfig] Skipping model preload (management command)')
            return
        
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        print(f'[CoreConfig] 🔍 DJANGO_SETTINGS_MODULE: {django_settings}', flush=True)
        logger.info(f'[CoreConfig] DJANGO_SETTINGS_MODULE: {django_settings}')
        
        if django_settings:
            try:
                print('[CoreConfig] 🔄 Preloading models in worker process...', flush=True)
                logger.info('[CoreConfig] Preloading models in worker process...')
                
                # 1. Preload Embedding Model (BGE-M3)
                try:
                    print('[CoreConfig] 📦 Preloading embedding model (BGE-M3)...', flush=True)
                    from .embeddings import get_embedding_model
                    embedding_model = get_embedding_model()
                    if embedding_model:
                        print('[CoreConfig] ✅ Embedding model preloaded successfully', flush=True)
                        logger.info('[CoreConfig] Embedding model preloaded successfully')
                    else:
                        print('[CoreConfig] ⚠️ Embedding model not loaded', flush=True)
                except Exception as e:
                    print(f'[CoreConfig] ⚠️ Embedding model preload failed: {e}', flush=True)
                    logger.warning(f'[CoreConfig] Embedding model preload failed: {e}')
                
                # 2. Preload LLM Model (llama.cpp)
                llm_provider = os.environ.get('DEFAULT_LLM_PROVIDER') or os.environ.get('LLM_PROVIDER', '')
                if llm_provider.lower() == 'llama_cpp':
                    try:
                        print('[CoreConfig] 📦 Preloading LLM model (llama.cpp)...', flush=True)
                        from hue_portal.chatbot.llm_integration import get_llm_generator
                        llm_gen = get_llm_generator()
                        if llm_gen and hasattr(llm_gen, 'llama_cpp') and llm_gen.llama_cpp:
                            print('[CoreConfig] ✅ LLM model preloaded successfully', flush=True)
                            logger.info('[CoreConfig] LLM model preloaded successfully')
                        else:
                            print('[CoreConfig] ⚠️ LLM model not loaded (may load on first request)', flush=True)
                    except Exception as e:
                        print(f'[CoreConfig] ⚠️ LLM model preload failed: {e} (will load on first request)', flush=True)
                        logger.warning(f'[CoreConfig] LLM model preload failed: {e}')
                else:
                    print(f'[CoreConfig] ⏭️ Skipping LLM preload (provider is {llm_provider or "not set"}, not llama_cpp)', flush=True)
                
                # 3. Preload Reranker Model
                try:
                    print('[CoreConfig] 📦 Preloading reranker model...', flush=True)
                    from .reranker import get_reranker
                    reranker = get_reranker()
                    if reranker:
                        print('[CoreConfig] ✅ Reranker model preloaded successfully', flush=True)
                        logger.info('[CoreConfig] Reranker model preloaded successfully')
                    else:
                        print('[CoreConfig] ⚠️ Reranker model not loaded (may load on first request)', flush=True)
                except Exception as e:
                    print(f'[CoreConfig] ⚠️ Reranker preload failed: {e} (will load on first request)', flush=True)
                    logger.warning(f'[CoreConfig] Reranker preload failed: {e}')
                
                print('[CoreConfig] ✅ Model preload completed in worker process', flush=True)
                logger.info('[CoreConfig] Model preload completed in worker process')
            except Exception as e:
                print(f'[CoreConfig] ⚠️ Model preload error: {e} (models will load on first request)', flush=True)
                logger.warning(f'[CoreConfig] Model preload error: {e}')

