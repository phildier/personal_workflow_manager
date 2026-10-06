from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from pwm.pr.open import generate_pr_title, generate_pr_description, open_pr
from pwm.pr.open import preflight_pr


def _ready_preflight(
    *,
    commits=None,
    existing_pr=None,
    ok=True,
    blocking_issues=None,
    head_sha="abc123",
):
    if commits is None:
        commits = [{"hash": "abc123", "subject": "Commit subject"}]
    if existing_pr is None:
        existing_pr = {
            "url": None,
            "number": None,
            "title": None,
            "source": "none",
        }
    return {
        "ok": ok,
        "repo_root": ".",
        "remote": {"name": "origin"},
        "branch": {"name": "ABC-123-test", "issue_key": "ABC-123"},
        "github_repository": {"resolved_repo": "org/repo"},
        "base_branch": {"ref": "origin/main", "name": "main"},
        "ahead": {"commits": commits},
        "existing_pr": existing_pr,
        "receipt": {"head_sha": head_sha},
        "blocking_issues": blocking_issues or [],
    }


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


def test_open_pr_blocks_on_preflight_failure(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}}

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr(
        "pwm.pr.open.preflight_pr",
        lambda **_kwargs: _ready_preflight(
            ok=False,
            blocking_issues=[
                {
                    "code": "missing_issue_key",
                    "message": "Branch missing key",
                    "remediation": "Run pwm ws ABC-123",
                }
            ],
        ),
    )
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(
            lambda *_args: (_ for _ in ()).throw(
                AssertionError("GitHub client should not be created")
            )
        ),
    )

    rc = open_pr(open_browser=False, use_ai=False, non_interactive=True)
    assert rc == 1


def test_open_pr_displays_github_creation_error(monkeypatch, capsys):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "jira": {}}

    class FakeGitHub:
        last_error = "GitHub API returned HTTP 422: Validation Failed (missing_field)"

        def get_pr_for_branch(self, _repo, _branch):
            return None

        def create_pr(self, repo, title, head, base, body=None):
            return None

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.preflight_pr", lambda **_kwargs: _ready_preflight())
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda cls, cfg: FakeGitHub()),
    )
    monkeypatch.setattr("pwm.pr.open.push_branch", lambda *_args: True)
    monkeypatch.setattr("pwm.pr.open.JiraClient.from_config", classmethod(lambda *_args: None))
    monkeypatch.setattr(
        "pwm.ai.openai_client.OpenAIClient.from_config",
        classmethod(lambda *_args: None),
    )

    rc = open_pr(open_browser=False, use_ai=False)

    assert rc == 1
    assert "HTTP 422: Validation Failed (missing_field)" in capsys.readouterr().out


def test_open_pr_uses_title_and_body_overrides(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "jira": {}}

    captured = {}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            return None

        def create_pr(self, repo, title, head, base, body=None):
            nonlocal captured
            captured = {
                "repo": repo,
                "title": title,
                "head": head,
                "base": base,
                "body": body,
            }
            return {"number": 12, "html_url": "https://example/pr/12"}

        def get_pr_details(self, _repo, _number):
            return None

        def get_pr_reviews(self, _repo, _number):
            return []

        def add_issue_labels(self, _repo, _issue_number, _labels):
            return True

        def add_issue_labels(self, _repo, _issue_number, _labels):
            return True

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.preflight_pr", lambda **_kwargs: _ready_preflight())
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda cls, cfg: FakeGitHub()),
    )
    monkeypatch.setattr("pwm.pr.open.push_branch", lambda *_args: True)
    monkeypatch.setattr("pwm.pr.open.JiraClient.from_config", classmethod(lambda *_args: None))
    monkeypatch.setattr(
        "pwm.ai.openai_client.OpenAIClient.from_config",
        classmethod(lambda *_args: None),
    )

    rc = open_pr(
        open_browser=False,
        use_ai=False,
        title_override="Manual title",
        body_override="Manual body",
    )

    assert rc == 0
    assert captured["title"] == "Manual title"
    assert captured["body"] == "Manual body"
    assert captured["head"] == "ABC-123-test"


