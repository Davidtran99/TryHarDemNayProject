### Checklist dữ liệu cần thu thập và xác minh (Công an IT Thừa Thiên Huế)

- Liên kết chính thức (điền vào NGUON_LIEN_KET_HUE.md)
  - URL trang chính thức Công an tỉnh T.T. Huế: [đang xác minh]
  - Chuyên mục PCCC (thuộc CA tỉnh): [đang xác minh]
  - Chuyên mục ANTT/kinh doanh có điều kiện: [đang xác minh]
  - Chuyên mục Cư trú (hướng dẫn/xác nhận): [đang xác minh]
  - Danh bạ/giờ làm việc/địa điểm tiếp dân (tỉnh/huyện/xã): [đang xác minh]
  - Cổng TTHC Huế (đã có): https://tthc.hue.gov.vn/Content/Thutuc/Default.aspx

- Danh bạ điểm tiếp dân (điền vào danh_ba_diem_tiep_dan.csv)
  - Địa chỉ, điện thoại, email, giờ làm việc của:
    - Công an tỉnh (bộ phận tiếp công dân)
    - Công an TP. Huế; TX. Hương Thủy; TX. Hương Trà
    - CA các huyện: Phú Vang, Phú Lộc, Quảng Điền, Phong Điền, A Lưới, Nam Đông
    - Toạ độ/bản đồ Google Maps cho mỗi điểm (nếu có)
  - Trạng thái: [đã tạo khung ≥10 dòng, sẽ bổ sung chi tiết]

- Thủ tục hành chính ưu tiên (trích từ cổng TTHC, định dạng có cấu trúc)
  - ANTT: điều kiện kinh doanh có điều kiện, con dấu, pháo/hoa nổ, sự kiện
  - Cư trú: xác nhận thông tin cư trú; tạm trú/tạm vắng; trích lục
  - PCCC: thẩm duyệt/kiểm tra/đào tạo; điều kiện an toàn theo loại hình
  - Giao thông: mức phạt theo hành vi; hướng dẫn nộp phạt (không làm phạt nguội nếu chưa có API)
  - Trạng thái: [đang gom]

- Mức phạt theo hành vi giao thông (điền vào muc_phat_theo_hanh_vi.csv)
  - Nghị định hiện hành: [đang xác minh số hiệu mới nhất]
  - Tối thiểu 20 hành vi phổ biến: [đã tạo khung 20 hành vi]
  - Trường dữ liệu: mã hành vi, tên hành vi, điều/ khoản, nghị định, mức phạt tối thiểu/tối đa, điểm trừ GPLX (nếu có), biện pháp khắc phục, nguồn

- Cảnh báo lừa đảo/cyber
  - 15–20 bài cảnh báo từ nguồn chính thống (CAND, NCSC, cổng tỉnh/CA tỉnh) — [đã tạo thư viện 15 mục, cần bổ sung link nguồn cụ thể]
  - Tóm tắt ngắn gọn + link nguồn để trích dẫn trong chatbot

- Ghi chú vận hành
  - Mọi câu trả lời phải kèm 1–3 trích dẫn nguồn .gov.vn/.mps.gov.vn
  - Nội dung ngoài phạm vi (tố tụng, điều tra, PII) phải từ chối/định tuyến
  - Không thu thập PII không cần thiết; ẩn danh log


