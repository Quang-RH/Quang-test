# Kế hoạch triển khai: AI Meeting Notes

> Ngày: 2026-06-15 · Dựa trên [design spec](2026-06-15-ai-meeting-notes-design.md).
> Mỗi phase nhỏ, làm tuần tự, có tiêu chí "Done" kiểm tra được trước khi sang phase sau.

---

## Phase 0 — Scaffold project

**Việc:**
- Tạo cây thư mục (`app/`, `static/`, `tests/`).
- `requirements.txt`: `fastapi`, `uvicorn[standard]`, `python-multipart`, `google-genai`, `python-dotenv`, `pytest`.
- `.env.example`: `GEMINI_API_KEY=`, `GEMINI_MODEL=gemini-2.5-flash` *(xác nhận/đổi theo model audio bạn có quyền)*, `MAX_FILE_MB=200`, `FOOTER_TEXT=AI Meeting Notes`.
- `app/config.py`: đọc `.env`, fail fast nếu thiếu `GEMINI_API_KEY`.
- `README.md`: hướng dẫn chạy.

**Done khi:** `pip install -r requirements.txt` chạy được · `python -c "from app import config"` không lỗi (với `.env` đã điền key giả).

## Phase 1 — Gemini service (lõi AI)

**Việc — `app/gemini_service.py`:**
- Hàm `summarize_meeting(file_path, mime_type) -> dict`.
- Upload file lên Gemini Files API → poll tới trạng thái `ACTIVE` (có timeout).
- `generateContent(audio + prompt + responseSchema)` với JSON mode.
- Prompt tiếng Việt: đóng vai thư ký; giữ nguyên thuật ngữ Anh; trả đúng JSON schema; trường không rõ để `null`.
- Parse JSON; **JSON hỏng → retry 1 lần**; vẫn hỏng → raise lỗi rõ ràng.

**Done khi:** chạy thử với 1 file ghi âm ngắn thật → trả về dict đúng schema (manual) · unit test với client **mock** pass.

## Phase 2 — Render/format

**Việc — `app/render.py`:**
- `make_meeting_id()` → `MEETING-` + số.
- `merge_metadata(ai_result, user_input)`: ô người dùng nhập **ghi đè** AI; cả hai trống → `"Chưa xác nhận"`.
- `to_markdown(meeting) -> str`: dựng markdown đúng cấu trúc biên bản (header + 4 mục + footer).

**Done khi:** `tests/test_render.py` pass — kiểm: fallback "Chưa xác nhận", metadata ghi đè, markdown có đủ 4 mục + bảng.

## Phase 3 — API

**Việc — `app/main.py`:**
- `GET /` → trả `static/index.html`.
- `POST /process`: nhận multipart `file` + các field tùy chọn (`title`, `meeting_date`, `participants`).
  - Validate loại file (audio/video) + dung lượng ≤ `MAX_FILE_MB` → sai thì 400.
  - Lưu file tạm → gọi `gemini_service` → `render` → trả `{ "meeting": {...}, "markdown": "..." }`.
  - Lỗi Gemini/timeout/JSON hỏng → 502 + message.
  - Xoá file tạm (finally).
- Mount `static/`.

**Done khi:** `tests/test_validate.py` pass (Gemini mock) · gọi thử `POST /process` bằng file thật trả JSON đúng.

## Phase 4 — Frontend

**Việc:**
- `static/index.html`: vùng kéo-thả + input file; ô tùy chọn Tên cuộc họp / Ngày họp / Người dự; nút "Tạo biên bản"; khung hiển thị kết quả + nút [In/Lưu PDF] [Copy .md] [Tải .md]; trạng thái loading/lỗi.
- `static/styles.css`: style tài liệu giống mẫu (tiêu đề xanh, bảng viền) + `@media print` (ẩn form/nút, khổ A4).
- `static/app.js`: submit `FormData` → `/process`; render JSON → HTML (header, mục 1 đoạn, mục 2 nhóm+bold+đoạn, mục 3 bảng 4 cột, mục 4 bảng 3 cột, footer); `window.print()`; copy & tải `.md`.

**Done khi:** chạy `uvicorn` → mở browser → upload 1 file thật → ra biên bản đúng khuôn · "In/Lưu PDF" cho ra PDF nhìn giống mẫu MEETING-20177.

## Phase 5 — Polish

**Việc:** soát message lỗi trên UI; README hoàn chỉnh (cài đặt + lấy `GEMINI_API_KEY`); chạy đối chiếu cuối với file mẫu; chỉnh prompt nếu output lệch khuôn.

**Done khi:** end-to-end mượt với file họp thật, output bám sát mẫu, README đủ để chạy lại từ đầu.

---

## Thứ tự & phụ thuộc

```
Phase 0 (scaffold)
  └─ Phase 1 (gemini)  ─┐
  └─ Phase 2 (render)  ─┼─ Phase 3 (API) ── Phase 4 (frontend) ── Phase 5 (polish)
```
Phase 1 và 2 độc lập, có thể làm song song; cả hai xong mới ráp Phase 3.

## Rủi ro / điểm cần xác nhận khi build

- **`GEMINI_MODEL`**: xác nhận model audio cụ thể bạn có quyền (ID có thể đổi) — để trong `.env`, dễ bump.
- **Chi phí**: Gemini Flash đọc audio rẻ + có free tier; 1 cuộc họp ~vài cent hoặc thấp hơn.
- **Output bám khuôn**: nếu Gemini gom nhóm quyết định chưa giống mẫu → tinh chỉnh prompt ở Phase 5.
