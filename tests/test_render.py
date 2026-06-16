from app import render


def test_fallback_chua_xac_nhan():
    ai = {"title": "", "meeting_date": "", "summary": "x",
          "key_decisions": [], "action_items": []}
    m = render.normalize(ai, {"title": "", "meeting_date": ""}, "MEETING-12345")
    assert m["meeting_date"] == "Chưa xác nhận"
    assert m["title"] == "Cuộc họp"


def test_user_overrides_ai():
    ai = {"title": "AI Title", "meeting_date": "01/01/2026",
          "summary": "x", "key_decisions": [], "action_items": []}
    m = render.normalize(ai, {"title": "User Title", "meeting_date": ""}, "MEETING-1")
    assert m["title"] == "User Title"          # user ghi đè
    assert m["meeting_date"] == "01/01/2026"   # user trống -> dùng AI


def test_no_people_fields():
    """Biên bản không còn trường về tên/vai trò người."""
    ai = {"title": "T", "meeting_date": "", "summary": "s",
          "key_decisions": [], "action_items": []}
    m = render.normalize(ai, {}, "MEETING-3")
    assert "participants" not in m
    assert "personnel" not in m


def test_markdown_has_sections_no_personnel():
    ai = {"title": "T", "meeting_date": "", "summary": "Tóm tắt nội dung",
          "key_decisions": [{"category": "Nhóm A", "items": [{"title": "QĐ1", "detail": "chi tiết"}]}],
          "action_items": [{"task": "việc 1", "status_deadline": "", "note": "ghi chú"}]}
    m = render.normalize(ai, {}, "MEETING-9")
    md = render.to_markdown(m)
    assert "BIÊN BẢN HỌP" in md
    assert "1. Tóm tắt" in md
    assert "2. Các quyết định" in md
    assert "3. Danh sách công việc" in md
    assert "QĐ1" in md and "việc 1" in md
    # KHÔNG còn mục/ cột về người
    assert "Phân công nhân sự" not in md
    assert "Người phụ trách" not in md
    assert "Đối tượng" not in md


def test_markdown_escapes_pipe():
    ai = {"title": "T", "meeting_date": "", "summary": "s", "key_decisions": [],
          "action_items": [{"task": "a|b", "status_deadline": "", "note": "x"}]}
    m = render.normalize(ai, {}, "MEETING-2")
    md = render.to_markdown(m)
    assert "a\\|b" in md
