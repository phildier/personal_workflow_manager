from pwm.pr.open import open_pr
from pwm.work.end import work_end
from pwm.summary.command import daily_summary


def test_open_pr_emits_debug_when_not_on_branch(monkeypatch, capsys):
    class Ctx:
        repo_root = "."
        github_repo = "org/repo"
        config = {}

    monkeypatch.setenv("PWM_DEBUG", "1")
    monkeypatch.setattr("pwm.pr.open.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.pr.open.current_branch", lambda _repo_root: None)

    assert open_pr(open_browser=False) == 1
    captured = capsys.readouterr()
    assert "[DEBUG] pr.open: current_branch returned no branch" in captured.err


def test_work_end_emits_debug_when_not_on_branch(monkeypatch, capsys):
    class Ctx:
        repo_root = "."
        github_repo = "org/repo"
        config = {}

    monkeypatch.setenv("PWM_DEBUG", "1")
    monkeypatch.setattr("pwm.work.end.resolve_context", lambda: Ctx())
    monkeypatch.setattr("pwm.work.end.current_branch", lambda _repo_root: None)

    assert work_end() == 1
    captured = capsys.readouterr()
    assert "[DEBUG] work.end: current_branch returned no branch" in captured.err


def test_daily_summary_emits_debug_when_context_fails(monkeypatch, capsys):
    monkeypatch.setenv("PWM_DEBUG", "1")
    monkeypatch.setattr(
        "pwm.summary.command.resolve_context",
        lambda: (_ for _ in ()).throw(RuntimeError("not in repo")),
    )

    assert daily_summary() == 1
    captured = capsys.readouterr()
    assert "[DEBUG] summary.command: resolve_context failed: RuntimeError" in captured.err
