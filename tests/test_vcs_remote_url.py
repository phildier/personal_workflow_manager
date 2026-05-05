from pwm.vcs.remote_url import parse_repo_from_remote_url


def test_parse_repo_from_remote_url_ssh():
    assert parse_repo_from_remote_url("git@github.com:org/repo.git") == "org/repo"


def test_parse_repo_from_remote_url_https():
    assert parse_repo_from_remote_url("https://github.com/org/repo.git") == "org/repo"


def test_parse_repo_from_remote_url_invalid():
    assert parse_repo_from_remote_url("file:///tmp/repo") is None
