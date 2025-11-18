# Tài nguyên Báo cáo

Folder này chứa tất cả các file báo cáo và tài liệu markdown được tổ chức theo **ngày tạo** và **category**.

## Cấu trúc

```
tài nguyên/báo cáo/
├── README.md (file này)
├── BAO_CAO_HE_THONG.html (báo cáo hệ thống chính)
├── 2025-11-13/
│   ├── README.md
│   ├── general/
│   │   └── *.md
│   └── ml/
│       └── *.md
└── 2025-11-14/
    ├── README.md
    ├── database/
    │   ├── README.md
    │   └── *.md (tài liệu về database)
    ├── backend/
    │   ├── README.md
    │   └── *.md (tài liệu về backend)
    └── setup/
        ├── README.md
        └── *.md (tài liệu về setup)
```

## Quy tắc tổ chức

### 1. Tổ chức theo ngày VÀ category

- Format: `tài nguyên/báo cáo/YYYY-MM-DD/category/filename.md`
- Ví dụ: `tài nguyên/báo cáo/2025-11-14/database/DATABASE_VIEWING_TOOLS.md`

### 2. Categories phổ biến

- **`database`** / `db` - Tài liệu về database, PostgreSQL, MySQL, etc.
- **`backend`** / `be` - Tài liệu về backend, API, server, Django, etc.
- **`frontend`** / `ui` / `fe` - Tài liệu về frontend, UI, React, components, etc.
- **`devops`** / `ops` - Tài liệu về DevOps, deployment, CI/CD, Docker, etc.
- **`ml`** / `ai` - Tài liệu về Machine Learning, AI, models, etc.
- **`plan`** / `planning` - Kế hoạch, roadmap, planning documents
- **`setup`** / `config` - Setup, configuration, installation guides
- **`general`** / `other` - Tài liệu chung, không thuộc category cụ thể

### 3. Tự động detect category

Script tự động detect category từ:
- **Tên file** (keywords: database, postgresql, backend, frontend, etc.)
- **Nội dung file** (tìm keywords trong 100 dòng đầu)
- **Metadata trong file** (nếu có `Category: xxx`)

### 4. Linh động trong việc tạo folder

- Tự động tạo folder `YYYY-MM-DD/category/` nếu chưa có
- Tự động tạo README.md trong folder category
- Có thể tạo sub-category nếu cần: `YYYY-MM-DD/database/postgresql/`

## Script tự động

Chạy script để tự động tổ chức các file markdown:

```bash
# Preview (không di chuyển thực sự)
bash backend/scripts/organize_markdowns.sh --dry-run

# Thực sự di chuyển
bash backend/scripts/organize_markdowns.sh

# Với backup
bash backend/scripts/organize_markdowns.sh --backup
```

### Tính năng script:

- ✅ Xác định ngày tạo (git, metadata, file system)
- ✅ Tự động detect category từ tên file và nội dung
- ✅ Tự động tạo folder structure
- ✅ Tự động tạo README.md trong folder category
- ✅ Kiểm tra duplicate và validation
- ✅ Dry-run mode để preview
- ✅ Backup mode (optional)

## Metadata trong file (Optional)

Có thể thêm metadata vào đầu file markdown để script xác định chính xác hơn:

```markdown
<!--
Created: 2025-11-14
Category: database
Tags: postgresql, setup, tools
-->
```

## Ngoại lệ

Các file markdown sau KHÔNG cần di chuyển:
- `backend/ops/*.md` - Operational documentation
- `backend/hue_portal/chatbot/training/README.md` - Technical docs
- `node_modules/**/*.md` - Dependencies
- `.cursor/**/*.md` - Cursor config files
- `*.plan.md` trong `.cursor/plans/` - Plan files

## Lợi ích

- ✅ Dễ dàng tìm file theo category (database, backend, frontend)
- ✅ Tổ chức rõ ràng theo ngày và chủ đề
- ✅ Tự động hóa việc tổ chức file
- ✅ Linh động trong việc tạo folder structure

## Rule chi tiết

Xem file `.cursor/rules/MARKDOWN_ORGANIZATION.md` để biết chi tiết về rule và logic.
