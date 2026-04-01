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


def test_generate_pr_title_without_jira_with_commits():
    """Test PR title generation falls back to commit message when Jira unavailable."""
    commits = [
        {"hash": "abc123", "subject": "Add login endpoint", "body": ""},
        {"hash": "def456", "subject": "Add tests", "body": ""},
    ]

    title = generate_pr_title("ABC-123", None, commits)

    assert title == "[ABC-123] Add login endpoint"


def test_generate_pr_title_without_jira_without_commits():
    """Test PR title generation with no Jira and no commits."""
    title = generate_pr_title("ABC-123", None, [])

    assert title == "[ABC-123] Changes"


def test_generate_pr_title_jira_priority():
    """Test that Jira summary takes priority over commit messages."""
    jira = Mock()
    jira.get_issue_summary.return_value = "Implement user authentication"
    commits = [{"hash": "abc123", "subject": "Add login endpoint", "body": ""}]

    title = generate_pr_title("ABC-123", jira, commits)

    assert title == "[ABC-123] Implement user authentication"
    # Should use Jira, not commits
    jira.get_issue_summary.assert_called_once_with("ABC-123")


def test_generate_pr_description_basic():
    """Test PR description generation with commits."""
    commits = [
        {"hash": "abc123", "subject": "Add login endpoint", "body": ""},
        {"hash": "def456", "subject": "Add tests for auth", "body": ""},
    ]

    description = generate_pr_description(
        "ABC-123", commits, None, "https://jira.example.com"
    )

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
                            {
                                "type": "text",
                                "text": "This is the Jira issue description",
                            }
                        ],
                    }
                ],
            }
        }
    }

    commits = [{"hash": "abc123", "subject": "Initial commit", "body": ""}]

    description = generate_pr_description(
        "ABC-123", commits, jira, "https://jira.example.com"
    )

    assert "This is the Jira issue description" in description
    assert "## Description" in description


def test_generate_pr_description_no_commits():
    """Test PR description with no commits."""
    description = generate_pr_description(
        "ABC-123", [], None, "https://jira.example.com"
    )

    assert "[ABC-123]" in description
    assert "https://jira.example.com/browse/ABC-123" in description
    # Should not have commits section
    assert "Total commits" not in description


def test_generate_pr_description_with_diff_summary():
    """Test PR description includes diff summary when provided."""

    class MockOpenAI:
        def complete(self, prompt, system=None):
            # Return different summaries based on prompt content
            if "diff --git" in prompt:
                return "Modified authentication module to use JWT tokens instead of sessions."
            return "Added authentication feature"

    commits = [{"hash": "abc123", "subject": "Add auth", "body": ""}]
    diff = "diff --git a/auth.py b/auth.py\n+def use_jwt():\n+    pass"

    description = generate_pr_description(
        "ABC-123",
        commits,
        None,
        "https://jira.example.com",
        openai=MockOpenAI(),
        use_ai=True,
        diff=diff,
    )

    assert "## Code Changes" in description
    assert "Modified authentication module" in description
    assert "JWT tokens" in description


def test_generate_pr_description_without_diff():
    """Test PR description without diff parameter (backward compatibility)."""
    commits = [{"hash": "abc123", "subject": "Add feature", "body": ""}]

    description = generate_pr_description(
        "ABC-123",
        commits,
        None,
        "https://jira.example.com",
        openai=None,
        use_ai=True,
        diff=None,
    )

    assert "## Code Changes" not in description
    assert "[ABC-123]" in description


def test_generate_pr_description_diff_with_no_ai():
    """Test that diff summary is skipped when use_ai=False."""

    class MockOpenAI:
        def complete(self, prompt, system=None):
            raise AssertionError("Should not be called when use_ai=False")

    commits = [{"hash": "abc123", "subject": "Add feature", "body": ""}]
    diff = "diff --git a/test.py b/test.py\n+def foo():\n+    pass"

    description = generate_pr_description(
        "ABC-123",
        commits,
        None,
        "https://jira.example.com",
        openai=MockOpenAI(),
        use_ai=False,
        diff=diff,
    )

    assert "## Code Changes" not in description


def test_generate_pr_description_empty_diff():
    """Test PR description with empty diff string."""

    class MockOpenAI:
        def complete(self, prompt, system=None):
            return None

    commits = [{"hash": "abc123", "subject": "Add feature", "body": ""}]
    diff = ""

    description = generate_pr_description(
        "ABC-123",
        commits,
        None,
        "https://jira.example.com",
        openai=MockOpenAI(),
        use_ai=True,
        diff=diff,
    )

    # Should not have code changes section with empty diff
    assert "## Code Changes" not in description


def test_generate_pr_description_uses_precomputed_diff_summary():
    """If diff summary is provided, helper should not invoke OpenAI diff path."""

    class FailingOpenAI:
        def complete(self, prompt, system=None):
            if "diff --git" in prompt:
                raise AssertionError(
                    "Diff summarization should not run when diff_summary is supplied"
                )
            return "Commit summary"

    commits = [{"hash": "abc123", "subject": "Add feature", "body": ""}]
    description = generate_pr_description(
        "ABC-123",
        commits,
        jira=None,
        jira_base_url="https://jira.example.com",
        openai=FailingOpenAI(),
        use_ai=True,
        diff="diff --git a/a.py b/a.py",
        diff_summary="Precomputed code changes summary.",
    )

    assert "## Code Changes" in description
    assert "Precomputed code changes summary." in description
    assert "Commit summary" in description
