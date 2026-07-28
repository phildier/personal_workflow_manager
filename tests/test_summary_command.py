"""Tests for the daily summary command."""

from datetime import datetime

from pwm.summary.command import daily_summary


def test_daily_summary_runs_outside_git_repository(
    tmp_path, monkeypatch, capsys
):
    """Daily summaries should not require a local Git repository."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "pwm.config.loader.USER_CONFIG_PATH",
        tmp_path / "missing-config.toml",
    )
    for name in (
        "PWM_JIRA_TOKEN",
        "PWM_JIRA_BASE_URL",
        "PWM_JIRA_EMAIL",
        "GITHUB_TOKEN",
        "PWM_GITHUB_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    result = daily_summary(
        since=datetime(2026, 7, 23),
        use_ai=False,
    )

    assert result == 0
    assert "Not inside a git repository" not in capsys.readouterr().out
