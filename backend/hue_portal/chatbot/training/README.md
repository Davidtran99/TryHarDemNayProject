# Huấn luyện Intent Chatbot

## Yêu cầu
- Python 3.11
- Đã cài đặt các dependency trong `backend/requirements.txt`

## Bước thực hiện
1. Kích hoạt virtualenv và cài dependency: `pip install -r backend/requirements.txt`
2. Chạy lệnh huấn luyện mặc định:
   ```bash
   python backend/hue_portal/chatbot/training/train_intent.py
   ```
   - Model tốt nhất được lưu tại `backend/hue_portal/chatbot/training/artifacts/intent_model.joblib`
   - Metrics chi tiết nằm ở `backend/hue_portal/chatbot/training/artifacts/metrics.json`
   - Log huấn luyện append vào `backend/logs/intent/train.log`

### Tuỳ chọn
- Chỉ định dataset khác:
  ```bash
  python train_intent.py --dataset /path/to/intent_dataset.json
  ```
- Thay đổi tỉ lệ test hoặc random seed:
  ```bash
  python train_intent.py --test-size 0.25 --seed 2024
  ```

## Kiểm thử nhanh
Chạy unit test đảm bảo pipeline hoạt động:
```bash
python -m unittest backend.hue_portal.chatbot.tests.test_intent_training
```

## Cập nhật model production
Sau khi huấn luyện xong, commit `intent_model.joblib` và `metrics.json` (nếu phù hợp quy trình), sau đó redeploy backend để chatbot load model mới.