def test_open_pr_applies_labels_to_existing_pr(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}}

    captured = {}

    class FakeGitHub:
        def add_issue_labels(self, repo, issue_number, labels):
            nonlocal captured
            captured = {
                "repo": repo,
                "issue_number": issue_number,
                "labels": labels,
            }
            return True

        def get_pr_details(self, _repo, _number):
            return None

        def get_pr_reviews(self, _repo, _number):
            return []

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr(
        "pwm.pr.open.preflight_pr",
        lambda **_kwargs: _ready_preflight(
            existing_pr={
                "url": "https://example/pr/34",
                "number": 34,
                "title": "Existing PR",
                "source": "github",
            }
        ),
    )
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda cls, cfg: FakeGitHub()),
    )

    rc = open_pr(open_browser=False, use_ai=False, labels=["bug", "bug", " ops "])

    assert rc == 0
    assert captured["repo"] == "org/repo"
    assert captured["issue_number"] == 34
    assert captured["labels"] == ["bug", "ops"]


def test_open_pr_applies_labels_to_new_pr(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "jira": {}}

    captured = {}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            return None

        def create_pr(self, repo, title, head, base, body=None):
            return {"number": 56, "html_url": "https://example/pr/56"}

        def add_issue_labels(self, repo, issue_number, labels):
            nonlocal captured
            captured = {
                "repo": repo,
                "issue_number": issue_number,
                "labels": labels,
            }
            return True

        def get_pr_details(self, _repo, _number):
            return None

        def get_pr_reviews(self, _repo, _number):
            return []

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.preflight_pr", lambda **_kwargs: _ready_preflight())
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda cls, cfg: FakeGitHub()),
    )
    monkeypatch.setattr("pwm.pr.open.push_branch", lambda *_args: True)
    monkeypatch.setattr(
        "pwm.pr.open.JiraClient.from_config", classmethod(lambda *_args: None)
    )
    monkeypatch.setattr(
        "pwm.ai.openai_client.OpenAIClient.from_config",
        classmethod(lambda *_args: None),
    )

    rc = open_pr(open_browser=False, use_ai=False, labels=["bug", "ai-assisted"])

    assert rc == 0
    assert captured["repo"] == "org/repo"
    assert captured["issue_number"] == 56
    assert captured["labels"] == ["bug", "ai-assisted"]


def test_open_pr_without_labels_does_not_call_add_labels(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "jira": {}}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            return None

        def create_pr(self, repo, title, head, base, body=None):
            return {"number": 78, "html_url": "https://example/pr/78"}

        def add_issue_labels(self, repo, issue_number, labels):
            raise AssertionError("add_issue_labels should not be called")

        def get_pr_details(self, _repo, _number):
            return None

        def get_pr_reviews(self, _repo, _number):
            return []

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.preflight_pr", lambda **_kwargs: _ready_preflight())
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda cls, cfg: FakeGitHub()),
    )
    monkeypatch.setattr("pwm.pr.open.push_branch", lambda *_args: True)
    monkeypatch.setattr(
        "pwm.pr.open.JiraClient.from_config", classmethod(lambda *_args: None)
    )
    monkeypatch.setattr(
        "pwm.ai.openai_client.OpenAIClient.from_config",
        classmethod(lambda *_args: None),
    )

    rc = open_pr(open_browser=False, use_ai=False)

    assert rc == 0


def test_preflight_reports_success_diagnostics(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "github": {"token": "x"}}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            return None

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.current_branch", lambda _repo_root: "ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._get_upstream_ref", lambda _repo_root: "origin/ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._head_sha", lambda _repo_root: "abc123")
    monkeypatch.setattr(
        "pwm.pr.open._get_remote_url",
        lambda _repo_root, _remote: "git@github.com:org/repo.git",
    )
    monkeypatch.setattr("pwm.pr.open.get_default_branch", lambda *_args: "origin/main")
    monkeypatch.setattr(
        "pwm.pr.open.get_commits_since_base",
        lambda *_args: [{"hash": "abc123", "subject": "Commit subject"}],
    )
    monkeypatch.setattr(
        "pwm.pr.open._changed_files_since_base",
        lambda *_args: ["pwm/pr/open.py"],
    )
    monkeypatch.setattr("pwm.pr.open._push_viability", lambda *_args: (True, "ok"))
    monkeypatch.setattr("pwm.pr.open._read_pr_receipt", lambda *_args: None)
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda *_args: FakeGitHub()),
    )

    result = preflight_pr(labels=["ai-assisted"])

    assert result["ok"] is True
    assert result["branch"]["issue_key"] == "ABC-123"
    assert result["base_branch"]["ref"] == "origin/main"
    assert result["ahead"]["commit_count"] == 1
    assert result["ahead"]["changed_file_count"] == 1
    assert result["github_repository"]["resolved_repo"] == "org/repo"
    assert result["existing_pr"]["source"] == "none"


