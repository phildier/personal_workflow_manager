
from pathlib import Path
import pwm.work.start as ws
import pwm.vcs.git_cli as git_cli
from pwm.jira import client as jira_client_module
from pwm.context.resolver import Context, ContextMeta
from pwm.work import create_issue as create_issue_module

def test_work_start_creates_branch(monkeypatch, tmp_path):
    created = []
    switched = []

    monkeypatch.setattr(ws, "current_branch", lambda repo_root: None)
    def fake_create(repo_root: Path, branch_name: str, from_ref: str | None = None, remote: str = "origin"):
        created.append(branch_name); return True
    monkeypatch.setattr(ws, "create_branch", fake_create)
    monkeypatch.setattr(ws, "branch_exists", lambda repo_root, name: False)
    def fake_switch(repo_root: Path, name: str): switched.append(name); return True
    monkeypatch.setattr(ws, "switch_branch", fake_switch)

    class FakeJira:
        def get_issue_summary(self, key): return "Implement feature X"
        def transition_by_name(self, key, name): return True
        def add_comment(self, key, body): return True
        def get_current_account_id(self): return "test-account-id-123"
        def assign_issue(self, key, account_id): return True
    monkeypatch.setattr(jira_client_module.JiraClient, "from_config", classmethod(lambda cls, cfg: FakeJira()))

    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    config = {"branch": {"pattern": "{issue_key}-{slug}"}}
    meta = ContextMeta(user_config_path=None, project_config_path=None, source_summary="defaults")
    fake_ctx = Context(repo_root=repo_root, config=config, github_repo="org/repo", jira_project_key="ABC", meta=meta)
    monkeypatch.setattr(ws, "resolve_context", lambda: fake_ctx)

    rc = ws.work_start(issue_key="ABC-123", transition=True, comment=True)
    assert rc == 0
    assert created, "branch should be created"
    assert any(b.startswith("ABC-123-implement-feature-x") for b in created)
    # Note: when create_branch is called, it uses git checkout -b which automatically switches
    # to the new branch, so switch_branch is not called separately

def test_work_start_with_new_flag(monkeypatch, tmp_path):
    """Test work-start --new creates a Jira issue and branch."""
    created = []
    created_issue_key = None

    # Mock git operations
    monkeypatch.setattr(ws, "current_branch", lambda repo_root: None)
    def fake_create(repo_root: Path, branch_name: str, from_ref: str | None = None, remote: str = "origin"):
        created.append(branch_name); return True
    monkeypatch.setattr(ws, "create_branch", fake_create)
    monkeypatch.setattr(ws, "branch_exists", lambda repo_root, name: False)

    # Mock Jira client
    class FakeJira:
        def get_issue_summary(self, key):
            return "Test issue summary"
        def transition_by_name(self, key, name):
            return True
        def add_comment(self, key, body):
            return True
        def get_issue_types(self, project_key):
            return [{"id": "1", "name": "Story", "description": ""}]
        def get_current_account_id(self):
            return "test-account-id-456"
        def assign_issue(self, key, account_id):
            return True
    monkeypatch.setattr(jira_client_module.JiraClient, "from_config", classmethod(lambda cls, cfg: FakeJira()))

    # Mock create_new_issue (patch where it's used, not where it's defined)
    def fake_create_issue(jira, project_key, repo_root, config):
        return "TEST-456"
    monkeypatch.setattr(ws, "create_new_issue", fake_create_issue)

    # Setup context
    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    config = {"branch": {"pattern": "{issue_key}-{slug}"}, "jira": {"issue_defaults": {}}}
    meta = ContextMeta(user_config_path=None, project_config_path=None, source_summary="defaults")
    fake_ctx = Context(repo_root=repo_root, config=config, github_repo="org/repo", jira_project_key="TEST", meta=meta)
    monkeypatch.setattr(ws, "resolve_context", lambda: fake_ctx)

    # Run work_start with create_new flag
    rc = ws.work_start(create_new=True, transition=True, comment=True)
    assert rc == 0
    assert created, "branch should be created"
    assert any(b.startswith("TEST-456-") for b in created), f"Expected branch starting with TEST-456, got {created}"

def test_work_start_errors_with_both_new_and_issue_key(monkeypatch, tmp_path):
    """Test that providing both --new and issue_key returns error."""
    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    config = {}
    meta = ContextMeta(user_config_path=None, project_config_path=None, source_summary="defaults")
    fake_ctx = Context(repo_root=repo_root, config=config, github_repo="org/repo", jira_project_key="TEST", meta=meta)
    monkeypatch.setattr(ws, "resolve_context", lambda: fake_ctx)

    rc = ws.work_start(issue_key="ABC-123", create_new=True)
    assert rc == 1

def test_work_start_errors_with_neither_new_nor_issue_key(monkeypatch, tmp_path):
    """Test that providing neither --new nor issue_key returns error."""
    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    config = {}
    meta = ContextMeta(user_config_path=None, project_config_path=None, source_summary="defaults")
    fake_ctx = Context(repo_root=repo_root, config=config, github_repo="org/repo", jira_project_key="TEST", meta=meta)
    monkeypatch.setattr(ws, "resolve_context", lambda: fake_ctx)

    rc = ws.work_start()
    assert rc == 1
