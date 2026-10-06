from pwm.config import agent_defaults


def test_load_agent_jira_defaults_prefers_project_and_repository_match(
    monkeypatch,
    tmp_path,
):
    defaults_path = tmp_path / "agent-defaults.toml"
    defaults_path.write_text(
        "\n".join(
            [
                "[[defaults]]",
                'project = "ABC"',
                'issue_type = "Task"',
                'labels = ["project"]',
                "",
                "[[defaults]]",
                'repository = "org/repo"',
                'issue_type = "Bug"',
                'labels = ["repository"]',
                "",
                "[[defaults]]",
                'project = "ABC"',
                'repository = "org/repo"',
                'issue_type = "Story"',
                'labels = ["both"]',
                'reporter = "none"',
                "[defaults.responsible_team]",
                'field = "customfield_10370"',
                'value = "Core"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent_defaults, "AGENT_DEFAULTS_PATH", defaults_path)

    resolution = agent_defaults.load_agent_jira_defaults(
        project_key="ABC",
        github_repo="org/repo",
        repo_name="repo",
    )

    assert resolution.warning is None
    assert resolution.overrides["issue_type"] == "Story"
    assert resolution.overrides["labels"] == ["both"]
    assert resolution.overrides["reporter_behavior"] == "none"
    assert resolution.overrides["custom_fields"]["customfield_10370"] == {
        "value": "Core"
    }


def test_load_agent_jira_defaults_supports_repo_name_fallback(monkeypatch, tmp_path):
    defaults_path = tmp_path / "agent-defaults.toml"
    defaults_path.write_text(
        "\n".join(
            [
                "[[defaults]]",
                'repository = "personal_workflow_manager"',
                'issue_type = "Task"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent_defaults, "AGENT_DEFAULTS_PATH", defaults_path)

    resolution = agent_defaults.load_agent_jira_defaults(
        project_key="ABC",
        github_repo=None,
        repo_name="personal_workflow_manager",
    )

    assert resolution.overrides["issue_type"] == "Task"


def test_load_agent_jira_defaults_missing_or_malformed_is_safe(
    monkeypatch,
    tmp_path,
):
    missing_path = tmp_path / "missing.toml"
    monkeypatch.setattr(agent_defaults, "AGENT_DEFAULTS_PATH", missing_path)
    missing = agent_defaults.load_agent_jira_defaults(
        project_key="ABC",
        github_repo="org/repo",
        repo_name="repo",
    )
    assert missing.overrides == {}
    assert missing.warning is None

    malformed_path = tmp_path / "bad.toml"
    malformed_path.write_text("[[defaults]\nproject = 'ABC'", encoding="utf-8")
    monkeypatch.setattr(agent_defaults, "AGENT_DEFAULTS_PATH", malformed_path)
    malformed = agent_defaults.load_agent_jira_defaults(
        project_key="ABC",
        github_repo="org/repo",
        repo_name="repo",
    )
    assert malformed.overrides == {}
    assert malformed.warning is not None
