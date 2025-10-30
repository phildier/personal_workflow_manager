
import types
from pathlib import Path
from pwm.vcs import git_cli

def test_infer_github_repo_from_remote_ssh(monkeypatch, tmp_path):
    repo = tmp_path
    (repo / ".git").mkdir()
    def fake_run(args, repo_root: Path, capture: bool=True):
        return types.SimpleNamespace(returncode=0, stdout="git@github.com:org/repo.git")
    monkeypatch.setattr(git_cli, "_run", fake_run)
    assert git_cli.infer_github_repo_from_remote(repo) == "org/repo"

def test_infer_github_repo_from_remote_https(monkeypatch, tmp_path):
    repo = tmp_path
    (repo / ".git").mkdir()
    def fake_run(args, repo_root: Path, capture: bool=True):
        return types.SimpleNamespace(returncode=0, stdout="https://github.com/org/repo.git")
    monkeypatch.setattr(git_cli, "_run", fake_run)
    assert git_cli.infer_github_repo_from_remote(repo) == "org/repo"
