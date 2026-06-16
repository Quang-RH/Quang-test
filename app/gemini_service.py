"""Gemini end-to-end: audio -> JSON biên bản họp (chỉ tập trung nội dung, không nêu tên/vai trò người)."""
import json
import os
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app import config

# Mã lỗi server tạm thời nên retry (quá tải / rate-limit / lỗi nội bộ)
TRANSIENT_CODES = (429, 500, 503)

# Map đuôi file -> MIME type. Gemini Files API cần mime_type rõ ràng;
# Python mimetypes không nhận diện .m4a/.opus... trên Linux container.
AUDIO_MIME = {
    ".mp3": "audio/mp3",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "video/webm",
    ".aiff": "audio/aiff",
}


def guess_mime(filename: str, fallback: str = "") -> str:
    """Suy ra MIME type từ đuôi file; fallback dùng content-type của trình duyệt."""
    ext = os.path.splitext(filename or "")[1].lower()
    return AUDIO_MIME.get(ext) or fallback or "application/octet-stream"


# ---- JSON schema (Pydantic) Gemini phải trả về ----
# Trường text "có thể thiếu" dùng chuỗi rỗng "" thay vì null cho gọn schema.
class DecisionItem(BaseModel):
    title: str
    detail: str


class DecisionGroup(BaseModel):
    category: str
    items: list[DecisionItem]


class ActionItem(BaseModel):
    task: str
    status_deadline: str   # "" nếu không có
    note: str


class MeetingSummary(BaseModel):
    title: str
    meeting_date: str      # "" nếu không nhắc trong audio
    summary: str
    key_decisions: list[DecisionGroup]
    action_items: list[ActionItem]


PROMPT = """Bạn là thư ký chuyên ghi biên bản họp. Dưới đây là file ghi âm một cuộc họp \
bằng tiếng Việt (có lẫn thuật ngữ tiếng Anh như deploy, sprint, API, repo, frontend...).

Hãy nghe kỹ và tạo biên bản họp theo đúng JSON schema được yêu cầu. Quy tắc:
- Viết bằng tiếng Việt. GIỮ NGUYÊN các thuật ngữ tiếng Anh, không dịch sang tiếng Việt.
- CHỈ tập trung vào NỘI DUNG cuộc họp. TUYỆT ĐỐI KHÔNG nêu tên người, KHÔNG gán vai trò
  hay người phụ trách cho bất kỳ ai. Diễn đạt trung tính theo nội dung (vd "cần làm...",
  "thống nhất...", "đề xuất...") thay vì "ai làm việc gì".
- summary: 1 đoạn tóm tắt cô đọng toàn bộ nội dung cuộc họp.
- key_decisions: gom các quyết định / nội dung quan trọng theo nhóm chủ đề (category).
  Mỗi mục gồm title (tiêu đề ngắn) và detail (1 đoạn diễn giải). Không nêu tên người.
- action_items: các việc cần làm, CHỈ mô tả công việc (không kèm tên người phụ trách).
  status_deadline = trạng thái/deadline nếu có nhắc (để "" nếu không); note = mô tả chi tiết việc cần làm.
- title: tiêu đề ngắn gọn của cuộc họp.
- meeting_date: ngày họp nếu được nhắc trong audio (để "" nếu không).
- TUYỆT ĐỐI không bịa thông tin không có trong audio. Không chắc thì để rỗng.
Chỉ trả về JSON đúng schema, không kèm giải thích."""


def _client() -> genai.Client:
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _upload_and_wait(client: genai.Client, file_path: str, mime_type: str, timeout: int = 300):
    """Upload file lên Files API (khai báo mime_type rõ ràng) và chờ tới khi ACTIVE."""
    f = client.files.upload(file=file_path, config={"mime_type": mime_type})
    waited = 0
    while f.state.name == "PROCESSING":
        if waited >= timeout:
            raise TimeoutError("Gemini xử lý file quá lâu (timeout).")
        time.sleep(2)
        waited += 2
        f = client.files.get(name=f.name)
    if f.state.name == "FAILED":
        raise RuntimeError("Gemini không xử lý được file audio này.")
    return f


def _generate(client: genai.Client, uploaded, max_attempts: int = 4) -> dict:
    """Gọi model, parse JSON. Retry: lỗi tạm thời (429/503/500) có backoff; JSON hỏng retry thẳng."""
    last_err = None
    for attempt in range(max_attempts):
        try:
            resp = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[PROMPT, uploaded],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MeetingSummary,
                    temperature=0.2,
                ),
            )
            data = json.loads(resp.text)
            MeetingSummary(**data)  # validate cấu trúc
            return data
        except genai_errors.APIError as e:
            last_err = e
            if getattr(e, "code", None) in TRANSIENT_CODES and attempt < max_attempts - 1:
                time.sleep(2 ** attempt)  # backoff 1s, 2s, 4s
                continue
            raise
        except Exception as e:  # noqa: BLE001 - JSON/schema hỏng -> retry thẳng
            last_err = e
    raise ValueError(f"Gemini trả JSON không hợp lệ sau {max_attempts} lần thử: {last_err}")


def summarize_meeting(file_path: str, mime_type: str) -> dict:
    """Nhận đường dẫn file audio + mime_type -> dict biên bản theo MeetingSummary."""
    client = _client()
    uploaded = _upload_and_wait(client, file_path, mime_type)
    try:
        return _generate(client, uploaded)
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:  # noqa: BLE001 - dọn dẹp best-effort
            pass
