
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from pwm.pr.open import generate_pr_title, generate_pr_description


def test_generate_pr_title_with_jira():
    """Test PR title generation with Jira client."""
    jira = Mock()
    jira.get_issue_summary.return_value = "Implement user authentication"

    title = generate_pr_title("ABC-123", jira)

    assert title == "[ABC-123] Implement user authentication"
    jira.get_issue_summary.assert_called_once_with("ABC-123")


def test_generate_pr_title_without_jira():
    """Test PR title generation without Jira client."""
    title = generate_pr_title("ABC-123", None)

    assert title == "[ABC-123] Changes"


def test_generate_pr_description_basic():
    """Test PR description generation with commits."""
    commits = [
        {"hash": "abc123", "subject": "Add login endpoint", "body": ""},
        {"hash": "def456", "subject": "Add tests for auth", "body": ""}
    ]

    description = generate_pr_description("ABC-123", commits, None, "https://jira.example.com")

    assert "[ABC-123]" in description
    assert "https://jira.example.com/browse/ABC-123" in description
    assert "Add login endpoint" in description
    assert "Add tests for auth" in description
    assert "**Total commits:** 2" in description


def test_generate_pr_description_with_jira_description():
    """Test PR description includes Jira issue description."""
    jira = Mock()
    jira.get_issue.return_value = {
        "fields": {
            "description": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "This is the Jira issue description"}
                        ]
                    }
                ]
            }
        }
    }

    commits = [{"hash": "abc123", "subject": "Initial commit", "body": ""}]

    description = generate_pr_description("ABC-123", commits, jira, "https://jira.example.com")

    assert "This is the Jira issue description" in description
    assert "## Description" in description


def test_generate_pr_description_no_commits():
    """Test PR description with no commits."""
    description = generate_pr_description("ABC-123", [], None, "https://jira.example.com")

    assert "[ABC-123]" in description
    assert "https://jira.example.com/browse/ABC-123" in description
    # Should not have commits section
    assert "Total commits" not in description
