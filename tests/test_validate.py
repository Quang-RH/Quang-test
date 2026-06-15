import pytest

from app import config
from app.main import validate_file


def test_reject_bad_ext():
    with pytest.raises(ValueError):
        validate_file("notes.txt", 1000)


def test_reject_no_ext():
    with pytest.raises(ValueError):
        validate_file("noextfile", 1000)


def test_reject_too_big():
    with pytest.raises(ValueError):
        validate_file("a.mp3", (config.MAX_FILE_MB + 1) * 1024 * 1024)


def test_accept_ok():
    # không raise
    validate_file("meeting.mp3", 5 * 1024 * 1024)
    validate_file("MEETING.M4A", 1000)
