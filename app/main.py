"""FastAPI app: phục vụ trang + xử lý file họp."""
import os
import secrets
import tempfile
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from app import config, doc_review, extract, gemini_service, render

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


def _check_size(size_bytes: int) -> None:
    if size_bytes > config.MAX_FILE_MB * 1024 * 1024:
        raise ValueError(
            f"File quá lớn ({size_bytes / 1024 / 1024:.1f}MB). "
            f"Giới hạn {config.MAX_FILE_MB}MB."
        )


def validate_file(filename: str, size_bytes: int) -> None:
    """Raise ValueError nếu sai định dạng audio hoặc quá lớn."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(
            f"Định dạng không hỗ trợ: {ext or '(không rõ)'}. "
            f"Hỗ trợ: {', '.join(sorted(ALLOWED_EXT))}"
        )
    _check_size(size_bytes)


def validate_doc(filename: str, size_bytes: int) -> None:
    """Raise ValueError nếu sai định dạng tài liệu hoặc quá lớn."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in extract.ALLOWED_DOC_EXT:
        raise ValueError(
            f"Định dạng không hỗ trợ: {ext or '(không rõ)'}. "
            f"Hỗ trợ: {', '.join(sorted(extract.ALLOWED_DOC_EXT))}"
        )
    _check_size(size_bytes)


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
        mime_type = gemini_service.guess_mime(file.filename, file.content_type or "")
        try:
            ai = gemini_service.summarize_meeting(tmp.name, mime_type)
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


@app.post("/review-doc")
async def review_doc(
    file: UploadFile = File(...),
    _: None = Depends(require_auth),
):
    contents = await file.read()
    try:
        validate_doc(file.filename, len(contents))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = os.path.splitext(file.filename)[1].lower()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(contents)
        tmp.close()
        try:
            text = extract.extract_text(tmp.name, file.filename)
        except Exception as e:  # noqa: BLE001 - lỗi đọc file -> 400
            raise HTTPException(status_code=400, detail=f"Không đọc được tài liệu: {e}")
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Không trích được nội dung text (tài liệu rỗng hoặc là bản scan ảnh?).",
            )
        try:
            review = doc_review.review_document(text)
        except Exception as e:  # noqa: BLE001 - bao lỗi AI thành 502
            raise HTTPException(status_code=502, detail=f"Lỗi xử lý AI: {e}")
        return {"filename": file.filename, "text": text, "review": review}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
