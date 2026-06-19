"""Review tài liệu bằng Gemini: text -> nhận xét có cấu trúc (overall + findings)."""
from pydantic import BaseModel

from app import gemini_service


class Finding(BaseModel):
    type: str        # chính tả | ngữ pháp | rõ ràng | logic | thiếu sót | văn phong | nhất quán | số liệu
    severity: str    # cao | vừa | thấp
    quote: str       # trích NGUYÊN VĂN đoạn lỗi ("" nếu là vấn đề chung)
    issue: str       # sai/yếu chỗ nào
    suggestion: str  # đề xuất sửa cụ thể


class ReviewResult(BaseModel):
    doc_type: str    # AI nhận diện loại tài liệu
    overall: str     # đánh giá tổng quan thẳng thắn
    rating: str      # vd "3/5" hoặc "Khá - cần sửa"
    findings: list[Finding]


REVIEW_PROMPT = """Bạn là chuyên gia review tài liệu (tờ trình, báo cáo, đặc tả yêu cầu, \
văn bản hành chính, slide, bảng tính...). Hãy đọc kỹ TÀI LIỆU bên dưới và đưa ra bản nhận xét \
theo đúng JSON schema. Quy tắc:

- Viết bằng tiếng Việt, GIỮ NGUYÊN thuật ngữ tiếng Anh.
- doc_type: nhận diện loại tài liệu.
- overall: lời đánh giá tổng quan THẲNG THẮN, trung thực, KHÔNG nể nang — nêu rõ tài liệu mạnh/yếu
  ở đâu, đã dùng được chưa, ấn tượng chung.
- rating: xếp loại ngắn gọn (vd "3/5" hoặc "Khá - cần sửa").
- findings: liệt kê CỤ THỂ từng vấn đề phát hiện. Mỗi finding:
   - type: một trong "chính tả", "ngữ pháp", "rõ ràng", "logic", "thiếu sót", "văn phong", "nhất quán", "số liệu".
   - severity: "cao" | "vừa" | "thấp".
   - quote: TRÍCH NGUYÊN VĂN đoạn text bị lỗi, COPY CHÍNH XÁC TỪNG KÝ TỰ y như trong tài liệu
     (để hệ thống tô màu định vị được). Nếu là vấn đề chung không gắn vào 1 đoạn cụ thể, để quote = "".
   - issue: sai hoặc yếu ở chỗ nào.
   - suggestion: đề xuất sửa CỤ THỂ (vd lỗi chính tả thì ghi rõ từ đúng; thiếu sót thì nêu cần bổ sung gì).
- Tập trung vào vấn đề thực chất và SỬA ĐƯỢC. Không bịa lỗi không có.
Chỉ trả về JSON đúng schema, không kèm giải thích."""


def review_document(text: str) -> dict:
    contents = [REVIEW_PROMPT, "\n\n=== TÀI LIỆU ===\n" + text]
    return gemini_service.generate_json(contents, ReviewResult)
