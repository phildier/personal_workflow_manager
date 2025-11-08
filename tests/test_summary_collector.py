"""Tests for work summary data collection."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from pwm.summary.collector import collect_work_data, WorkSummaryData


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = Mock()
    client.get_current_user.return_value = "testuser"
    client.search_prs_by_date.return_value = [
        {"number": 1, "title": "PR 1", "state": "open"},
        {"number": 2, "title": "PR 2", "state": "open"}
    ]
    client.get_closed_prs.return_value = [
        {"number": 3, "title": "Closed PR", "merged_at": None},
        {"number": 4, "title": "Merged PR", "merged_at": "2025-01-11T10:00:00Z"}
    ]
    return client


@pytest.fixture
def mock_jira_client():
    """Create a mock Jira client."""
    client = Mock()
    client.get_issues_created_since.return_value = [
        {"key": "ABC-1", "summary": "New issue"}
    ]
    client.get_issues_updated_since.return_value = [
        {"key": "ABC-5", "summary": "Updated issue"}
    ]
    return client


class TestCollectWorkData:
    """Tests for collect_work_data function."""

    def test_collects_github_and_jira_data(self, mock_github_client, mock_jira_client):
        """Should collect data from both GitHub and Jira."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {
            "daily_summary": {
                "include_own_prs_only": True,
                "include_own_issues_only": True
            }
        }

        result = collect_work_data(
            github_repo="org/repo",
            jira_project="ABC",
            since=since,
            github_client=mock_github_client,
            jira_client=mock_jira_client,
            config=config
        )

        assert isinstance(result, WorkSummaryData)
        assert len(result.prs_opened) == 2
        assert len(result.prs_closed) == 1
        assert len(result.prs_merged) == 1
        assert len(result.jira_created) == 1
        assert len(result.jira_updated) == 1
        assert result.start_time == since
        assert isinstance(result.end_time, datetime)

    def test_filters_by_current_user_when_configured(self, mock_github_client, mock_jira_client):
        """Should filter by current user when include_own_*_only is True."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {
            "daily_summary": {
                "include_own_prs_only": True,
                "include_own_issues_only": True
            }
        }

        collect_work_data(
            github_repo="org/repo",
            jira_project="ABC",
            since=since,
            github_client=mock_github_client,
            jira_client=mock_jira_client,
            config=config
        )

        # Should get current user
        mock_github_client.get_current_user.assert_called_once()

        # Should pass user to PR search
        mock_github_client.search_prs_by_date.assert_called_once_with(
            "org/repo",
            since,
            author="testuser",
            state="all"
        )

        mock_github_client.get_closed_prs.assert_called_once_with(
            "org/repo",
            since,
            author="testuser"
        )

        # Should pass currentUser() to Jira
        mock_jira_client.get_issues_created_since.assert_called_once_with(
            "ABC",
            since,
            assignee="currentUser()"
        )

        mock_jira_client.get_issues_updated_since.assert_called_once_with(
            "ABC",
            since,
            assignee="currentUser()"
        )

    def test_does_not_filter_when_configured(self, mock_github_client, mock_jira_client):
        """Should not filter by user when include_own_*_only is False."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {
            "daily_summary": {
                "include_own_prs_only": False,
                "include_own_issues_only": False
            }
        }

        collect_work_data(
            github_repo="org/repo",
            jira_project="ABC",
            since=since,
            github_client=mock_github_client,
            jira_client=mock_jira_client,
            config=config
        )

        # Should NOT get current user
        mock_github_client.get_current_user.assert_not_called()

        # Should pass None for author
        mock_github_client.search_prs_by_date.assert_called_once_with(
            "org/repo",
            since,
            author=None,
            state="all"
        )

        mock_github_client.get_closed_prs.assert_called_once_with(
            "org/repo",
            since,
            author=None
        )

        # Should pass None for assignee
        mock_jira_client.get_issues_created_since.assert_called_once_with(
            "ABC",
            since,
            assignee=None
        )

        mock_jira_client.get_issues_updated_since.assert_called_once_with(
            "ABC",
            since,
            assignee=None
        )

    def test_handles_missing_github_client(self, mock_jira_client):
        """Should handle gracefully when GitHub is not configured."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {"daily_summary": {}}

        result = collect_work_data(
            github_repo=None,
            jira_project="ABC",
            since=since,
            github_client=None,
            jira_client=mock_jira_client,
            config=config
        )

        # Should have empty PR lists
        assert result.prs_opened == []
        assert result.prs_closed == []
        assert result.prs_merged == []

        # Should still have Jira data
        assert len(result.jira_created) == 1
        assert len(result.jira_updated) == 1

    def test_handles_missing_jira_client(self, mock_github_client):
        """Should handle gracefully when Jira is not configured."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {"daily_summary": {}}

        result = collect_work_data(
            github_repo="org/repo",
            jira_project=None,
            since=since,
            github_client=mock_github_client,
            jira_client=None,
            config=config
        )

        # Should have PR data
        assert len(result.prs_opened) == 2

        # Should have empty Jira lists
        assert result.jira_created == []
        assert result.jira_updated == []

    def test_handles_no_services_configured(self):
        """Should handle gracefully when neither service is configured."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {"daily_summary": {}}

        result = collect_work_data(
            github_repo=None,
            jira_project=None,
            since=since,
            github_client=None,
            jira_client=None,
            config=config
        )

        # Should have all empty lists
        assert result.prs_opened == []
        assert result.prs_closed == []
        assert result.prs_merged == []
        assert result.jira_created == []
        assert result.jira_updated == []
        assert result.start_time == since
        assert isinstance(result.end_time, datetime)

    def test_separates_closed_and_merged_prs(self, mock_github_client, mock_jira_client):
        """Should correctly separate closed vs merged PRs."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {"daily_summary": {}}

        # Mock with multiple closed PRs
        mock_github_client.get_closed_prs.return_value = [
            {"number": 1, "title": "Just closed", "merged_at": None},
            {"number": 2, "title": "Merged PR 1", "merged_at": "2025-01-11T10:00:00Z"},
            {"number": 3, "title": "Another closed", "merged_at": None},
            {"number": 4, "title": "Merged PR 2", "merged_at": "2025-01-11T11:00:00Z"}
        ]

        result = collect_work_data(
            github_repo="org/repo",
            jira_project="ABC",
            since=since,
            github_client=mock_github_client,
            jira_client=mock_jira_client,
            config=config
        )

        assert len(result.prs_closed) == 2
        assert len(result.prs_merged) == 2
        assert result.prs_closed[0]["title"] == "Just closed"
        assert result.prs_closed[1]["title"] == "Another closed"
        assert result.prs_merged[0]["title"] == "Merged PR 1"
        assert result.prs_merged[1]["title"] == "Merged PR 2"

    def test_uses_default_config_values(self, mock_github_client, mock_jira_client):
        """Should use default values when config is missing daily_summary section."""
        since = datetime(2025, 1, 10, 0, 0)
        config = {}  # No daily_summary config

        result = collect_work_data(
            github_repo="org/repo",
            jira_project="ABC",
            since=since,
            github_client=mock_github_client,
            jira_client=mock_jira_client,
            config=config
        )

        # Should default to include_own_*_only = True
        mock_github_client.get_current_user.assert_called_once()
        mock_jira_client.get_issues_created_since.assert_called_once()
        call_args = mock_jira_client.get_issues_created_since.call_args
        assert call_args[1]["assignee"] == "currentUser()"
