
from unittest.mock import Mock
from pwm.work.end import generate_work_summary


def test_generate_work_summary_single_commit():
    """Test summary generation with single commit."""
    commits = [
        {"hash": "abc123", "subject": "Add user authentication", "body": ""}
    ]

    summary = generate_work_summary(commits)

    assert summary == "Add user authentication."


def test_generate_work_summary_multiple_commits():
    """Test summary generation with multiple commits."""
    commits = [
        {"hash": "abc123", "subject": "Add login endpoint", "body": ""},
        {"hash": "def456", "subject": "Add logout endpoint", "body": ""},
        {"hash": "ghi789", "subject": "Add tests", "body": ""}
    ]

    summary = generate_work_summary(commits)

    assert "Add login endpoint" in summary
    assert "2 other changes" in summary


def test_generate_work_summary_two_commits():
    """Test summary generation with exactly two commits."""
    commits = [
        {"hash": "abc123", "subject": "Add feature", "body": ""},
        {"hash": "def456", "subject": "Add tests", "body": ""}
    ]

    summary = generate_work_summary(commits)

    assert "Add feature" in summary
    assert "1 other change" in summary


def test_generate_work_summary_no_commits():
    """Test summary when there are no commits."""
    commits = []

    summary = generate_work_summary(commits)

    assert summary == "No new changes since last update."
