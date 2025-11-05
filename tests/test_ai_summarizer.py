
from pwm.ai.summarizer import (
    format_commits_for_prompt,
    summarize_commits_for_pr,
    summarize_work_end
)

def test_format_commits_for_prompt():
    """Test formatting commits for AI prompts."""
    commits = [
        {"subject": "Add user authentication", "body": "Implemented JWT tokens"},
        {"subject": "Fix login bug", "body": ""},
        {"subject": "Update docs", "body": ""}
    ]

    result = format_commits_for_prompt(commits)

    assert "Add user authentication" in result
    assert "Implemented JWT tokens" in result
    assert "Fix login bug" in result
    assert "Update docs" in result

def test_format_commits_for_prompt_limits_commits():
    """Test that format_commits_for_prompt limits number of commits."""
    commits = [{"subject": f"Commit {i}", "body": ""} for i in range(15)]

    result = format_commits_for_prompt(commits, max_commits=10)

    assert "Commit 0" in result
    assert "Commit 9" in result
    assert "... and 5 more commits" in result

def test_format_commits_for_prompt_empty():
    """Test formatting empty commit list."""
    result = format_commits_for_prompt([])
    assert result == "(no commits)"

def test_summarize_commits_for_pr_returns_none_without_openai():
    """Test that summarize_commits_for_pr returns None when OpenAI not configured."""
    commits = [{"subject": "test", "body": ""}]
    result = summarize_commits_for_pr(commits, None)
    assert result is None

def test_summarize_commits_for_pr_returns_none_without_commits():
    """Test that summarize_commits_for_pr returns None when no commits."""
    # Mock OpenAI client (we don't actually call the API in tests)
    class MockOpenAI:
        pass

    result = summarize_commits_for_pr([], MockOpenAI())
    assert result is None

def test_summarize_work_end_returns_none_without_openai():
    """Test that summarize_work_end returns None when OpenAI not configured."""
    commits = [{"subject": "test", "body": ""}]
    result = summarize_work_end(commits, None)
    assert result is None

def test_summarize_work_end_returns_none_without_commits():
    """Test that summarize_work_end returns None when no commits."""
    # Mock OpenAI client
    class MockOpenAI:
        pass

    result = summarize_work_end([], MockOpenAI())
    assert result is None
