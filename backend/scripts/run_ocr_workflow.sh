#!/bin/bash
# Helper script để chạy OCR workflow với virtual environment
# Script này tự động detect worktree và chuyển sang đúng thư mục

set -e

# Tìm worktree thực tế
WORKTREE_PATH="/Users/davidtran/.cursor/worktrees/TryHarDemNayProject/q6Bp2"
CURRENT_DIR="$(pwd)"

# Nếu đang ở worktree, dùng thư mục hiện tại
if [ -f "$CURRENT_DIR/backend/scripts/run_ocr_workflow.py" ]; then
    PROJECT_ROOT="$CURRENT_DIR"
elif [ -f "$WORKTREE_PATH/backend/scripts/run_ocr_workflow.py" ]; then
    PROJECT_ROOT="$WORKTREE_PATH"
    echo "📍 Chuyển sang worktree: $WORKTREE_PATH"
else
    echo "❌ Không tìm thấy run_ocr_workflow.py"
    exit 1
fi

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment"
else
    echo "⚠️  Warning: .venv not found, using system Python"
fi

# Run the workflow
python backend/scripts/run_ocr_workflow.py "$@"
