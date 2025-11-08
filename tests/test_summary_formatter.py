"""Tests for work summary formatting."""

from datetime import datetime

import pytest

from pwm.summary.collector import WorkSummaryData
from pwm.summary.formatter import format_markdown, format_text


@pytest.fixture
def sample_data():
    """Create sample work summary data for testing."""
    return WorkSummaryData(
        prs_opened=[
            {"number": 1, "title": "Add new feature", "html_url": "https://github.com/org/repo/pull/1"},
            {"number": 2, "title": "Fix bug in auth", "html_url": "https://github.com/org/repo/pull/2"}
        ],
        prs_closed=[
            {"number": 3, "title": "Old PR closed", "html_url": "https://github.com/org/repo/pull/3"}
        ],
        prs_merged=[
            {"number": 4, "title": "Merged feature", "html_url": "https://github.com/org/repo/pull/4"},
            {"number": 5, "title": "Another merge", "html_url": "https://github.com/org/repo/pull/5"}
        ],
        jira_created=[
            {"key": "ABC-1", "summary": "New task for feature"},
            {"key": "ABC-2", "summary": "Bug report"}
        ],
        jira_updated=[
            {"key": "ABC-5", "summary": "Old task", "status": {"name": "In Progress"}},
            {"key": "ABC-6", "summary": "Another task", "status": {"name": "Done"}}
        ],
        start_time=datetime(2025, 1, 10, 0, 0),
        end_time=datetime(2025, 1, 13, 12, 0)
    )


@pytest.fixture
def empty_data():
    """Create empty work summary data."""
    return WorkSummaryData(
        prs_opened=[],
        prs_closed=[],
        prs_merged=[],
        jira_created=[],
        jira_updated=[],
        start_time=datetime(2025, 1, 10, 0, 0),
        end_time=datetime(2025, 1, 13, 12, 0)
    )


class TestFormatMarkdown:
    """Tests for format_markdown function."""

    def test_includes_header_and_period(self, sample_data):
        """Should include title and date range."""
        result = format_markdown(sample_data)

        assert "# Daily Work Summary" in result
        assert "**Period:**" in result
        assert "Friday, Jan 10 2025" in result
        assert "Monday, Jan 13 2025" in result

    def test_formats_opened_prs(self, sample_data):
        """Should format opened PRs with markdown links."""
        result = format_markdown(sample_data)

        assert "## Pull Requests" in result
        assert "### Opened (2)" in result
        assert "[#1](https://github.com/org/repo/pull/1) Add new feature" in result
        assert "[#2](https://github.com/org/repo/pull/2) Fix bug in auth" in result

    def test_formats_merged_prs(self, sample_data):
        """Should format merged PRs."""
        result = format_markdown(sample_data)

        assert "### Merged (2)" in result
        assert "[#4](https://github.com/org/repo/pull/4) Merged feature" in result
        assert "[#5](https://github.com/org/repo/pull/5) Another merge" in result

    def test_formats_closed_prs(self, sample_data):
        """Should format closed PRs."""
        result = format_markdown(sample_data)

        assert "### Closed (1)" in result
        assert "[#3](https://github.com/org/repo/pull/3) Old PR closed" in result

    def test_formats_created_jira_issues(self, sample_data):
        """Should format created Jira issues."""
        result = format_markdown(sample_data)

        assert "## Jira Issues" in result
        assert "### Created (2)" in result
        assert "- ABC-1: New task for feature" in result
        assert "- ABC-2: Bug report" in result

    def test_formats_updated_jira_issues(self, sample_data):
        """Should format updated Jira issues with status."""
        result = format_markdown(sample_data)

        assert "### Updated (2)" in result
        assert "- ABC-5: Old task → In Progress" in result
        assert "- ABC-6: Another task → Done" in result

    def test_includes_ai_summary_at_top(self, sample_data):
        """Should include AI summary at the top if provided."""
        ai_summary = "Made significant progress on authentication and new features."
        result = format_markdown(sample_data, ai_summary=ai_summary)

        assert "## Summary" in result
        assert ai_summary in result
        # Summary should come before Pull Requests
        summary_pos = result.index("## Summary")
        pr_pos = result.index("## Pull Requests")
        assert summary_pos < pr_pos

    def test_handles_empty_data(self, empty_data):
        """Should handle empty data gracefully."""
        result = format_markdown(empty_data)

        assert "# Daily Work Summary" in result
        assert "No work activity found for this period" in result
        assert "## Pull Requests" not in result
        assert "## Jira Issues" not in result

    def test_handles_missing_html_url(self):
        """Should handle PRs without html_url."""
        data = WorkSummaryData(
            prs_opened=[{"number": 1, "title": "Test PR"}],
            prs_closed=[],
            prs_merged=[],
            jira_created=[],
            jira_updated=[],
            start_time=datetime(2025, 1, 10, 0, 0),
            end_time=datetime(2025, 1, 13, 12, 0)
        )

        result = format_markdown(data)
        assert "- #1 Test PR" in result

    def test_handles_only_prs(self):
        """Should format correctly with only PR data."""
        data = WorkSummaryData(
            prs_opened=[{"number": 1, "title": "Test", "html_url": "https://example.com"}],
            prs_closed=[],
            prs_merged=[],
            jira_created=[],
            jira_updated=[],
            start_time=datetime(2025, 1, 10, 0, 0),
            end_time=datetime(2025, 1, 13, 12, 0)
        )

        result = format_markdown(data)
        assert "## Pull Requests" in result
        assert "## Jira Issues" not in result

    def test_handles_only_jira(self):
        """Should format correctly with only Jira data."""
        data = WorkSummaryData(
            prs_opened=[],
            prs_closed=[],
            prs_merged=[],
            jira_created=[{"key": "ABC-1", "summary": "Test"}],
            jira_updated=[],
            start_time=datetime(2025, 1, 10, 0, 0),
            end_time=datetime(2025, 1, 13, 12, 0)
        )

        result = format_markdown(data)
        assert "## Jira Issues" in result
        assert "## Pull Requests" not in result


