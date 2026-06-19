# Feature: Review tài liệu (Turnitin-style 2 cột)

> Ngày: 2026-06-16 · Bổ sung vào app AI Meeting Notes (tab thứ 2).

## Mục tiêu
Upload tài liệu (tờ trình, báo cáo, spec, slide, bảng tính...) → AI **đánh giá thẳng thắn** + chỉ rõ **chỗ nào sai, sửa thế nào** theo kiểu **Turnitin 2 cột**: trái = text tài liệu có highlight lỗi, phải = giải thích + đề xuất sửa. Bấm highlight ↔ thẻ link 2 chiều.

## Định dạng hỗ trợ
PDF · DOCX · PPTX · XLSX · TXT · MD. **Trích text** rồi review (không giữ layout gốc — quyết định 2026-06-16).

## Kiến trúc (lắp vào app cũ)
| Thành phần | File | Việc |
|---|---|---|
| Trích text | `app/extract.py` | pypdf / python-docx / python-pptx / openpyxl / txt |
| Review AI | `app/doc_review.py` | prompt reviewer thẳng thắn + schema `ReviewResult` |
| Gọi Gemini chung | `app/gemini_service.py` | `generate_json(contents, schema)` (dùng chung meeting + review) |
| API | `app/main.py` | `POST /review-doc` (auth-gated) |
| UI | `static/` | tab + 2 cột + highlight + link + nút "Mở bản HTML để in" |

## Luồng
```
upload → /review-doc → extract.extract_text() → doc_review.review_document()
  → Gemini trả {doc_type, overall, rating, findings[]}
  → trả {filename, text, review}
frontend: highlight từng finding.quote trong text (range-based, non-overlap)
  + thẻ phát hiện bên phải + link 2 chiều + xuất HTML in.
```

## Schema review
```json
{
  "doc_type": "loại tài liệu",
  "overall": "đánh giá tổng quan thẳng thắn",
  "rating": "vd 3/5 hoặc Khá - cần sửa",
  "findings": [
    { "type": "chính tả|ngữ pháp|rõ ràng|logic|thiếu sót|văn phong|nhất quán|số liệu",
      "severity": "cao|vừa|thấp",
      "quote": "trích NGUYÊN VĂN đoạn lỗi (để highlight) — \"\" nếu vấn đề chung",
      "issue": "sai/yếu gì", "suggestion": "sửa thế nào" }
  ]
}
```

## Giới hạn đã biết
- Highlight chạy bằng **khớp quote chính xác** trong text; quote AI trả không khớp → finding vẫn hiện ở cột phải nhưng báo "không định vị được".
- PDF scan ảnh (không có text) → không trích được → báo lỗi 400.
- Tài liệu rất lớn → có thể chạm giới hạn token (chưa chunk ở v1).
