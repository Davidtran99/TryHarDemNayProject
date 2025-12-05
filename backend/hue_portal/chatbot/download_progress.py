"""
Download progress tracker for Hugging Face models.
Tracks real-time download progress in bytes.
"""
import threading
import time
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DownloadProgress:
    """Track download progress for a single file."""
    filename: str
    total_bytes: int = 0
    downloaded_bytes: int = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    speed_bytes_per_sec: float = 0.0
    
    @property
    def percentage(self) -> float:
        """Calculate download percentage."""
        if self.total_bytes == 0:
            return 0.0
        return min(100.0, (self.downloaded_bytes / self.total_bytes) * 100.0)
    
    @property
    def is_complete(self) -> bool:
        """Check if download is complete."""
        return self.total_bytes > 0 and self.downloaded_bytes >= self.total_bytes
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at or time.time()
        return end_time - self.started_at


@dataclass
class ModelDownloadProgress:
    """Track overall download progress for a model."""
    model_path: str
    files: Dict[str, DownloadProgress] = field(default_factory=dict)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def update_file(self, filename: str, downloaded: int, total: int):
        """Update progress for a specific file."""
        if filename not in self.files:
            self.files[filename] = DownloadProgress(
                filename=filename,
                started_at=time.time()
            )
            if self.started_at is None:
                self.started_at = time.time()
        
        file_progress = self.files[filename]
        file_progress.downloaded_bytes = downloaded
        file_progress.total_bytes = total
        
        # Calculate speed
        if file_progress.started_at:
            elapsed = time.time() - file_progress.started_at
            if elapsed > 0:
                file_progress.speed_bytes_per_sec = downloaded / elapsed
        
        # Mark as complete
        if total > 0 and downloaded >= total:
            file_progress.completed_at = time.time()
    
    def complete_file(self, filename: str):
        """Mark a file as complete."""
        if filename in self.files:
            self.files[filename].completed_at = time.time()
    
    @property
    def total_bytes(self) -> int:
        """Get total bytes across all files."""
        return sum(f.total_bytes for f in self.files.values())
    
    @property
    def downloaded_bytes(self) -> int:
        """Get downloaded bytes across all files."""
        return sum(f.downloaded_bytes for f in self.files.values())
    
    @property
    def percentage(self) -> float:
        """Calculate overall download percentage."""
        total = self.total_bytes
        if total == 0:
            # If no total yet, count completed files
            if len(self.files) == 0:
                return 0.0
            completed = sum(1 for f in self.files.values() if f.is_complete)
            return (completed / len(self.files)) * 100.0
        return min(100.0, (self.downloaded_bytes / total) * 100.0)
    
    @property
    def is_complete(self) -> bool:
        """Check if all files are downloaded."""
        if len(self.files) == 0:
            return False
        return all(f.is_complete for f in self.files.values())
    
    @property
    def speed_bytes_per_sec(self) -> float:
        """Get overall download speed."""
        total_speed = sum(f.speed_bytes_per_sec for f in self.files.values() if f.started_at)
        return total_speed
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at or time.time()
        return end_time - self.started_at
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_path": self.model_path,
            "total_bytes": self.total_bytes,
            "downloaded_bytes": self.downloaded_bytes,
            "percentage": round(self.percentage, 2),
            "speed_bytes_per_sec": round(self.speed_bytes_per_sec, 2),
            "speed_mb_per_sec": round(self.speed_bytes_per_sec / (1024 * 1024), 2),
            "elapsed_time": round(self.elapsed_time, 2),
            "is_complete": self.is_complete,
            "files_count": len(self.files),
            "files_completed": sum(1 for f in self.files.values() if f.is_complete),
            "files": {
                name: {
                    "filename": f.filename,
                    "total_bytes": f.total_bytes,
                    "downloaded_bytes": f.downloaded_bytes,
                    "percentage": round(f.percentage, 2),
                    "speed_mb_per_sec": round(f.speed_bytes_per_sec / (1024 * 1024), 2),
                    "is_complete": f.is_complete
                }
                for name, f in self.files.items()
            }
        }


