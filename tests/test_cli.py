from typer.testing import CliRunner

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
