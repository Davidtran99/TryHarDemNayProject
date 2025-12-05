#!/usr/bin/env python3
"""
Script to push code directly to Hugging Face Space repository.
This will upload updated files to trigger a rebuild.
"""
import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, login
from huggingface_hub.utils import HfFolder

DEFAULT_SPACE_ID = "davidtran999/hue-portal-backend"

def get_hf_token() -> str:
    """Get HF token from environment or cache."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if token:
        return token
    
    # Try to read from cache
    try:
        token = HfFolder.get_token()
        if token:
            return token
    except:
        pass
    
    return None

def upload_file_to_space(api: HfApi, space_id: str, local_path: Path, repo_path: str) -> bool:
    """Upload a file to Space repository."""
    try:
        print(f"📤 Uploading {local_path.name} to {repo_path}...")
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=repo_path,
            repo_id=space_id,
            repo_type="space",
        )
        print(f"✅ Successfully uploaded {local_path.name}")
        return True
    except Exception as e:
        print(f"❌ Failed to upload {local_path.name}: {e}")
        return False

def push_code_to_space(space_id: str = DEFAULT_SPACE_ID) -> bool:
    """Push updated code files to Space to trigger rebuild."""
    hf_token = get_hf_token()
    if not hf_token:
        print("❌ No Hugging Face token found.")
        print("   Please set HF_TOKEN or HUGGINGFACE_HUB_TOKEN environment variable,")
        print("   or run: huggingface-cli login")
        return False
    
    try:
        login(token=hf_token)
        api = HfApi(token=hf_token)
        print(f"✅ Authenticated with Hugging Face Hub")
    except Exception as e:
        print(f"❌ Failed to authenticate: {e}")
        return False
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    backend_dir = project_root / "backend"
    hue_portal_backend_dir = script_dir
    
    print(f"\n📦 Preparing to push code to Space: {space_id}")
    print(f"   Project root: {project_root}")
    print(f"   Backend dir: {backend_dir}")
    print(f"   Hue portal backend dir: {hue_portal_backend_dir}\n")
    
    # Files to upload (relative to Space repo root)
    files_to_upload = [
        # Dockerfile
        (hue_portal_backend_dir / "Dockerfile", "Dockerfile"),
        # README
        (hue_portal_backend_dir / "README.md", "README.md"),
        # Requirements.txt (from backend)
        (backend_dir / "requirements.txt", "requirements.txt"),
    ]
    
    # Upload backend code (all Python files)
    backend_code_dir = backend_dir / "hue_portal"
    if backend_code_dir.exists():
        print(f"\n📤 Uploading backend code from {backend_code_dir}...")
        
        # Upload all Python files recursively
        python_files = list(backend_code_dir.rglob("*.py"))
        print(f"   Found {len(python_files)} Python files to upload...")
        
        uploaded_count = 0
        for local_file in python_files:
            # Skip __pycache__ and test files if needed
            if "__pycache__" in str(local_file) or ".pyc" in str(local_file):
                continue
            
            # Calculate relative path
            rel_path = local_file.relative_to(backend_code_dir)
            repo_path = f"backend/{rel_path}"
            
            if upload_file_to_space(api, space_id, local_file, repo_path):
                uploaded_count += 1
        
        print(f"✅ Uploaded {uploaded_count}/{len(python_files)} Python files")
    
    # Upload main files
    print(f"\n📤 Uploading main files...")
    success_count = 0
    for local_path, repo_path in files_to_upload:
        if local_path.exists():
            if upload_file_to_space(api, space_id, local_path, repo_path):
                success_count += 1
        else:
            print(f"⚠️  File not found: {local_path}")
    
    print(f"\n✅ Uploaded {success_count}/{len(files_to_upload)} main files")
    print(f"\n🔄 Space should automatically rebuild with the new code.")
    print(f"   Check build status at: https://huggingface.co/spaces/{space_id}")
    
    return success_count > 0

if __name__ == "__main__":
    space_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SPACE_ID
    success = push_code_to_space(space_id)
    sys.exit(0 if success else 1)