def test_preflight_blocks_when_no_changes_without_create_anyway(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "github": {"token": "x"}}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            return None

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.current_branch", lambda _repo_root: "ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._get_upstream_ref", lambda _repo_root: "origin/ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._head_sha", lambda _repo_root: "abc123")
    monkeypatch.setattr(
        "pwm.pr.open._get_remote_url",
        lambda _repo_root, _remote: "git@github.com:org/repo.git",
    )
    monkeypatch.setattr("pwm.pr.open.get_default_branch", lambda *_args: "origin/main")
    monkeypatch.setattr("pwm.pr.open.get_commits_since_base", lambda *_args: [])
    monkeypatch.setattr("pwm.pr.open._changed_files_since_base", lambda *_args: [])
    monkeypatch.setattr("pwm.pr.open._push_viability", lambda *_args: (True, "ok"))
    monkeypatch.setattr("pwm.pr.open._read_pr_receipt", lambda *_args: None)
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda *_args: FakeGitHub()),
    )

    result = preflight_pr(create_anyway=False)

    assert result["ok"] is False
    codes = {issue["code"] for issue in result["blocking_issues"]}
    assert "no_changes_ahead" in codes


def test_preflight_uses_receipt_when_head_and_labels_match(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "github": {"token": "x"}}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            raise AssertionError("Should not call GitHub when receipt is reusable")

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.current_branch", lambda _repo_root: "ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._get_upstream_ref", lambda _repo_root: "origin/ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._head_sha", lambda _repo_root: "abc123")
    monkeypatch.setattr(
        "pwm.pr.open._get_remote_url",
        lambda _repo_root, _remote: "git@github.com:org/repo.git",
    )
    monkeypatch.setattr("pwm.pr.open.get_default_branch", lambda *_args: "origin/main")
    monkeypatch.setattr(
        "pwm.pr.open.get_commits_since_base",
        lambda *_args: [{"hash": "abc123", "subject": "Commit subject"}],
    )
    monkeypatch.setattr(
        "pwm.pr.open._changed_files_since_base",
        lambda *_args: ["pwm/pr/open.py"],
    )
    monkeypatch.setattr("pwm.pr.open._push_viability", lambda *_args: (True, "ok"))
    monkeypatch.setattr(
        "pwm.pr.open._read_pr_receipt",
        lambda *_args: {
            "branch": "ABC-123-test",
            "head_sha": "abc123",
            "pr_url": "https://example/pr/11",
            "labels": ["ai-assisted"],
        },
    )
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda *_args: FakeGitHub()),
    )

    result = preflight_pr(labels=["ai-assisted"])

    assert result["existing_pr"]["source"] == "receipt"
    assert result["existing_pr"]["url"] == "https://example/pr/11"
    assert result["receipt"]["reusable"] is True


def test_preflight_invalidates_receipt_when_head_changes(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "github": {"token": "x"}}

    github_calls = {"count": 0}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            github_calls["count"] += 1
            return None

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.current_branch", lambda _repo_root: "ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._get_upstream_ref", lambda _repo_root: "origin/ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._head_sha", lambda _repo_root: "newsha")
    monkeypatch.setattr(
        "pwm.pr.open._get_remote_url",
        lambda _repo_root, _remote: "git@github.com:org/repo.git",
    )
    monkeypatch.setattr("pwm.pr.open.get_default_branch", lambda *_args: "origin/main")
    monkeypatch.setattr(
        "pwm.pr.open.get_commits_since_base",
        lambda *_args: [{"hash": "abc123", "subject": "Commit subject"}],
    )
    monkeypatch.setattr(
        "pwm.pr.open._changed_files_since_base",
        lambda *_args: ["pwm/pr/open.py"],
    )
    monkeypatch.setattr("pwm.pr.open._push_viability", lambda *_args: (True, "ok"))
    monkeypatch.setattr(
        "pwm.pr.open._read_pr_receipt",
        lambda *_args: {
            "branch": "ABC-123-test",
            "head_sha": "oldsha",
            "pr_url": "https://example/pr/11",
            "labels": ["ai-assisted"],
        },
    )
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda *_args: FakeGitHub()),
    )

    result = preflight_pr(labels=["ai-assisted"])

    assert result["receipt"]["reusable"] is False
    assert github_calls["count"] == 1


