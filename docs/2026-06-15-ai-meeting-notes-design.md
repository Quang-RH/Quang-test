# Thiết kế: AI Meeting Notes — "Biên bản họp tự động"

> Ngày: 2026-06-15 · Tác giả: Quang (PE/BA) · Trạng thái: Approved (chờ implementation plan)
> Side-project độc lập · ngoài repo O2O · git local-only (không push).

---

## 1. Mục tiêu

Một **web app chạy local**: người dùng kéo-thả 1 file ghi âm cuộc họp → AI sinh ra **biên bản họp** có định dạng giống tài liệu mẫu `MEETING-20177` (Hasabot), gồm Tóm tắt + Quyết định + Action Items + Phân công nhân sự → xem trên trang và **In/Lưu PDF** đúng look mẫu, kèm Copy/Tải markdown.

**Bối cảnh đầu vào:**
- Cuộc họp tiếng Việt, lẫn thuật ngữ tiếng Anh (deploy, sprint, API, repo...).
- File ghi âm có sẵn (mp3/m4a/mp4/...), thường dài 30 phút – 2 tiếng.

## 2. Phi mục tiêu (YAGNI — không làm ở v1)

- ❌ Lưu lịch sử / database các cuộc họp.
- ❌ Phân vai người nói (speaker diarization).
- ❌ Thu âm trực tiếp trong app.
- ❌ Đăng nhập / đa người dùng.
- ❌ Sinh PDF/.docx phía server (đã chọn In/Lưu PDF qua trình duyệt).

## 3. Kiến trúc & stack

- **Backend**: Python **FastAPI** (chạy bằng `uvicorn`, mở `http://localhost:8000`).
- **Frontend**: **HTML/CSS thuần** + vanilla JS. CSS có `@media print` để bản in/PDF giống mẫu. Không dùng CDN/framework để kiểm soát hoàn toàn output in.
- **AI pipeline**: **Gemini end-to-end** — đọc thẳng audio → trả JSON biên bản có cấu trúc (1 lượt gọi/ file). Dùng JSON mode (`responseSchema`) cho ổn định.
- **Không DB.** File audio chỉ lưu tạm trong lúc xử lý rồi xoá.

### Các thành phần tách bạch

| Mảnh | File | Nhiệm vụ | Phụ thuộc |
|---|---|---|---|
| UI | `static/index.html`, `styles.css`, `app.js` | Form upload + ô metadata tùy chọn; render biên bản; nút In/Lưu PDF, Copy .md, Tải .md | gọi `POST /process` |
| API | `app/main.py` | `GET /` trả trang · `POST /process` nhận file + metadata → gọi service → trả JSON | gemini_service, render, config |
| Gemini service | `app/gemini_service.py` | upload file lên Gemini Files API → chờ ACTIVE → `generateContent(audio + prompt + schema)` → parse JSON | config |
| Render/format | `app/render.py` | Áp fallback "Chưa xác nhận", gộp metadata người dùng, sinh `meeting_id`, build chuỗi markdown | — |
| Config | `app/config.py` + `.env` | `GEMINI_API_KEY`, `GEMINI_MODEL`, `MAX_FILE_MB`, `FOOTER_TEXT` | — |

## 4. Luồng dữ liệu

```
Trình duyệt (kéo-thả audio + tùy chọn: Tên cuộc họp · Ngày họp · Người dự)
   → POST /process (multipart: file + metadata)
   → FastAPI lưu file tạm
   → gemini_service: upload → poll tới ACTIVE → generateContent(audio + prompt + responseSchema)
   → JSON biên bản
   → render: gộp metadata người dùng (ưu tiên hơn AI), sinh MEETING-xxxxx, áp fallback "Chưa xác nhận", build markdown
   → trả {biên bản JSON, markdown}
   → xoá file tạm
   → UI render tài liệu theo khuôn mẫu + [In/Lưu PDF] [Copy .md] [Tải .md]
```

Chỉ **1 lượt gọi Gemini**/file → rẻ & nhanh; Gemini xử lý audio dài native nên không cần ffmpeg/cắt khúc.

## 5. Cấu trúc đầu ra (chỉ tập trung nội dung — không tên/vai trò người)

- **Header**: `BIÊN BẢN HỌP: MEETING SUMMARY` · **Mã cuộc họp** `MEETING-xxxxx` · **Ngày họp**
- **1. Tóm tắt cuộc họp (Summary)** — 1 đoạn văn cô đọng.
- **2. Các quyết định quan trọng (Key Decisions)** — gom theo **nhóm chủ đề** (`category`); mỗi quyết định = **tiêu đề in đậm + 1 đoạn diễn giải**.
- **3. Danh sách công việc (Action Items)** — **bảng 3 cột**: Tên công việc · Trạng thái/Deadline · Ghi chú từ cuộc họp.
- **Footer**: "Biên bản này được tổng hợp tự động bởi {FOOTER_TEXT}".

