"""FastAPI app: phục vụ trang + xử lý file họp."""
import os
import secrets
import tempfile
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from app import config, gemini_service, render

_security = HTTPBasic(auto_error=False)


def require_auth(creds: HTTPBasicCredentials = Depends(_security)) -> None:
    """Chặn bằng HTTP Basic nếu APP_PASSWORD được đặt; bỏ qua nếu để trống (local)."""
    if not config.APP_PASSWORD:
        return
    ok = creds is not None and secrets.compare_digest(
        creds.password, config.APP_PASSWORD
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Sai mật khẩu",
            headers={"WWW-Authenticate": "Basic"},
        )

ALLOWED_EXT = {
    ".mp3", ".m4a", ".mp4", ".wav", ".aac", ".ogg",
    ".flac", ".webm", ".mpeg", ".mpga", ".opus",
}

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.require_api_key()  # fail fast nếu thiếu key
    yield


app = FastAPI(title="AI Meeting Notes", lifespan=lifespan)


def validate_file(filename: str, size_bytes: int) -> None:
    """Raise ValueError nếu sai định dạng hoặc quá lớn."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(
            f"Định dạng không hỗ trợ: {ext or '(không rõ)'}. "
            f"Hỗ trợ: {', '.join(sorted(ALLOWED_EXT))}"
        )
    if size_bytes > config.MAX_FILE_MB * 1024 * 1024:
        raise ValueError(
            f"File quá lớn ({size_bytes / 1024 / 1024:.1f}MB). "
            f"Giới hạn {config.MAX_FILE_MB}MB."
        )


@app.get("/")
def index(_: None = Depends(require_auth)):
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    title: str = Form(""),
    meeting_date: str = Form(""),
    _: None = Depends(require_auth),
):
    contents = await file.read()
    try:
        validate_file(file.filename, len(contents))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = os.path.splitext(file.filename)[1].lower()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(contents)
        tmp.close()
        try:
            ai = gemini_service.summarize_meeting(tmp.name)
        except Exception as e:  # noqa: BLE001 - bao lỗi AI thành 502
            raise HTTPException(status_code=502, detail=f"Lỗi xử lý AI: {e}")

        meeting = render.normalize(
            ai,
            {"title": title, "meeting_date": meeting_date},
            render.make_meeting_id(),
        )
        return {"meeting": meeting, "markdown": render.to_markdown(meeting)}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