def test_open_pr_writes_receipt_on_create(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}, "jira": {}}

    receipt = {}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            return None

        def create_pr(self, repo, title, head, base, body=None):
            return {"number": 56, "html_url": "https://example/pr/56"}

        def add_issue_labels(self, _repo, _issue_number, _labels):
            return True

        def get_pr_details(self, _repo, _number):
            return None

        def get_pr_reviews(self, _repo, _number):
            return []

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.preflight_pr", lambda **_kwargs: _ready_preflight())
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda *_args: FakeGitHub()),
    )
    monkeypatch.setattr("pwm.pr.open.push_branch", lambda *_args: True)
    monkeypatch.setattr(
        "pwm.pr.open.JiraClient.from_config", classmethod(lambda *_args: None)
    )
    monkeypatch.setattr(
        "pwm.ai.openai_client.OpenAIClient.from_config",
        classmethod(lambda *_args: None),
    )
    monkeypatch.setattr(
        "pwm.pr.open._write_pr_receipt",
        lambda **kwargs: receipt.update(kwargs),
    )

    rc = open_pr(open_browser=False, use_ai=False, labels=["ai-assisted"])

    assert rc == 0
    assert receipt["branch"] == "ABC-123-test"
    assert receipt["head_sha"] == "abc123"
    assert receipt["pr_url"] == "https://example/pr/56"
    assert receipt["labels"] == ["ai-assisted"]


def test_preflight_reports_remote_repo_mismatch(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo-configured"
        config = {
            "git": {"default_remote": "origin"},
            "github": {"token": "x", "repo": "org/repo-configured"},
        }

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            return None

    def fake_remote_url(_repo_root, remote):
        if remote == "origin":
            return "git@github.com:org/repo-origin.git"
        if remote == "upstream":
            return "git@github.com:org/repo-configured.git"
        return None

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.current_branch", lambda _repo_root: "ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._get_upstream_ref", lambda _repo_root: "origin/ABC-123-test")
    monkeypatch.setattr("pwm.pr.open._head_sha", lambda _repo_root: "abc123")
    monkeypatch.setattr("pwm.pr.open._get_remote_url", fake_remote_url)
    monkeypatch.setattr("pwm.pr.open._list_remotes", lambda _repo_root: ["origin", "upstream"])
    monkeypatch.setattr("pwm.pr.open.get_default_branch", lambda *_args: "origin/main")
    monkeypatch.setattr(
        "pwm.pr.open.get_commits_since_base",
        lambda *_args: [{"hash": "abc123", "subject": "Commit subject"}],
    )
    monkeypatch.setattr(
        "pwm.pr.open._changed_files_since_base",
        lambda *_args: ["pwm/pr/open.py"],
    )
    monkeypatch.setattr("pwm.pr.open._push_viability", lambda *_args: (True, "ok"))
    monkeypatch.setattr("pwm.pr.open._read_pr_receipt", lambda *_args: None)
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda *_args: FakeGitHub()),
    )

    result = preflight_pr()

    assert result["github_repository"]["remote_mismatch"] is True
    assert result["github_repository"]["matching_remote_for_configured_repo"] == (
        "upstream"
    )
    warning_codes = {warning["code"] for warning in result["warnings"]}
    assert "github_repo_mismatch" in warning_codes


def test_open_pr_reuses_receipt_without_pr_lookup(monkeypatch):
    class Ctx:
        repo_root = Path(".")
        github_repo = "org/repo"
        config = {"git": {"default_remote": "origin"}}

    class FakeGitHub:
        def get_pr_for_branch(self, _repo, _branch):
            raise AssertionError("Should not query PR when receipt is reusable")

    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr(
        "pwm.pr.open.preflight_pr",
        lambda **_kwargs: _ready_preflight(
            existing_pr={
                "url": "https://example/pr/99",
                "number": 99,
                "title": "Existing",
                "source": "receipt",
            }
        ),
    )
    monkeypatch.setattr(
        "pwm.pr.open.GitHubClient.from_config",
        classmethod(lambda *_args: FakeGitHub()),
    )

    rc = open_pr(open_browser=False, use_ai=False)

    assert rc == 0