**Đã bỏ so với mẫu gốc MEETING-20177 (yêu cầu Owner 2026-06-16):** mục "Phân công nhân sự", cột "Người phụ trách", trường "Đối tượng/người dự". AI **không nêu tên, không gán vai trò** cho bất kỳ ai — chỉ tập trung nội dung record.

**Quy ước thiếu dữ liệu:** ngày họp không có trong audio và người dùng không nhập → hiển thị **"Chưa xác nhận"**.

## 6. JSON schema Gemini trả về

```json
{
  "title": "tiêu đề ngắn cuộc họp",
  "meeting_date": "string (\"\" nếu không có)",
  "summary": "1 đoạn tóm tắt",
  "key_decisions": [
    {
      "category": "nhóm chủ đề",
      "items": [ { "title": "tiêu đề quyết định", "detail": "đoạn diễn giải" } ]
    }
  ],
  "action_items": [
    { "task": "tên công việc", "status_deadline": "string (\"\" nếu không có)", "note": "ghi chú từ cuộc họp" }
  ]
}
```

**Prompt Gemini (tiếng Việt):** đóng vai thư ký biên bản; giữ nguyên thuật ngữ Anh; **chỉ tập trung nội dung, KHÔNG nêu tên / gán vai trò / người phụ trách cho ai**; chỉ trả JSON đúng schema; trường không xác định để `""` (không bịa).

**Hợp nhất metadata (trong `render.py`):** giá trị người dùng nhập (title, meeting_date) **ghi đè** giá trị AI trích; cả hai trống → `"Chưa xác nhận"`. `meeting_id` luôn sinh phía server.

## 7. Cấu trúc thư mục

```
ai-meeting-notes/
├── app/
│   ├── main.py            # FastAPI: GET / , POST /process
│   ├── gemini_service.py  # upload → poll ACTIVE → generateContent → parse JSON
│   ├── render.py          # fallback "Chưa xác nhận" + gộp metadata + sinh meeting_id + build markdown
│   └── config.py          # đọc .env
├── static/
│   ├── index.html         # form upload + khung biên bản
│   ├── styles.css         # style tài liệu + @media print (giống mẫu)
│   └── app.js             # gọi API, render JSON → HTML, in/copy/tải
├── tests/
│   ├── test_render.py     # build markdown + fallback + gộp metadata
│   └── test_validate.py   # validate loại file / dung lượng (mock Gemini)
├── docs/
│   └── 2026-06-15-ai-meeting-notes-design.md
├── .env.example           # GEMINI_API_KEY, GEMINI_MODEL, MAX_FILE_MB, FOOTER_TEXT
├── requirements.txt
└── README.md
```

## 8. Xử lý lỗi

| Tình huống | Hành vi |
|---|---|
| File sai định dạng / quá `MAX_FILE_MB` | HTTP 400 + thông báo rõ trên UI |
| Thiếu `GEMINI_API_KEY` lúc khởi động | Fail fast khi start app, log rõ |
| Gemini lỗi / timeout | HTTP 502 + message trên UI (không treo) |
| Gemini trả JSON hỏng | Retry 1 lần; vẫn hỏng → 502 + báo lỗi |
| File audio quá lâu chưa ACTIVE | Timeout poll → 502 |

## 9. Cấu hình (`.env`)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `GEMINI_API_KEY` | (bắt buộc) | Khóa API Google Gemini |
| `GEMINI_MODEL` | model audio mới nhất (chỉnh được) | Tên model Gemini có hỗ trợ audio |
| `MAX_FILE_MB` | 200 | Giới hạn dung lượng file upload |
| `FOOTER_TEXT` | "AI Meeting Notes" | Tên hiển thị ở footer biên bản |

## 10. Test (đúng tầm side-project)

- `pytest`:
  - `test_render.py`: build markdown đúng cấu trúc, áp fallback "Chưa xác nhận", metadata người dùng ghi đè AI.
  - `test_validate.py`: từ chối file sai loại / quá lớn (Gemini được **mock**).
- Manual: chạy thật với 1 file ghi âm mẫu của người dùng, đối chiếu output với khuôn mẫu MEETING-20177.

## 11. Vận hành

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # điền GEMINI_API_KEY
uvicorn app.main:app --reload
# mở http://localhost:8000
```
