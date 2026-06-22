"""Đọc cấu hình từ .env."""
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "25"))
FOOTER_TEXT = os.getenv("FOOTER_TEXT", "AI Meeting Notes").strip()


def require_api_key() -> None:
    """Gọi lúc khởi động app — fail fast nếu thiếu key."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Thiếu GEMINI_API_KEY. Hãy copy .env.example -> .env và điền API key."
        )
