
from pwm.ai.summarizer import (
    format_commits_for_prompt,
    summarize_commits_for_pr,
    summarize_work_end,
    summarize_daily_work
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

def test_summarize_daily_work_returns_none_without_openai():
    """Test that summarize_daily_work returns None when OpenAI not configured."""
    prs = {'opened': [{'number': 1, 'title': 'Test PR'}], 'closed': [], 'merged': []}
    jira = {'created': [{'key': 'ABC-1', 'summary': 'Test'}], 'updated': []}
    result = summarize_daily_work(prs, jira, None)
    assert result is None

def test_summarize_daily_work_returns_none_without_work():
    """Test that summarize_daily_work returns None when no work to summarize."""
    class MockOpenAI:
        pass

    prs = {'opened': [], 'closed': [], 'merged': []}
    jira = {'created': [], 'updated': []}
    result = summarize_daily_work(prs, jira, MockOpenAI())
    assert result is None

def test_summarize_daily_work_calls_openai_with_work():
    """Test that summarize_daily_work calls OpenAI when there's work."""
    class MockOpenAI:
        def __init__(self):
            self.called = False
            self.prompt = None
            self.system = None

        def complete(self, prompt, system=None):
            self.called = True
            self.prompt = prompt
            self.system = system
            return "Great progress on features and bug fixes."

    mock_client = MockOpenAI()
    prs = {
        'opened': [{'number': 1, 'title': 'Add feature'}],
        'closed': [],
        'merged': [{'number': 2, 'title': 'Fix bug'}]
    }
    jira = {
        'created': [{'key': 'ABC-1', 'summary': 'New task'}],
        'updated': [{'key': 'ABC-2', 'summary': 'Update', 'status': {'name': 'Done'}}]
    }

    result = summarize_daily_work(prs, jira, mock_client)

    assert mock_client.called
    assert result == "Great progress on features and bug fixes."
    assert "Add feature" in mock_client.prompt
    assert "Fix bug" in mock_client.prompt
    assert "ABC-1" in mock_client.prompt
    assert "ABC-2" in mock_client.prompt

def test_summarize_daily_work_limits_items():
    """Test that summarize_daily_work limits items to 5 per category."""
    class MockOpenAI:
        def __init__(self):
            self.prompt = None

        def complete(self, prompt, system=None):
            self.prompt = prompt
            return "Summary"

    mock_client = MockOpenAI()
    prs = {
        'opened': [{'number': i, 'title': f'PR {i}'} for i in range(10)],
        'closed': [],
        'merged': []
    }
    jira = {'created': [], 'updated': []}

    summarize_daily_work(prs, jira, mock_client)

    # Should include first 5
    assert "PR 0" in mock_client.prompt
    assert "PR 4" in mock_client.prompt
    # Should show "and 5 more"
    assert "and 5 more" in mock_client.prompt

def test_summarize_daily_work_handles_missing_fields():
    """Test that summarize_daily_work handles PRs/issues with missing fields."""
    class MockOpenAI:
        def __init__(self):
            self.prompt = None

        def complete(self, prompt, system=None):
            self.prompt = prompt
            return "Summary"

    mock_client = MockOpenAI()
    prs = {
        'opened': [{'number': 1}],  # Missing title
        'closed': [],
        'merged': []
    }
    jira = {
        'created': [{'key': 'ABC-1'}],  # Missing summary
        'updated': []
    }

    result = summarize_daily_work(prs, jira, mock_client)

    assert result == "Summary"
    assert "Untitled" in mock_client.prompt
    assert "No summary" in mock_client.prompt
