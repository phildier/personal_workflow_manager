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
