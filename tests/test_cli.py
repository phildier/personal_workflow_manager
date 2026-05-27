from typer.testing import CliRunner
from datetime import datetime

from pwm.cli import app


runner = CliRunner()


def test_root_no_args_shows_help():
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "Personal Workflow Manager" in result.stdout


def test_ws_no_args_shows_command_help_without_error(monkeypatch):
    called = False

    def fake_work_start(**kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr("pwm.cli.work_start", fake_work_start)

    result = runner.invoke(app, ["ws"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "ws" in result.stdout
    assert "--new" in result.stdout
    assert not called


def test_daily_summary_since_date_defaults_to_midnight(monkeypatch):
    captured_since = None

    def fake_daily_summary(**kwargs):
        nonlocal captured_since
        captured_since = kwargs.get("since")
        return 0

    monkeypatch.setattr("pwm.cli.daily_summary", fake_daily_summary)

    result = runner.invoke(app, ["daily-summary", "--since", "2026-05-01"])

    assert result.exit_code == 0
    assert captured_since == datetime(2026, 5, 1, 0, 0)


def test_daily_summary_since_datetime_still_parses(monkeypatch):
    captured_since = None

    def fake_daily_summary(**kwargs):
        nonlocal captured_since
        captured_since = kwargs.get("since")
        return 0

    monkeypatch.setattr("pwm.cli.daily_summary", fake_daily_summary)

    result = runner.invoke(app, ["daily-summary", "--since", "2026-05-01 01:23"])

    assert result.exit_code == 0
    assert captured_since == datetime(2026, 5, 1, 1, 23)


def test_daily_summary_since_invalid_format_shows_error(monkeypatch):
    def fake_daily_summary(**kwargs):
        return 0

    monkeypatch.setattr("pwm.cli.daily_summary", fake_daily_summary)

    result = runner.invoke(app, ["daily-summary", "--since", "05/01/2026"])

    assert result.exit_code == 1
    assert "Invalid date format" in result.stdout
    assert "YYYY-MM-DD or YYYY-MM-DD HH:MM" in result.stdout


def test_ws_non_interactive_new_passes_args(monkeypatch):
    captured = {}
    logged = []

    def fake_work_start(**kwargs):
        nonlocal captured
        captured = kwargs
        return 0

    monkeypatch.setattr("pwm.cli.work_start", fake_work_start)
    monkeypatch.setattr(
        "pwm.cli.append_event",
        lambda command, args, details: logged.append(
            {"command": command, "args": args, "details": details}
        ),
    )

    result = runner.invoke(
        app,
        [
            "ws",
            "--new",
            "--non-interactive",
            "--summary",
            "CLI created issue",
            "--description",
            "Desc",
            "--issue-type",
            "Task",
            "--labels",
            "backend,api",
            "--story-points",
            "5",
            "--epic",
            "ABC-999",
            "--custom-field",
            "customfield_123=value",
            "--save-defaults",
        ],
    )

    assert result.exit_code == 0
    assert captured["create_new"] is True
    assert captured["non_interactive"] is True
    assert captured["summary"] == "CLI created issue"
    assert captured["description"] == "Desc"
    assert captured["issue_type"] == "Task"
    assert captured["labels"] == ["backend", "api"]
    assert captured["story_points"] == 5.0
    assert captured["epic"] == "ABC-999"
    assert captured["custom_fields"] == {"customfield_123": "value"}
    assert captured["save_defaults"] is True
    assert logged
    assert logged[0]["command"] == "ws"
    assert logged[0]["details"]["status"] == "success"


def test_ws_rejects_conflicting_save_default_flags(monkeypatch):
    monkeypatch.setattr("pwm.cli.work_start", lambda **kwargs: 0)

    result = runner.invoke(
        app,
        ["ws", "--new", "--save-defaults", "--no-save-defaults"],
    )

    assert result.exit_code == 2


def test_pr_passes_non_interactive_flags(monkeypatch):
    captured = {}
    logged = []

    def fake_open_pr(**kwargs):
        nonlocal captured
        captured = kwargs
        return 0

    monkeypatch.setattr("pwm.cli.open_pr", fake_open_pr)
    monkeypatch.setattr(
        "pwm.cli.append_event",
        lambda command, args, details: logged.append(
            {"command": command, "args": args, "details": details}
        ),
    )

    result = runner.invoke(
        app,
        [
            "pr",
            "--no-ai",
            "--create-anyway",
            "--no-open-browser",
            "--title",
            "Manual title",
            "--body",
            "Manual body",
            "--label",
            "bug",
            "--label",
            "ai-assisted",
            "--label",
            "bug",
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert captured["use_ai"] is False
    assert captured["create_anyway"] is True
    assert captured["open_browser"] is False
    assert captured["title_override"] == "Manual title"
    assert captured["body_override"] == "Manual body"
    assert captured["labels"] == ["bug", "ai-assisted"]
    assert captured["non_interactive"] is True
    assert logged
    assert logged[0]["command"] == "pr"


def test_epic_history_passes_options(monkeypatch):
    captured = {}

    def fake_epic_history_command(**kwargs):
        nonlocal captured
        captured = kwargs
        return 0

    monkeypatch.setattr("pwm.cli.epic_history_command", fake_epic_history_command)

    result = runner.invoke(
        app,
        [
            "epic-history",
            "--project",
            "ABC",
            "--limit",
            "25",
            "--json",
            "--clear",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "project": "ABC",
        "limit": 25,
        "as_json": True,
        "clear": True,
        "yes": True,
        "set_default": None,
        "clear_default": False,
    }


def test_epic_history_set_default_passes_args(monkeypatch):
    captured = {}

    def fake_epic_history_command(**kwargs):
        nonlocal captured
        captured = kwargs
        return 0

    monkeypatch.setattr("pwm.cli.epic_history_command", fake_epic_history_command)

    result = runner.invoke(app, ["epic-history", "--set-default", "ABC-123"])

    assert result.exit_code == 0
    assert captured["set_default"] == "ABC-123"
    assert captured["clear_default"] is False
