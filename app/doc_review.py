"""Review tài liệu bằng Gemini: text/PDF -> nhận xét có cấu trúc (scorecard + findings 3 lớp)."""
from pydantic import BaseModel

from app import gemini_service


class Finding(BaseModel):
    type: str        # Chính tả | Ngữ pháp | Thể thức/format | Văn phong | Logic | Nội dung
    severity: str    # cao | vừa | thấp
    quote: str       # PINPOINT đúng từ/cụm liên quan ("" nếu là vấn đề nội dung/cấu trúc toàn cục)
    why: str         # vì sao cần sửa: vi phạm nguyên tắc gì, gây hại gì
    suggestion: str  # sửa thế nào: cụ thể, kèm ví dụ


class DimScore(BaseModel):
    dimension: str   # nhóm tiêu chí
    score: str       # Đạt | Một phần | Chưa
    note: str


class ReviewResult(BaseModel):
    doc_type: str
    author_unit: str     # đơn vị/người soạn, nơi phát hành ("" nếu không rõ)
    related_units: str   # các phòng ban liên quan ("" nếu không rõ)
    summary: str         # tổng quan nội dung: tài liệu nói về vấn đề gì (khách quan)
    overall: str         # đánh giá thẳng thắn (chất lượng)
    rating: str
    scorecard: list[DimScore]
    findings: list[Finding]


class ReviewWithText(BaseModel):
    document_text: str  # text Gemini đọc/OCR được (đường PDF scan)
    doc_type: str
    author_unit: str
    related_units: str
    summary: str
    overall: str
    rating: str
    scorecard: list[DimScore]
    findings: list[Finding]


INTRO = (
    "Bạn là chuyên gia review tài liệu (tờ trình, báo cáo, kế hoạch, công văn, đặc tả yêu cầu...). "
    "Đọc kỹ tài liệu và trả nhận xét theo đúng JSON schema."
)

