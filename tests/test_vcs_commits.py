
from pathlib import Path
from unittest.mock import patch, Mock
from pwm.vcs.git_cli import get_commits_since_base, push_branch


def test_get_commits_since_base():
    """Test getting commits since base branch."""
    mock_result = Mock()
    mock_result.returncode = 0
    # Simulated git log output with format markers
    mock_result.stdout = (
        "abc123\x00Add feature X\x00Detailed description\x1e"
        "def456\x00Fix bug Y\x00\x1e"
        "ghi789\x00Update docs\x00Added examples\x1e"
    )

    with patch("pwm.vcs.git_cli._run", return_value=mock_result):
        commits = get_commits_since_base(Path("/repo"), "origin/main")

        assert len(commits) == 3
        assert commits[0]["hash"] == "abc123"
        assert commits[0]["subject"] == "Add feature X"
        assert commits[0]["body"] == "Detailed description"
        assert commits[1]["hash"] == "def456"
        assert commits[1]["subject"] == "Fix bug Y"
        assert commits[1]["body"] == ""


def test_get_commits_since_base_no_commits():
    """Test when there are no commits."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = ""

    with patch("pwm.vcs.git_cli._run", return_value=mock_result):
        commits = get_commits_since_base(Path("/repo"), "origin/main")

        assert len(commits) == 0


def test_push_branch_success():
    """Test successful branch push."""
    mock_result = Mock()
    mock_result.returncode = 0

    with patch("pwm.vcs.git_cli._run", return_value=mock_result) as mock_run:
        result = push_branch(Path("/repo"), "feature-branch", "origin", set_upstream=True)

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "push" in args
        assert "-u" in args
        assert "origin" in args
        assert "feature-branch" in args


def test_push_branch_failure():
    """Test failed branch push."""
    mock_result = Mock()
    mock_result.returncode = 1

    with patch("pwm.vcs.git_cli._run", return_value=mock_result):
        result = push_branch(Path("/repo"), "feature-branch")

        assert result is False


def test_push_branch_without_upstream():
    """Test pushing without setting upstream."""
    mock_result = Mock()
    mock_result.returncode = 0

    with patch("pwm.vcs.git_cli._run", return_value=mock_result) as mock_run:
        result = push_branch(Path("/repo"), "feature-branch", set_upstream=False)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "push" in args
        assert "-u" not in args
