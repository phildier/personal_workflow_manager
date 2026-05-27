import json
import tomllib

import pwm.work.epic_history as epic_history


def test_upsert_epic_history_dedupes_and_orders_latest(monkeypatch, tmp_path):
    history_file = tmp_path / "epic_history.json"
    monkeypatch.setattr(epic_history, "EPIC_HISTORY_FILE", history_file)

    epic_history.upsert_epic_history("ABC-1", "First", "ABC")
    epic_history.upsert_epic_history("ABC-2", "Second", "ABC")
    epic_history.upsert_epic_history("ABC-1", "First updated", "ABC")

    loaded = epic_history.load_epic_history()
    assert len(loaded) == 2
    assert loaded[0]["key"] == "ABC-1"
    assert loaded[0]["title"] == "First updated"


def test_epic_history_command_json_marks_default(monkeypatch, tmp_path, capsys):
    history_file = tmp_path / "epic_history.json"
    monkeypatch.setattr(epic_history, "EPIC_HISTORY_FILE", history_file)
    history_file.write_text(
        json.dumps(
            [
                {
                    "key": "ABC-1",
                    "title": "First",
                    "project_key": "ABC",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                },
                {
                    "key": "XYZ-9",
                    "title": "Other",
                    "project_key": "XYZ",
                    "updated_at": "2026-01-02T00:00:00+00:00",
                },
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        epic_history,
        "_get_repo_default_parent_epic_key",
        lambda: "ABC-1",
    )

    rc = epic_history.epic_history_command(project="ABC", as_json=True)
    assert rc == 0

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert len(payload) == 1
    assert payload[0]["key"] == "ABC-1"
    assert payload[0]["is_default"] is True


def test_epic_history_clear_with_yes(monkeypatch, tmp_path):
    history_file = tmp_path / "epic_history.json"
    monkeypatch.setattr(epic_history, "EPIC_HISTORY_FILE", history_file)
    history_file.write_text("[]", encoding="utf-8")

    rc = epic_history.epic_history_command(clear=True, yes=True)
    assert rc == 0
    assert not history_file.exists()


def test_set_default_uses_cached_epic_without_jira_lookup(monkeypatch, tmp_path):
    history_file = tmp_path / "epic_history.json"
    monkeypatch.setattr(epic_history, "EPIC_HISTORY_FILE", history_file)
    history_file.write_text(
        json.dumps(
            [
                {
                    "key": "ABC-1",
                    "title": "Cached epic",
                    "project_key": "ABC",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    class Ctx:
        repo_root = tmp_path
        config = {}

    monkeypatch.setattr(epic_history, "resolve_context", lambda: Ctx())
    monkeypatch.setattr(
        epic_history,
        "_lookup_epic_in_jira",
        lambda _key: (_ for _ in ()).throw(
            AssertionError("Jira lookup should not run for cached epic")
        ),
    )

    rc = epic_history.epic_history_command(set_default="ABC-1")
    assert rc == 0

    with (tmp_path / ".pwm.toml").open("rb") as file_obj:
        config = tomllib.load(file_obj)

    assert config["jira"]["issue_defaults"]["parent_epic_key"] == "ABC-1"


def test_set_default_fetches_missing_epic_from_jira(monkeypatch, tmp_path):
    history_file = tmp_path / "epic_history.json"
    monkeypatch.setattr(epic_history, "EPIC_HISTORY_FILE", history_file)

    class Ctx:
        repo_root = tmp_path
        config = {"jira": {"base_url": "x", "email": "x", "token": "x"}}

    class FakeJira:
        def get_issue(self, key):
            if key != "ABC-9":
                return None
            return {
                "fields": {
                    "summary": "Fetched epic",
                    "issuetype": {"name": "Epic"},
                    "project": {"key": "ABC"},
                }
            }

    monkeypatch.setattr(epic_history, "resolve_context", lambda: Ctx())
    monkeypatch.setattr(
        epic_history.JiraClient,
        "from_config",
        classmethod(lambda cls, _cfg: FakeJira()),
    )

    rc = epic_history.epic_history_command(set_default="ABC-9")
    assert rc == 0

    loaded = epic_history.load_epic_history()
    assert loaded[0]["key"] == "ABC-9"
    assert loaded[0]["title"] == "Fetched epic"


def test_clear_default_removes_value(monkeypatch, tmp_path):
    class Ctx:
        repo_root = tmp_path
        config = {}

    config_path = tmp_path / ".pwm.toml"
    config_path.write_text(
        "[jira.issue_defaults]\nissue_type = \"Story\"\n"
        "parent_epic_key = \"ABC-3\"\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(epic_history, "resolve_context", lambda: Ctx())

    rc = epic_history.epic_history_command(clear_default=True)
    assert rc == 0

    with config_path.open("rb") as file_obj:
        config = tomllib.load(file_obj)

    assert config["jira"]["issue_defaults"].get("parent_epic_key") is None
