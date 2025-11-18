<!-- b91d75c4-5800-4e36-9770-7ee0a810d4e6 081415a6-6896-4e2f-8eec-0790c4e967c4 -->
# Kế hoạch điều tra chatbot không trả lời được câu hỏi

## Bước 1: Xác nhận hành vi hiện tại

- Gửi request tới `/api/chat` với các biến thể câu hỏi (đầy đủ dấu và không dấu)
- Ghi nhận `intent`, `confidence`, `results`

## Bước 2: Kiểm tra intent classification backend

- Inspect `chatbot.py` logic (preprocess, keyword detection, fallback)
- Chạy thử trong Django shell để xem `_keyword_based_intent`/`classify_intent` trả gì

## Bước 3: Kiểm tra dữ liệu và search pipeline

- Xem `Fine` trong DB có chứa “Vượt đèn đỏ”
- Chạy `search_with_ml` hoặc `fines_list` với query tương ứng

## Bước 4: Xác định nguyên nhân và đề xuất fix

- Nếu do intent: điều chỉnh keyword/greeting logic
- Nếu do search: điều chỉnh synonyms, TF-IDF
- Tóm tắt nguyên nhân và đề xuất các bước khắc phục

### To-dos

- [ ] Nhập ≥10 dòng vào danh_ba_diem_tiep_dan.csv
- [ ] Điền ≥20 hành vi vào muc_phat_theo_hanh_vi.csv
- [ ] Tạo THU_VIEN_CANH_BAO.md với ≥15 cảnh báo chính thống
- [ ] Cập nhật CHECKLIST_DU_LIEU.md trạng thái đã xác minh/đã nhập