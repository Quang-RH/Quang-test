"""Chuẩn hoá dữ liệu biên bản + build markdown (chỉ nội dung, không tên/vai trò người)."""
import random

from app import config

CHUA_XAC_NHAN = "Chưa xác nhận"


def make_meeting_id() -> str:
    return f"MEETING-{random.randint(10000, 99999)}"


def normalize(ai: dict, user_input: dict, meeting_id: str) -> dict:
    """Gộp metadata người dùng (ưu tiên) + AI, áp fallback 'Chưa xác nhận'."""
    user_input = user_input or {}

    def merged(key: str, fallback: str) -> str:
        u = (user_input.get(key) or "").strip()
        a = (ai.get(key) or "").strip()
        val = u or a
        return val if val else fallback

    return {
        "meeting_id": meeting_id,
        "title": merged("title", "") or "Cuộc họp",
        "meeting_date": merged("meeting_date", CHUA_XAC_NHAN),
        "summary": (ai.get("summary") or "").strip(),
        "key_decisions": ai.get("key_decisions") or [],
        "action_items": ai.get("action_items") or [],
        "footer": config.FOOTER_TEXT,
    }


def _cell(s) -> str:
    return (s or "").replace("\n", " ").replace("|", "\\|").strip()


def to_markdown(m: dict) -> str:
    L = []
    L.append("# BIÊN BẢN HỌP: MEETING SUMMARY")
    L.append(f"## {m['meeting_id']}")
    L.append("")
    L.append(f"**Tên cuộc họp:** {m['title']}  ")
    L.append(f"**Ngày họp:** {m['meeting_date']}")
    L.append("")
    L.append("## 1. Tóm tắt cuộc họp (Summary)")
    L.append("")
    L.append(m["summary"] or "")
    L.append("")
    L.append("## 2. Các quyết định quan trọng (Key Decisions)")
    for grp in m["key_decisions"]:
        L.append("")
        L.append(f"### {grp.get('category', '')}")
        for it in grp.get("items", []):
            L.append("")
            L.append(f"**{it.get('title', '')}**")
            L.append("")
            L.append(it.get("detail", ""))
    L.append("")
    L.append("## 3. Danh sách công việc (Action Items)")
    L.append("")
    L.append("| Tên công việc | Trạng thái / Deadline | Ghi chú từ cuộc họp |")
    L.append("|---|---|---|")
    for a in m["action_items"]:
        L.append(
            f"| {_cell(a.get('task'))} | {_cell(a.get('status_deadline'))} | {_cell(a.get('note'))} |"
        )
    L.append("")
    L.append(f"*Biên bản này được tổng hợp tự động bởi {m['footer']}.*")
    return "\n".join(L)
