"""Data collection orchestration for work summary."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pwm.github.client import GitHubClient
from pwm.jira.client import JiraClient


@dataclass
class WorkSummaryData:
    """Container for collected work summary data."""
    prs_opened: list[dict]
    prs_closed: list[dict]
    prs_merged: list[dict]
    jira_created: list[dict]
    jira_updated: list[dict]
    start_time: datetime
    end_time: datetime


def collect_work_data(
    github_repo: Optional[str],
    jira_project: Optional[str],
    since: datetime,
    github_client: Optional[GitHubClient],
    jira_client: Optional[JiraClient],
    config: dict
) -> WorkSummaryData:
    """
    Collect all work data from GitHub and Jira.

    Handles graceful degradation when services are not configured.

    Args:
        github_repo: GitHub repository in "owner/repo" format (None if not configured)
        jira_project: Jira project key (None if not configured)
        since: Start datetime for the summary period
        github_client: GitHub client instance (None if not configured)
        jira_client: Jira client instance (None if not configured)
        config: PWM configuration dict

    Returns:
        WorkSummaryData with all collected information
    """
    end_time = datetime.now()

    # Get configuration
    summary_config = config.get("daily_summary", {})
    include_own_prs = summary_config.get("include_own_prs_only", True)
    include_own_issues = summary_config.get("include_own_issues_only", True)
    github_org = summary_config.get("github_org")
    jira_projects = summary_config.get("jira_projects")

    # Collect GitHub PRs
    prs_opened = []
    prs_closed = []
    prs_merged = []

    if github_client:
        # Get current user if filtering by author
        github_user = None
        if include_own_prs:
            github_user = github_client.get_current_user()

        # Determine search scope: org-wide or specific repo
        if github_org:
            # Search across all repos in org
            prs_opened = github_client.search_prs_by_date(
                repo=None,
                since=since,
                author=github_user,
                state="all",
                org=github_org
            )

            all_closed = github_client.get_closed_prs(
                repo=None,
                since=since,
                author=github_user,
                org=github_org
            )
        elif github_repo:
            # Search specific repo
            prs_opened = github_client.search_prs_by_date(
                repo=github_repo,
                since=since,
                author=github_user,
                state="all"
            )

            all_closed = github_client.get_closed_prs(
                repo=github_repo,
                since=since,
                author=github_user
            )
        else:
            all_closed = []

        # Separate closed vs merged
        for pr in all_closed:
            if pr.get("merged_at"):
                prs_merged.append(pr)
            else:
                prs_closed.append(pr)

    # Collect Jira issues
    jira_created = []
    jira_updated = []

    if jira_client:
        # Use currentUser() JQL function if filtering by assignee
        assignee = "currentUser()" if include_own_issues else None

        # Determine search scope: multiple projects or single project
        projects_to_search = jira_projects if jira_projects else (jira_project if jira_project else None)

        if projects_to_search:
            jira_created = jira_client.get_issues_created_since(
                projects_to_search,
                since,
                assignee=assignee
            )

            jira_updated = jira_client.get_issues_updated_since(
                projects_to_search,
                since,
                assignee=assignee
            )

    return WorkSummaryData(
        prs_opened=prs_opened,
        prs_closed=prs_closed,
        prs_merged=prs_merged,
        jira_created=jira_created,
        jira_updated=jira_updated,
        start_time=since,
        end_time=end_time
    )
