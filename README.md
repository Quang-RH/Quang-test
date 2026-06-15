# AI Meeting Notes — Biên bản họp tự động

Web app chạy local: tải file ghi âm cuộc họp → AI (Gemini) tạo **biên bản họp** (Tóm tắt · Quyết định · Action Items · Phân công nhân sự) đúng khuôn mẫu → xem trên trang và **In/Lưu PDF**, hoặc Copy/Tải markdown.

- Cuộc họp tiếng Việt (lẫn thuật ngữ Anh) · upload file (mp3/m4a/mp4/wav…)
- Xử lý: Gemini end-to-end (đọc thẳng audio, không cần ffmpeg)
- Không lưu lịch sử/DB · file audio chỉ lưu tạm rồi xoá

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

copy .env.example .env          # rồi mở .env điền GEMINI_API_KEY
```

Lấy API key (có free tier): https://aistudio.google.com/apikey

## Chạy

```bash
uvicorn app.main:app --reload
```

Mở http://localhost:8000 → kéo-thả file audio → (tùy chọn điền Tên/Ngày/Người dự) → **Tạo biên bản**.

## Cấu hình (`.env`)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `GEMINI_API_KEY` | (bắt buộc) | Khóa Google Gemini |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model Gemini hỗ trợ audio (đổi được) |
| `MAX_FILE_MB` | `200` | Giới hạn dung lượng upload |
| `FOOTER_TEXT` | `AI Meeting Notes` | Tên ở footer biên bản |

## Test

```bash
pytest
```

## Tài liệu

- Thiết kế: [docs/2026-06-15-ai-meeting-notes-design.md](docs/2026-06-15-ai-meeting-notes-design.md)
- Kế hoạch: [docs/2026-06-15-ai-meeting-notes-plan.md](docs/2026-06-15-ai-meeting-notes-plan.md)
