#!/bin/bash
# Script tự động tổ chức các file markdown theo ngày tạo và category
# Chạy: bash backend/scripts/organize_markdowns.sh [--dry-run] [--backup]

set -e

# Parse arguments
DRY_RUN=false
BACKUP=false
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --backup)
            BACKUP=true
            shift
            ;;
        *)
            ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORTS_DIR="${PROJECT_ROOT}/tài nguyên/báo cáo"
DOCS_DIR="${PROJECT_ROOT}/backend/docs"

echo "📁 Tổ chức file markdown theo ngày và category..."
if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY-RUN MODE: Chỉ preview, không di chuyển file"
fi
echo ""

# Hàm xác định ngày tạo file
get_file_creation_date() {
    local file="$1"
    local git_date=""
    local birth_date=""
    local mod_date=""
    local meta_date=""
    local final_date=""
    
    # Git history
    if command -v git &> /dev/null && [ -d "${PROJECT_ROOT}/.git" ]; then
        git_date=$(cd "$PROJECT_ROOT" && git log --diff-filter=A --format="%ai" -- "$file" 2>/dev/null | tail -1 | cut -d' ' -f1)
        if [ -z "$git_date" ] || [[ ! "$git_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
            git_date=""
        fi
    fi
    
    # File birth time
    if [[ "$OSTYPE" == "darwin"* ]]; then
        birth_date=$(stat -f "%SB" -t "%Y-%m-%d" "$file" 2>/dev/null || stat -f "%Sm" -t "%Y-%m-%d" -B "$file" 2>/dev/null || echo "")
        if [ -z "$birth_date" ]; then
            birth_date=$(stat -f "%Sm" -t "%Y-%m-%d" "$file" 2>/dev/null || echo "")
        fi
    else
        birth_date=$(stat -c "%y" "$file" 2>/dev/null | cut -d' ' -f1 || echo "")
    fi
    
    # File modified time
    if [[ "$OSTYPE" == "darwin"* ]]; then
        mod_date=$(stat -f "%Sm" -t "%Y-%m-%d" "$file" 2>/dev/null || echo "")
    else
        mod_date=$(stat -c "%y" "$file" 2>/dev/null | cut -d' ' -f1 || echo "")
    fi
    
    # Metadata trong file
    if [ -f "$file" ]; then
        meta_date=$(grep -iE "(created|date|ngày):\s*[0-9]{4}-[0-9]{2}-[0-9]{2}" "$file" 2>/dev/null | head -1 | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" | head -1 || echo "")
    fi
    
    # Sử dụng ngày đầu tiên tìm được
    if [ -n "$git_date" ]; then
        final_date="$git_date"
    elif [ -n "$birth_date" ]; then
        final_date="$birth_date"
    elif [ -n "$mod_date" ]; then
        final_date="$mod_date"
    elif [ -n "$meta_date" ]; then
        final_date="$meta_date"
    else
        final_date=$(date +"%Y-%m-%d")
    fi
    
    # Validate format
    if [[ ! "$final_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        final_date=$(date +"%Y-%m-%d")
    fi
    
    echo "$final_date"
}

# Hàm detect category từ tên file và nội dung
detect_category() {
    local file="$1"
    local filename=$(basename "$file" | tr '[:upper:]' '[:lower:]')
    local category=""
    
    # Ưu tiên 1: Metadata trong file
    if [ -f "$file" ]; then
        meta_category=$(grep -iE "category:\s*[a-z]+" "$file" 2>/dev/null | head -1 | grep -oE "category:\s*([a-z_]+)" | cut -d: -f2 | tr -d ' ' || echo "")
        if [ -n "$meta_category" ]; then
            echo "$meta_category"
            return
        fi
    fi
    
    # Ưu tiên 2: Tên file
    declare -A category_keywords
    category_keywords["database"]="database|postgresql|mysql|mongodb|redis|db_|_db|sql"
    category_keywords["backend"]="backend|api|server|django|flask|fastapi|be_|_be|endpoint"
    category_keywords["frontend"]="frontend|ui|react|vue|angular|component|fe_|_fe|interface"
    category_keywords["devops"]="devops|docker|kubernetes|ci/cd|deploy|jenkins|terraform"
    category_keywords["ml"]="ml|ai|model|training|neural|tensorflow|pytorch|embedding"
    category_keywords["plan"]="plan|roadmap|planning|strategy|milestone"
    category_keywords["setup"]="setup|config|install|installation|guide|tutorial"
    
    local max_matches=0
    for cat in "${!category_keywords[@]}"; do
        matches=$(echo "$filename" | grep -oiE "${category_keywords[$cat]}" | wc -l | tr -d ' ')
        if [ "$matches" -gt "$max_matches" ]; then
            max_matches=$matches
            category="$cat"
        fi
    done
    
    # Ưu tiên 3: Nội dung file (100 dòng đầu)
    if [ -z "$category" ] && [ -f "$file" ]; then
        local content=$(head -100 "$file" | tr '[:upper:]' '[:lower:]')
        max_matches=0
        for cat in "${!category_keywords[@]}"; do
            matches=$(echo "$content" | grep -oiE "${category_keywords[$cat]}" | wc -l | tr -d ' ')
            if [ "$matches" -gt "$max_matches" ]; then
                max_matches=$matches
                category="$cat"
            fi
        done
    fi
    
    # Fallback
    if [ -z "$category" ]; then
        category="general"
    fi
    
    echo "$category"
}

# Hàm tạo folder và README nếu chưa có
ensure_category_folder() {
    local date_folder="$1"
    local category="$2"
    local category_folder="${date_folder}/${category}"
    
    if [ ! -d "$category_folder" ]; then
        if [ "$DRY_RUN" = false ]; then
            mkdir -p "$category_folder"
            echo "✅ Đã tạo folder: $category_folder"
            
            # Tạo README.md trong folder category
            cat > "${category_folder}/README.md" << EOF
# Tài liệu ${category} - $(basename "$date_folder")

Folder này chứa các file markdown về **${category}** được tạo trong ngày $(basename "$date_folder").

## Danh sách file

$(find "$category_folder" -maxdepth 1 -name "*.md" ! -name README.md -type f | sed 's|.*/||' | sort | sed 's/^/- /')

## Category
${category}

## Ngày tạo
$(basename "$date_folder")
EOF
        else
            echo "🔍 [DRY-RUN] Sẽ tạo folder: $category_folder"
        fi
    fi
}

# Hàm di chuyển file markdown
move_markdown() {
    local source_file="$1"
    local target_dir="$2"
    local filename=$(basename "$source_file")
    local target_file="${target_dir}/${filename}"
    
    if [ -f "$target_file" ]; then
        if cmp -s "$source_file" "$target_file" 2>/dev/null; then
            echo "⚠️  File trùng nội dung: $target_file (xóa file gốc)"
            if [ "$DRY_RUN" = false ]; then
                rm "$source_file"
            fi
            return 1
        else
            echo "⚠️  File đã tồn tại nhưng khác nội dung: $target_file"
            return 1
        fi
    fi
    
    if [ "$BACKUP" = true ] && [ "$DRY_RUN" = false ]; then
        backup_dir="${PROJECT_ROOT}/.backup/markdowns/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        cp "$source_file" "${backup_dir}/${filename}"
    fi
    
    if [ "$DRY_RUN" = false ]; then
        mv "$source_file" "$target_file"
        echo "✅ Đã di chuyển: $filename → $target_dir"
    else
        echo "🔍 [DRY-RUN] Sẽ di chuyển: $filename → $target_dir"
    fi
    return 0
}

# Xử lý các file trong backend/docs
if [ -d "$DOCS_DIR" ]; then
    echo "🔍 Tìm file markdown trong: $DOCS_DIR"
    
    find "$DOCS_DIR" -maxdepth 1 -name "*.md" -type f | while read -r file; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo ""
            echo "📄 Xử lý: $filename"
            
            # Xác định ngày tạo
            date_created=$(get_file_creation_date "$file")
            echo "  📅 Ngày: $date_created"
            
            # Detect category
            category=$(detect_category "$file")
            echo "  📂 Category: $category"
            
            date_folder="${REPORTS_DIR}/${date_created}"
            ensure_category_folder "$date_folder" "$category"
            
            # Di chuyển file
            move_markdown "$file" "${date_folder}/${category}"
        fi
    done
fi

# Tìm các file markdown lộn xộn khác
echo ""
echo "🔍 Tìm file markdown lộn xộn khác..."

EXCLUDE_DIRS=(
    "node_modules"
    "ops"
    "chatbot/training"
    ".git"
    ".venv"
    "__pycache__"
    ".cursor"
    "tài nguyên/báo cáo"
    ".backup"
)

find "$PROJECT_ROOT" -name "*.md" -type f | while read -r file; do
    skip=false
    for exclude in "${EXCLUDE_DIRS[@]}"; do
        if [[ "$file" == *"$exclude"* ]]; then
            skip=true
            break
        fi
    done
    
    if [[ "$file" == *"tài nguyên/báo cáo"* ]]; then
        skip=true
    fi
    
    if [ "$skip" = true ]; then
        continue
    fi
    
    filename=$(basename "$file")
    echo ""
    echo "📄 Xử lý: $filename"
    
    # Xác định ngày tạo
    date_created=$(get_file_creation_date "$file")
    echo "  📅 Ngày: $date_created"
    
    # Detect category
    category=$(detect_category "$file")
    echo "  📂 Category: $category"
    
    date_folder="${REPORTS_DIR}/${date_created}"
    ensure_category_folder "$date_folder" "$category"
    
    # Di chuyển file
    move_markdown "$file" "${date_folder}/${category}"
done

echo ""
echo "✅ Hoàn tất tổ chức file markdown!"
echo ""
echo "📊 Thống kê:"
for date_folder in "${REPORTS_DIR}"/20*; do
    if [ -d "$date_folder" ]; then
        date_name=$(basename "$date_folder")
        echo "  📁 $date_name:"
        for category_folder in "${date_folder}"/*; do
            if [ -d "$category_folder" ]; then
                category_name=$(basename "$category_folder")
                count=$(find "$category_folder" -maxdepth 1 -name "*.md" ! -name README.md -type f | wc -l | tr -d ' ')
                if [ "$count" -gt 0 ]; then
                    echo "    └─ $category_name: $count file(s)"
                fi
            fi
        done
    fi
done

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "💡 Chạy lại không có --dry-run để thực sự di chuyển file"
fi
