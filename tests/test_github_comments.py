
from unittest.mock import Mock, patch
from datetime import datetime
from pwm.github.client import GitHubClient


def test_get_pr_comments_success():
    """Test getting PR comments."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "body": "First comment", "created_at": "2024-01-01T00:00:00Z"},
        {"id": 2, "body": "Second comment", "created_at": "2024-01-02T00:00:00Z"}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        comments = client.get_pr_comments("owner/repo", 123)

        assert len(comments) == 2
        assert comments[0]["body"] == "First comment"
        assert comments[1]["body"] == "Second comment"


def test_add_pr_comment_success():
    """Test adding a comment to PR."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 123,
        "body": "Test comment",
        "created_at": "2024-01-01T00:00:00Z"
    }

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        comment = client.add_pr_comment("owner/repo", 42, "Test comment")

        assert comment is not None
        assert comment["id"] == 123
        assert comment["body"] == "Test comment"


def test_add_pr_comment_failure():
    """Test PR comment failure."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 403  # Forbidden

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        comment = client.add_pr_comment("owner/repo", 42, "Test comment")

        assert comment is None


def test_request_reviewers_success():
    """Test requesting reviewers."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 201

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = client.request_reviewers(
            "owner/repo",
            42,
            reviewers=["user1", "user2"],
            team_reviewers=["team1"]
        )

        assert result is True


def test_request_reviewers_no_reviewers():
    """Test requesting reviewers with no reviewers specified."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    result = client.request_reviewers("owner/repo", 42)

    assert result is False


def test_request_reviewers_failure():
    """Test reviewer request failure."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 422  # Unprocessable

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = client.request_reviewers("owner/repo", 42, reviewers=["user1"])

        assert result is False


def test_get_last_pwm_comment_time_no_comments():
    """Test getting last pwm comment time when there are no comments."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        result = client.get_last_pwm_comment_time("owner/repo", 42)

        assert result is None


def test_get_last_pwm_comment_time_no_pwm_comments():
    """Test getting last pwm comment time when there are no pwm comments."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "body": "Regular comment", "created_at": "2024-01-01T00:00:00Z"},
        {"id": 2, "body": "Another comment", "created_at": "2024-01-02T00:00:00Z"}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        result = client.get_last_pwm_comment_time("owner/repo", 42)

        assert result is None


def test_get_last_pwm_comment_time_with_pwm_comments():
    """Test getting last pwm comment time when there are pwm comments."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "body": "Regular comment", "created_at": "2024-01-01T00:00:00Z"},
        {"id": 2, "body": "<!-- pwm:work-end -->\n**Status Update**\n\nFirst update", "created_at": "2024-01-02T10:00:00Z"},
        {"id": 3, "body": "Another regular comment", "created_at": "2024-01-03T00:00:00Z"},
        {"id": 4, "body": "<!-- pwm:work-end -->\n**Status Update**\n\nSecond update", "created_at": "2024-01-04T15:30:00Z"}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        result = client.get_last_pwm_comment_time("owner/repo", 42)

        assert result is not None
        # Should return the most recent pwm comment time (2024-01-04T15:30:00Z)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 4
        assert result.hour == 15
        assert result.minute == 30


def test_get_last_pwm_comment_time_invalid_timestamp():
    """Test handling invalid timestamp in pwm comment."""
    client = GitHubClient(base_url="https://api.github.com", token="test-token")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "body": "<!-- pwm:work-end -->\n**Status Update**\n\nUpdate", "created_at": "invalid-date"},
        {"id": 2, "body": "<!-- pwm:work-end -->\n**Status Update**\n\nValid update", "created_at": "2024-01-05T12:00:00Z"}
    ]

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        result = client.get_last_pwm_comment_time("owner/repo", 42)

        # Should skip the invalid timestamp and return the valid one
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 5