class ProgressTracker:
    """Thread-safe progress tracker for multiple models."""
    
    def __init__(self):
        self._progress: Dict[str, ModelDownloadProgress] = {}
        self._lock = threading.Lock()
    
    def get_or_create(self, model_path: str) -> ModelDownloadProgress:
        """Get or create progress tracker for a model."""
        with self._lock:
            if model_path not in self._progress:
                self._progress[model_path] = ModelDownloadProgress(model_path=model_path)
            return self._progress[model_path]
    
    def get(self, model_path: str) -> Optional[ModelDownloadProgress]:
        """Get progress tracker for a model."""
        with self._lock:
            return self._progress.get(model_path)
    
    def update(self, model_path: str, filename: str, downloaded: int, total: int):
        """Update download progress for a file."""
        progress = self.get_or_create(model_path)
        progress.update_file(filename, downloaded, total)
    
    def complete_file(self, model_path: str, filename: str):
        """Mark a file as complete."""
        progress = self.get(model_path)
        if progress:
            progress.complete_file(filename)
    
    def complete_model(self, model_path: str):
        """Mark entire model download as complete."""
        progress = self.get(model_path)
        if progress:
            progress.completed_at = time.time()
    
    def get_all(self) -> Dict[str, Dict]:
        """Get all progress as dictionary."""
        with self._lock:
            return {
                path: prog.to_dict()
                for path, prog in self._progress.items()
            }
    
    def get_model_progress(self, model_path: str) -> Optional[Dict]:
        """Get progress for a specific model."""
        progress = self.get(model_path)
        if progress:
            return progress.to_dict()
        return None


# Global progress tracker instance
_global_tracker = ProgressTracker()


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker instance."""
    return _global_tracker


def create_progress_callback(model_path: str):
    """
    Create a progress callback for huggingface_hub downloads.
    
    Usage:
        from huggingface_hub import snapshot_download
        callback = create_progress_callback("Qwen/Qwen2.5-32B-Instruct")
        snapshot_download(repo_id=model_path, resume_download=True, 
                         tqdm_class=callback)
    """
    tracker = get_progress_tracker()
    
    class ProgressCallback:
        """Progress callback for tqdm."""
        
        def __init__(self, *args, **kwargs):
            # Store tqdm arguments but don't initialize yet
            self.tqdm_args = args
            self.tqdm_kwargs = kwargs
            self.current_file = None
        
        def __call__(self, *args, **kwargs):
            # This will be called by huggingface_hub
            # We'll intercept the progress updates
            pass
        
        def update(self, n: int = 1):
            """Update progress."""
            if self.current_file:
                # Get current progress from tqdm
                if hasattr(self, 'n'):
                    downloaded = self.n
                else:
                    downloaded = n
                if hasattr(self, 'total'):
                    total = self.total
                else:
                    total = 0
                tracker.update(model_path, self.current_file, downloaded, total)
        
        def set_description(self, desc: str):
            """Set description (filename)."""
            # Extract filename from description
            if desc:
                self.current_file = desc.split()[-1] if ' ' in desc else desc
        
        def close(self):
            """Close progress bar."""
            if self.current_file:
                tracker.complete_file(model_path, self.current_file)
    
    return ProgressCallback


def create_hf_progress_callback(model_path: str):
    """
    Create a progress callback compatible with huggingface_hub.
    Returns a function that can be used with tqdm.
    """
    tracker = get_progress_tracker()
    current_file = [None]  # Use list to allow modification in nested function
    
    def progress_callback(tqdm_bar):
        """Progress callback function."""
        if tqdm_bar.desc:
            # Extract filename from description
            filename = tqdm_bar.desc.split()[-1] if ' ' in tqdm_bar.desc else tqdm_bar.desc
            if filename != current_file[0]:
                current_file[0] = filename
                if current_file[0] not in tracker.get_or_create(model_path).files:
                    tracker.get_or_create(model_path).files[current_file[0]] = DownloadProgress(
                        filename=current_file[0],
                        started_at=time.time()
                    )
        
        if current_file[0]:
            downloaded = getattr(tqdm_bar, 'n', 0)
            total = getattr(tqdm_bar, 'total', 0)
            tracker.update(model_path, current_file[0], downloaded, total)
    
    return progress_callback




