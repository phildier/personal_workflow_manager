
from pathlib import Path
import pwm.work.start as ws
import pwm.vcs.git_cli as git_cli
from pwm.jira import client as jira_client_module
from pwm.context.resolver import Context, ContextMeta

def test_work_start_creates_branch(monkeypatch, tmp_path):
    created = []
    switched = []

    monkeypatch.setattr(ws, "current_branch", lambda repo_root: None)
    def fake_create(repo_root: Path, branch_name: str, from_ref: str | None = None):
        created.append(branch_name); return True
    monkeypatch.setattr(ws, "create_branch", fake_create)
    monkeypatch.setattr(ws, "branch_exists", lambda repo_root, name: False)
    def fake_switch(repo_root: Path, name: str): switched.append(name); return True
    monkeypatch.setattr(ws, "switch_branch", fake_switch)

    class FakeJira:
        def get_issue_summary(self, key): return "Implement feature X"
        def transition_by_name(self, key, name): return True
        def add_comment(self, key, body): return True
    monkeypatch.setattr(jira_client_module.JiraClient, "from_config", classmethod(lambda cls, cfg: FakeJira()))

    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    config = {"branch": {"pattern": "feature/{issue_key}-{slug}"}}
    meta = ContextMeta(user_config_path=None, project_config_path=None, source_summary="defaults")
    fake_ctx = Context(repo_root=repo_root, config=config, github_repo="org/repo", jira_project_key="ABC", meta=meta)
    monkeypatch.setattr(ws, "resolve_context", lambda: fake_ctx)

    rc = ws.work_start("ABC-123", transition=True, comment=True)
    assert rc == 0
    assert created, "branch should be created"
    assert any(b.startswith("feature/ABC-123-implement-feature-x") for b in created)
    # Note: when create_branch is called, it uses git checkout -b which automatically switches
    # to the new branch, so switch_branch is not called separately
