import pwm.work.create as create_module
from pwm.context.resolver import Context, ContextMeta


def test_issue_create_success_forwards_to_create_new_issue(monkeypatch, tmp_path):
    captured = {}

    class FakeJira:
        base_url = "https://jira.example.com"

    monkeypatch.setattr(
        create_module.JiraClient,
        "from_config",
        classmethod(lambda cls, cfg: FakeJira()),
    )

    def fake_create_new_issue(jira, project_key, repo_root, config, **kwargs):
        nonlocal captured
        captured = {
            "project_key": project_key,
            "repo_root": repo_root,
            **kwargs,
        }
        return "ABC-123"

    monkeypatch.setattr(create_module, "create_new_issue", fake_create_new_issue)

    meta = ContextMeta(
        user_config_path=None,
        project_config_path=None,
        source_summary="defaults",
    )
    ctx = Context(
        repo_root=tmp_path,
        config={"jira": {}},
        github_repo="org/repo",
        jira_project_key="ABC",
        meta=meta,
    )
    monkeypatch.setattr(create_module, "resolve_context", lambda: ctx)

    run_details = {}
    rc = create_module.issue_create(
        non_interactive=True,
        summary="Implement feature",
        description="Desc",
        issue_type="Task",
        labels=["backend"],
        story_points=3.0,
        epic="ABC-100",
        custom_fields={"customfield_1": "x"},
        save_defaults=False,
        event_details=run_details,
    )

    assert rc == 0
    assert captured["project_key"] == "ABC"
    assert captured["repo_root"] == tmp_path
    assert captured["non_interactive"] is True
    assert captured["summary"] == "Implement feature"
    assert captured["epic"] == "ABC-100"
    assert run_details["issue_key"] == "ABC-123"


def test_issue_create_errors_when_jira_not_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(
        create_module.JiraClient,
        "from_config",
        classmethod(lambda cls, cfg: None),
    )

    meta = ContextMeta(
        user_config_path=None,
        project_config_path=None,
        source_summary="defaults",
    )
    ctx = Context(
        repo_root=tmp_path,
        config={"jira": {}},
        github_repo="org/repo",
        jira_project_key="ABC",
        meta=meta,
    )
    monkeypatch.setattr(create_module, "resolve_context", lambda: ctx)

    assert create_module.issue_create(summary="x") == 1


def test_issue_create_errors_when_project_key_missing(monkeypatch, tmp_path):
    class FakeJira:
        base_url = "https://jira.example.com"

    monkeypatch.setattr(
        create_module.JiraClient,
        "from_config",
        classmethod(lambda cls, cfg: FakeJira()),
    )

    meta = ContextMeta(
        user_config_path=None,
        project_config_path=None,
        source_summary="defaults",
    )
    ctx = Context(
        repo_root=tmp_path,
        config={"jira": {}},
        github_repo="org/repo",
        jira_project_key=None,
        meta=meta,
    )
    monkeypatch.setattr(create_module, "resolve_context", lambda: ctx)

    assert create_module.issue_create(summary="x") == 1


def test_issue_create_returns_error_when_creation_fails(monkeypatch, tmp_path):
    class FakeJira:
        base_url = "https://jira.example.com"

    monkeypatch.setattr(
        create_module.JiraClient,
        "from_config",
        classmethod(lambda cls, cfg: FakeJira()),
    )
    monkeypatch.setattr(
        create_module,
        "create_new_issue",
        lambda *args, **kwargs: None,
    )

    meta = ContextMeta(
        user_config_path=None,
        project_config_path=None,
        source_summary="defaults",
    )
    ctx = Context(
        repo_root=tmp_path,
        config={"jira": {}},
        github_repo="org/repo",
        jira_project_key="ABC",
        meta=meta,
    )
    monkeypatch.setattr(create_module, "resolve_context", lambda: ctx)

    assert create_module.issue_create(summary="x") == 1
