"""
Modal deployment script for Hue Portal Backend (Django)
Based on flux-modal pattern: https://github.com/omarkortam/flux-modal
"""
import os
import subprocess
from pathlib import Path

import modal

# Build Docker image with all dependencies
hue_backend_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git",
        "build-essential",
        "tesseract-ocr",
        "tesseract-ocr-eng",
        "tesseract-ocr-vie",
        "libpoppler-cpp-dev",
        "pkg-config",
        "libgl1",
    )
    .pip_install(
        "Django==5.0.6",
        "djangorestframework==3.15.2",
        "django-cors-headers==4.4.0",
        "psycopg2-binary==2.9.9",
        "django-environ==0.11.2",
        "gunicorn==22.0.0",
        "whitenoise==6.6.0",
        "redis==5.0.6",
        "celery==5.4.0",
        "scikit-learn==1.3.2",
        "numpy==1.24.3",
        "scipy==1.11.4",
        "pydantic>=2.0.0,<3.0.0",
        "sentence-transformers>=2.2.0",
        "torch>=2.0.0",
        "faiss-cpu>=1.7.4",
        "python-docx==0.8.11",
        "PyMuPDF==1.24.3",
        "Pillow>=8.0.0,<12.0",
        "pytesseract==0.3.13",
        "requests>=2.31.0",
    )
    # Copy backend code
    .copy_local_dir("backend", "/app")
    .run_commands(
        "mkdir -p /app/hue_portal/static /app/hue_portal/media",
        "chmod +x /app/hue_portal/manage.py",
    )
)

app = modal.App(name="hue-portal-backend", image=hue_backend_image)


# Mount backend directory
backend_mount = modal.Mount.from_local_dir("backend", remote_path="/app")

@app.function(
    allow_concurrent_inputs=100,
    concurrency_limit=10,
    container_idle_timeout=300,  # 5 minutes
    timeout=600,  # 10 minutes max request time
    cpu=2,  # 2 CPUs
    memory=4096,  # 4GB RAM
    secrets=[
        modal.Secret.from_name("hue-portal-secrets", required=False),  # Optional for now
    ],
    mounts=[backend_mount],
)
@modal.web_server(8000, startup_timeout=180)
def web():
    """Start Django application with Gunicorn."""
    import os
    
    # Set working directory
    os.chdir("/app/hue_portal")
    
    # Run migrations
    print("[Modal] Running migrations...")
    migrate_result = subprocess.run(
        ["python", "manage.py", "migrate", "--noinput"],
        capture_output=True,
        text=True,
        check=False,
    )
    if migrate_result.returncode != 0:
        print(f"[Modal] Migration warning: {migrate_result.stderr[:200]}")
    else:
        print("[Modal] Migrations completed")
    
    # Collect static files
    print("[Modal] Collecting static files...")
    collect_result = subprocess.run(
        ["python", "manage.py", "collectstatic", "--noinput"],
        capture_output=True,
        text=True,
        check=False,
    )
    if collect_result.returncode != 0:
        print(f"[Modal] Collectstatic warning: {collect_result.stderr[:200]}")
    else:
        print("[Modal] Static files collected")
    
    # Start Gunicorn
    print("[Modal] Starting Gunicorn on 0.0.0.0:8000...")
    gunicorn_process = subprocess.Popen(
        [
            "gunicorn",
            "-b", "0.0.0.0:8000",
            "--workers", "2",  # Reduced for Modal
            "--timeout", "120",
            "--access-logfile", "-",
            "--error-logfile", "-",
            "hue_portal.wsgi:application",
        ],
        cwd="/app/hue_portal",
    )
    
    print("[Modal] Gunicorn started, waiting...")
    
    # Keep process alive and monitor
    import time
    try:
        while True:
            # Check if gunicorn is still running
            if gunicorn_process.poll() is not None:
                print(f"[Modal] Gunicorn exited with code {gunicorn_process.returncode}")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Modal] Shutting down...")
        gunicorn_process.terminate()
        gunicorn_process.wait()
