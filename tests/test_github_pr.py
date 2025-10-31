
import httpx
from unittest.mock import Mock, patch
from pwm.github.client import GitHubClient


def test_list_prs_success():
    """Test listing pull requests."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"number": 1, "title": "Test PR", "state": "open"},
        {"number": 2, "title": "Another PR", "state": "open"}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        prs = client.list_prs("owner/repo", state="open")

        assert len(prs) == 2
        assert prs[0]["number"] == 1
        assert prs[1]["title"] == "Another PR"


def test_list_prs_with_head_filter():
    """Test listing PRs filtered by head branch."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"number": 1, "title": "Test PR", "head": {"ref": "feature-branch"}}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        prs = client.list_prs("owner/repo", head="owner:feature-branch")

        assert len(prs) == 1
        assert prs[0]["number"] == 1


def test_create_pr_success():
    """Test creating a pull request."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "number": 42,
        "html_url": "https://github.com/owner/repo/pull/42",
        "title": "Test PR"
    }

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        pr = client.create_pr(
            repo="owner/repo",
            title="Test PR",
            head="feature-branch",
            base="main",
            body="Test description"
        )

        assert pr is not None
        assert pr["number"] == 42
        assert pr["html_url"] == "https://github.com/owner/repo/pull/42"


def test_create_pr_failure():
    """Test PR creation failure."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 422  # Unprocessable Entity

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        pr = client.create_pr(
            repo="owner/repo",
            title="Test PR",
            head="feature-branch",
            base="main"
        )

        assert pr is None


def test_get_pr_for_branch_exists():
    """Test getting PR for a specific branch when it exists."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"number": 1, "title": "Test PR", "head": {"ref": "feature-branch"}}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        pr = client.get_pr_for_branch("owner/repo", "feature-branch")

        assert pr is not None
        assert pr["number"] == 1


def test_get_pr_for_branch_not_exists():
    """Test getting PR for a branch when none exists."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        pr = client.get_pr_for_branch("owner/repo", "feature-branch")

        assert pr is None


def test_get_pr_for_branch_all_states():
    """Test getting PR for a branch including closed PRs."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"number": 42, "title": "Test PR", "state": "closed", "head": {"ref": "feature-branch"}}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        pr = client.get_pr_for_branch("owner/repo", "feature-branch", state="all")

        assert pr is not None
        assert pr["number"] == 42
        assert pr["state"] == "closed"


def test_get_pr_for_branch_defaults_to_open():
    """Test that get_pr_for_branch defaults to open PRs only."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"number": 1, "title": "Open PR", "state": "open"}
    ]

    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value
        mock_instance.get.return_value = mock_response

        # Call without state parameter (should default to "open")
        pr = client.get_pr_for_branch("owner/repo", "feature-branch")

        assert pr is not None
        # Verify the API was called with state="open"
        call_args = mock_instance.get.call_args
        assert call_args[1]["params"]["state"] == "open"


def test_get_pr_details():
    """Test getting detailed PR information."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "number": 42,
        "title": "Test PR",
        "changed_files": 3,
        "additions": 150,
        "deletions": 25
    }

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        details = client.get_pr_details("owner/repo", 42)

        assert details is not None
        assert details["number"] == 42
        assert details["changed_files"] == 3
        assert details["additions"] == 150
        assert details["deletions"] == 25


def test_get_pr_reviews():
    """Test getting PR reviews."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"user": {"login": "reviewer1"}, "state": "APPROVED"},
        {"user": {"login": "reviewer2"}, "state": "COMMENTED"}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        reviews = client.get_pr_reviews("owner/repo", 42)

        assert len(reviews) == 2
        assert reviews[0]["user"]["login"] == "reviewer1"
        assert reviews[0]["state"] == "APPROVED"
        assert reviews[1]["user"]["login"] == "reviewer2"
        assert reviews[1]["state"] == "COMMENTED"
