from app import render


def test_fallback_chua_xac_nhan():
    ai = {"title": "", "meeting_date": "", "participants": "", "summary": "x",
          "key_decisions": [], "action_items": [], "personnel": []}
    m = render.normalize(ai, {"title": "", "meeting_date": "", "participants": ""}, "MEETING-12345")
    assert m["meeting_date"] == "Chưa xác nhận"
    assert m["participants"] == "Chưa xác nhận"
    assert m["title"] == "Cuộc họp"
    assert m["personnel"][0]["role"] == "Chưa xác nhận"


def test_user_overrides_ai():
    ai = {"title": "AI Title", "meeting_date": "01/01/2026", "participants": "AI People",
          "summary": "x", "key_decisions": [], "action_items": [], "personnel": []}
    m = render.normalize(ai, {"title": "User Title", "meeting_date": "", "participants": "User People"},
                         "MEETING-1")
    assert m["title"] == "User Title"          # user ghi đè
    assert m["meeting_date"] == "01/01/2026"   # user trống -> dùng AI
    assert m["participants"] == "User People"


def test_markdown_has_all_sections():
    ai = {"title": "T", "meeting_date": "", "participants": "", "summary": "Tóm tắt nội dung",
          "key_decisions": [{"category": "Nhóm A", "items": [{"title": "QĐ1", "detail": "chi tiết"}]}],
          "action_items": [{"task": "việc 1", "owner": "An", "status_deadline": "", "note": "ghi chú"}],
          "personnel": []}
    m = render.normalize(ai, {}, "MEETING-9")
    md = render.to_markdown(m)
    assert "BIÊN BẢN HỌP" in md
    assert "1. Tóm tắt" in md
    assert "2. Các quyết định" in md
    assert "3. Danh sách công việc" in md
    assert "4. Phân công nhân sự" in md
    assert "QĐ1" in md and "việc 1" in md


def test_markdown_escapes_pipe():
    ai = {"title": "T", "meeting_date": "", "participants": "", "summary": "s",
          "key_decisions": [], "personnel": [],
          "action_items": [{"task": "a|b", "owner": "", "status_deadline": "", "note": "x"}]}
    m = render.normalize(ai, {}, "MEETING-2")
    md = render.to_markdown(m)
    assert "a\\|b" in md