class TestFormatText:
    """Tests for format_text function."""

    def test_includes_header_and_period(self, sample_data):
        """Should include title and date range in text format."""
        result = format_text(sample_data)

        assert "DAILY WORK SUMMARY" in result
        assert "=" * 60 in result
        assert "Period:" in result
        assert "Friday, Jan 10 2025" in result

    def test_formats_pull_requests(self, sample_data):
        """Should format pull requests in text format."""
        result = format_text(sample_data)

        assert "PULL REQUESTS" in result
        assert "Opened (2):" in result
        assert "  • #1 Add new feature" in result
        assert "Merged (2):" in result
        assert "  • #4 Merged feature" in result
        assert "Closed (1):" in result
        assert "  • #3 Old PR closed" in result

    def test_formats_jira_issues(self, sample_data):
        """Should format Jira issues in text format."""
        result = format_text(sample_data)

        assert "JIRA ISSUES" in result
        assert "Created (2):" in result
        assert "  • ABC-1: New task for feature" in result
        assert "Updated (2):" in result
        assert "  • ABC-5: Old task → In Progress" in result

    def test_includes_ai_summary(self, sample_data):
        """Should include AI summary in text format."""
        ai_summary = "Good progress on features."
        result = format_text(sample_data, ai_summary=ai_summary)

        assert "SUMMARY" in result
        assert ai_summary in result

    def test_handles_empty_data(self, empty_data):
        """Should handle empty data gracefully in text format."""
        result = format_text(empty_data)

        assert "DAILY WORK SUMMARY" in result
        assert "No work activity found for this period" in result
        assert "PULL REQUESTS" not in result
        assert "JIRA ISSUES" not in result

    def test_uses_bullet_points(self, sample_data):
        """Should use bullet points (•) for list items."""
        result = format_text(sample_data)

        assert "  • #1 Add new feature" in result
        assert "  • ABC-1: New task for feature" in result

    def test_uses_separators(self, sample_data):
        """Should use dashes for section separators."""
        result = format_text(sample_data)

        assert "-" * 60 in result
