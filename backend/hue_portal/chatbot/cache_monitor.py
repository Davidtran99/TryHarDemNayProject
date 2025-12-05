"""
Monitor Hugging Face model cache directory to track download progress.
This is a simpler approach that monitors the cache directory size.
"""
import os
import time
import threading
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class CacheProgress:
    """Track cache directory size progress."""
    model_path: str
    cache_path: Optional[str] = None
    total_size_bytes: int = 0
    current_size_bytes: int = 0
    files_count: int = 0
    files_completed: int = 0
    last_updated: float = 0.0
    is_monitoring: bool = False
    
    @property
    def percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_size_bytes == 0:
            # Estimate based on typical model sizes
            if "32B" in self.model_path or "32b" in self.model_path:
                estimated_size = 70 * 1024 * 1024 * 1024  # ~70GB for 32B
            elif "7B" in self.model_path or "7b" in self.model_path:
                estimated_size = 15 * 1024 * 1024 * 1024  # ~15GB for 7B
            else:
                estimated_size = 5 * 1024 * 1024 * 1024  # ~5GB default
            return min(100.0, (self.current_size_bytes / estimated_size) * 100.0)
        return min(100.0, (self.current_size_bytes / self.total_size_bytes) * 100.0)
    
    @property
    def size_gb(self) -> float:
        """Get current size in GB."""
        return self.current_size_bytes / (1024 ** 3)
    
    @property
    def total_size_gb(self) -> float:
        """Get total size in GB."""
        if self.total_size_bytes == 0:
            # Estimate
            if "32B" in self.model_path or "32b" in self.model_path:
                return 70.0
            elif "7B" in self.model_path or "7b" in self.model_path:
                return 15.0
            else:
                return 5.0
        return self.total_size_bytes / (1024 ** 3)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "model_path": self.model_path,
            "cache_path": self.cache_path,
            "current_size_bytes": self.current_size_bytes,
            "current_size_gb": round(self.size_gb, 2),
            "total_size_bytes": self.total_size_bytes,
            "total_size_gb": round(self.total_size_gb, 2),
            "percentage": round(self.percentage, 2),
            "files_count": self.files_count,
            "files_completed": self.files_completed,
            "is_monitoring": self.is_monitoring,
            "last_updated": self.last_updated
        }


class CacheMonitor:
    """Monitor cache directory for download progress."""
    
    def __init__(self):
        self._progress: Dict[str, CacheProgress] = {}
        self._lock = threading.Lock()
        self._monitoring_threads: Dict[str, threading.Thread] = {}
    
    def get_or_create(self, model_path: str) -> CacheProgress:
        """Get or create progress tracker."""
        with self._lock:
            if model_path not in self._progress:
                self._progress[model_path] = CacheProgress(model_path=model_path)
            return self._progress[model_path]
    
    def get(self, model_path: str) -> Optional[CacheProgress]:
        """Get progress tracker."""
        with self._lock:
            return self._progress.get(model_path)
    
    def _get_cache_path(self, model_path: str) -> Optional[Path]:
        """Get cache path for model."""
        try:
            cache_dir = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
            repo_id = model_path.replace("/", "--")
            cache_path = Path(cache_dir) / "hub" / f"models--{repo_id}"
            return cache_path if cache_path.exists() else None
        except Exception:
            return None
    
    def _monitor_cache(self, model_path: str, interval: float = 2.0):
        """Monitor cache directory size."""
        progress = self.get_or_create(model_path)
        progress.is_monitoring = True
        
        cache_path = self._get_cache_path(model_path)
        if cache_path:
            progress.cache_path = str(cache_path)
        
        while progress.is_monitoring:
            try:
                if cache_path and cache_path.exists():
                    # Calculate current size
                    total_size = 0
                    file_count = 0
                    for file_path in cache_path.rglob("*"):
                        if file_path.is_file():
                            file_count += 1
                            total_size += file_path.stat().st_size
                    
                    progress.current_size_bytes = total_size
                    progress.files_count = file_count
                    progress.last_updated = time.time()
                    
                    # Check for key files to determine completion
                    key_files = ["config.json", "tokenizer.json", "model.safetensors", "pytorch_model.bin"]
                    found_files = []
                    for key_file in key_files:
                        if list(cache_path.rglob(key_file)):
                            found_files.append(key_file)
                    progress.files_completed = len(found_files)
                    
                    # Estimate total size if not set
                    if progress.total_size_bytes == 0 and progress.files_completed == len(key_files):
                        # All key files found, use current size as total
                        progress.total_size_bytes = total_size
                else:
                    # Cache doesn't exist yet, check if it was created
                    cache_path = self._get_cache_path(model_path)
                    if cache_path:
                        progress.cache_path = str(cache_path)
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error monitoring cache: {e}")
                time.sleep(interval)
    
    def start_monitoring(self, model_path: str, interval: float = 2.0):
        """Start monitoring cache directory."""
        with self._lock:
            if model_path not in self._monitoring_threads:
                thread = threading.Thread(
                    target=self._monitor_cache,
                    args=(model_path, interval),
                    daemon=True
                )
                thread.start()
                self._monitoring_threads[model_path] = thread
    
    def stop_monitoring(self, model_path: str):
        """Stop monitoring cache directory."""
        with self._lock:
            progress = self._progress.get(model_path)
            if progress:
                progress.is_monitoring = False
            if model_path in self._monitoring_threads:
                del self._monitoring_threads[model_path]
    
    def get_progress(self, model_path: str) -> Optional[Dict]:
        """Get progress as dictionary."""
        progress = self.get(model_path)
        if progress:
            return progress.to_dict()
        return None


# Global monitor instance
_global_monitor = CacheMonitor()


def get_cache_monitor() -> CacheMonitor:
    """Get global cache monitor instance."""
    return _global_monitor


# Import logger
import logging
logger = logging.getLogger(__name__)




