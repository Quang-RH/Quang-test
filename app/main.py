"""FastAPI app: phục vụ trang + xử lý file họp + review tài liệu."""
import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config, doc_review, extract, gemini_service, pdf_render, render

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
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    title: str = Form(""),
    meeting_date: str = Form(""),
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

        if ext == ".pdf":
            return _review_pdf(file.filename, tmp.name)

        # Office / text: trích text -> review (chế độ text)
        try:
            text = extract.extract_text(tmp.name, file.filename)
        except Exception as e:  # noqa: BLE001 - lỗi đọc file -> 400
            raise HTTPException(status_code=400, detail=f"Không đọc được tài liệu: {e}")
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Không trích được text (file rỗng hoặc bản scan ảnh — hãy lưu sang PDF).",
            )
        try:
            review = doc_review.review_document(text)
        except Exception as e:  # noqa: BLE001 - bao lỗi AI thành 502
            raise HTTPException(status_code=502, detail=f"Lỗi xử lý AI: {e}")
        return {"filename": file.filename, "mode": "text", "text": text, "review": review}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _review_pdf(filename: str, path: str) -> dict:
    """PDF -> ảnh trang + highlight (Turnitin). PDF gõ máy = tô theo tọa độ; scan = ảnh + OCR review."""
    try:
        full_text, pages = pdf_render.render_pdf(path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Không đọc được PDF: {e}")

    if full_text.strip():
        # PDF có lớp text -> review + định vị highlight theo tọa độ
        try:
            review = doc_review.review_document(full_text)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Lỗi xử lý AI: {e}")
        page_h = [[] for _ in pages]
        for i, f in enumerate(review.get("findings", [])):
            q = (f.get("quote") or "").strip()
            if not q:
                continue
            for rc in pdf_render.locate_quote(pages, q):
                page_h[rc["page"]].append(
                    {"id": i, "x": rc["x"], "y": rc["y"], "w": rc["w"], "h": rc["h"],
                     "sev": f.get("severity", "thấp")}
                )
        pages_payload = [
            {"image": pages[idx]["image"], "highlights": page_h[idx]} for idx in range(len(pages))
        ]
        return {"filename": filename, "mode": "pdf-image", "pages": pages_payload,
                "text": full_text, "review": review}

    # PDF scan (không có lớp text) -> Gemini OCR + review; hiện ảnh nhưng không overlay
    try:
        text, review = doc_review.review_pdf_native(path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lỗi xử lý AI (đọc PDF scan): {e}")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Không đọc được nội dung từ PDF này.")
    pages_payload = [{"image": p["image"], "highlights": []} for p in pages]
    return {"filename": filename, "mode": "pdf-image", "pages": pages_payload,
            "text": text, "review": review}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