REVIEW_RULES = """QUY TẮC REVIEW (giữ nguyên thuật ngữ tiếng Anh, không bịa, chỉ trả JSON đúng schema):

A. NHẬN DIỆN LOẠI (doc_type): xác định loại tài liệu. Nếu là "Tờ trình", "Kế hoạch", "Công văn" hoặc
   "Báo cáo" → áp THÊM rubric đào sâu nội dung ở mục D. Loại khác → chỉ soi tầng chung (B, C).

A2. TỔNG QUAN (giúp người đọc nắm bức tranh chung TRƯỚC khi vào chi tiết — KHÁCH QUAN, không phải đánh giá):
   - author_unit: đơn vị/người soạn hoặc nơi phát hành tài liệu (vd "Phòng QTNT Digital"); "" nếu không xác định.
   - related_units: các phòng ban/bộ phận liên quan được nhắc tới (vd "BDA, SM, CĐS"); "" nếu không có.
   - summary: 2-4 câu mô tả TỔNG THỂ tài liệu nói về vấn đề/nội dung gì, mục đích chính. Khách quan, súc tích.
   (Lưu ý: "summary" là mô tả nội dung; "overall" ở mục G mới là lời ĐÁNH GIÁ thẳng thắn — đừng lẫn lộn.)

B. LỖI BỀ MẶT — chỉ bắt lỗi THẬT, pinpoint đúng chỗ (quote = đúng từ/cụm sai, KHÔNG lấy cả câu dài):
   - "Chính tả": sai dấu, sai từ (vd "giám đôc" → "giám đốc").
   - "Ngữ pháp": sai cấu trúc câu, thiếu/thừa thành phần, sai dùng từ.
   - "Thể thức/format": trình bày KHÔNG ĐỒNG ĐỀU (đánh số, heading, bullet, viết hoa, cách dùng thuật ngữ
     không nhất quán).
   - "Văn phong": câu lủng củng, tối nghĩa, KHÔNG MẠCH LẠC, không đúng văn phong trang trọng.
   - TUYỆT ĐỐI không bắt bẻ nội dung trong ngoặc đơn/ngoặc kép nếu nó không thật sự sai. Không nitpick vụn vặt.

C. CHẤT LƯỢNG NỘI DUNG CHUNG (mọi tài liệu, type="Logic" hoặc "Nội dung"): tính logic & mạch lạc,
   các phần liên kết không mâu thuẫn, thông tin đầy đủ không bỏ ngỏ (con số/thời gian/phạm vi).

D. RUBRIC ĐÀO SÂU THEO LOẠI (type="Nội dung", quote thường = "" vì là vấn đề toàn cục):
   • Tờ trình/đề xuất phê duyệt: căn cứ rõ; LÀM RÕ NHU CẦU & vấn đề cần giải quyết (thuyết phục);
     mục tiêu cụ thể ĐO LƯỜNG ĐƯỢC (KPI); nội dung đề xuất khả thi, đúng trọng tâm;
     PHÂN CÔNG bộ phận tham gia rõ; NGUỒN LỰC (chi phí/dự toán, thời gian, nhân sự) có số cụ thể;
     rủi ro & phương án dự phòng; kết quả mong đợi; thể thức hành chính (số hiệu, nơi nhận, trích yếu, ký).
   • Kế hoạch: mục tiêu rõ & đo được; mốc thời gian; phân công; nguồn lực; rủi ro; tiêu chí hoàn thành.
   • Công văn: mục đích rõ; đúng thể thức hành chính; nội dung súc tích; yêu cầu/đề nghị rõ ràng.
   • Báo cáo: mục đích; số liệu/dẫn chứng đầy đủ; phân tích khách quan; kết luận & khuyến nghị rõ.

E. MỖI FINDING đủ 3 lớp:
   - quote: pinpoint chỗ liên quan; để "" nếu là vấn đề nội dung/cấu trúc toàn cục.
   - why: VÌ SAO cần sửa — vi phạm nguyên tắc gì, gây hại gì (vd gây hiểu nhầm, sai thể thức, thiếu cơ sở phê duyệt).
   - suggestion: SỬA THẾ NÀO — cụ thể, kèm ví dụ câu/nội dung sửa nếu được.
   - severity: "cao" = ảnh hưởng tính hợp lệ/khả năng phê duyệt; "vừa" = ảnh hưởng chất lượng/rõ ràng;
     "thấp" = lỗi nhỏ bề mặt.

F. SCORECARD: chấm từng nhóm tiêu chí, score ∈ {"Đạt","Một phần","Chưa"} + note ngắn. Các nhóm:
   "Hình thức ngôn ngữ", "Thể thức & format", "Văn phong & mạch lạc", "Logic & lập luận",
   "Đầy đủ nội dung", "Đặc thù loại tài liệu".

G. overall: nhận xét tổng quan THẲNG THẮN, trung thực, không nể nang. rating: ngắn (vd "3/5" hoặc "Khá - cần sửa")."""

REVIEW_PROMPT = INTRO + "\n\n" + REVIEW_RULES

PDF_NATIVE_PROMPT = (
    INTRO
    + "\nTài liệu đính kèm là file PDF (CÓ THỂ là bản scan ảnh, không có lớp text). "
    "Hãy ĐỌC toàn bộ nội dung (OCR nếu là ảnh), đưa vào document_text (giữ đúng thứ tự đọc, "
    "xuống dòng hợp lý), rồi review theo các quy tắc dưới. quote trong findings phải trích NGUYÊN VĂN "
    "từ chính document_text bạn vừa tạo.\n\n"
    + REVIEW_RULES
)


def review_document(text: str) -> dict:
    contents = [REVIEW_PROMPT, "\n\n=== TÀI LIỆU ===\n" + text]
    return gemini_service.generate_json(contents, ReviewResult)


def review_pdf_native(file_path: str):
    """Cho PDF scan: Gemini OCR + review. Trả (text, review_dict)."""
    result = gemini_service.generate_json_with_file(
        file_path, "application/pdf", PDF_NATIVE_PROMPT, ReviewWithText
    )
    text = result.get("document_text", "")
    keys = ("doc_type", "author_unit", "related_units", "summary",
            "overall", "rating", "scorecard", "findings")
    review = {k: result.get(k) for k in keys}
    return text, review
