"""Render PDF -> ảnh từng trang + tọa độ chữ, để highlight kiểu Turnitin."""
import base64
from collections import defaultdict

try:
    import pymupdf as fitz
except ImportError:  # bản cũ
    import fitz


def render_pdf(file_path: str, zoom: float = 2.0):
    """Trả (full_text, pages). pages[i] = {image(dataURL), wpt, hpt, words[]}.
    words rỗng nếu trang không có lớp text (PDF scan)."""
    doc = fitz.open(file_path)
    pages = []
    texts = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img_b64 = base64.b64encode(pix.tobytes("png")).decode("ascii")
            rect = page.rect
            words = []
            for w in page.get_text("words"):
                # (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                words.append(
                    {"t": w[4], "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3], "line": (w[5], w[6])}
                )
            pages.append(
                {
                    "image": "data:image/png;base64," + img_b64,
                    "wpt": float(rect.width) or 1.0,
                    "hpt": float(rect.height) or 1.0,
                    "words": words,
                }
            )
            texts.append(page.get_text())
    finally:
        doc.close()
    return "\n".join(texts).strip(), pages


def _normalize(s: str) -> str:
    return "".join((s or "").split())


def locate_quote(pages, quote: str):
    """Tìm quote trên các trang -> list rect chuẩn hoá {page,x,y,w,h} (0..1), mỗi dòng 1 rect."""
    qn = _normalize(quote)
    if not qn:
        return []
    for pidx, page in enumerate(pages):
        words = page["words"]
        if not words:
            continue
        concat = ""
        owner = []  # char index -> word index
        for wi, w in enumerate(words):
            wt = _normalize(w["t"])
            concat += wt
            owner.extend([wi] * len(wt))
        pos = concat.find(qn)
        if pos < 0:
            continue
        idxs = sorted(set(owner[pos:pos + len(qn)]))
        if not idxs:
            continue
        by_line = defaultdict(list)
        for wi in idxs:
            by_line[words[wi]["line"]].append(words[wi])
        W, H = page["wpt"], page["hpt"]
        rects = []
        for ws in by_line.values():
            x0 = min(w["x0"] for w in ws)
            y0 = min(w["y0"] for w in ws)
            x1 = max(w["x1"] for w in ws)
            y1 = max(w["y1"] for w in ws)
            rects.append(
                {"page": pidx, "x": x0 / W, "y": y0 / H, "w": (x1 - x0) / W, "h": (y1 - y0) / H}
            )
        return rects
    return []
