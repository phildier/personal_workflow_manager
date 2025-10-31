
from __future__ import annotations
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich import print as rprint

from pwm.context.resolver import resolve_context
from pwm.vcs.git_cli import current_branch, get_commits_since_base
from pwm.github.client import GitHubClient
from pwm.jira.client import JiraClient
from pwm.prompt.command import extract_issue_key_from_branch


def get_commits_since_timestamp(
    repo_root: Path,
    since: Optional[datetime],
    base_branch: Optional[str] = None
) -> list[dict]:
    """
    Get commits since a specific timestamp.

    If since is None, returns all commits since base branch.
    """
    all_commits = get_commits_since_base(repo_root, base_branch)

    if since is None:
        return all_commits

    # Filter commits by timestamp
    # Note: This is simplified - in production you'd use git log --since
    # For now, return all commits if we have a timestamp
    # (git commit objects don't include timestamps in our current implementation)
    return all_commits


def generate_work_summary(commits: list[dict]) -> str:
    """
    Generate a concise 1-2 sentence summary of changes.

    Args:
        commits: List of commit objects with 'subject' and 'body' keys

    Returns a 1-2 sentence summary
    """
    if not commits:
        return "No new changes since last update."

    commit_count = len(commits)

    # Extract key topics from commit messages
    subjects = [c["subject"] for c in commits]

    # Simple heuristic: take first commit subject as main change
    if commit_count == 1:
        return f"{subjects[0]}."

    # For multiple commits, provide count and first subject
    first_subject = subjects[0]
    return f"{first_subject} and {commit_count - 1} other change{'s' if commit_count > 2 else ''}."


def work_end(
    message: Optional[str] = None,
    no_comment: bool = False,
    no_pr_comment: bool = False,
    no_jira_comment: bool = False,
    request_review: bool = False
) -> int:
    """
    Mark work as complete with status update.

    Workflow:
    1. Check we're on a work branch
    2. Check PR exists
    3. Get new commits since last comment
    4. Generate summary
    5. Comment on PR and Jira
    6. Optionally request reviewers

    Returns 0 on success, 1 on error.
    """
    ctx = resolve_context()
    repo_root = ctx.repo_root

    # Get current branch
    branch = current_branch(repo_root)
    if not branch:
        rprint("[red]Error: Not on a git branch[/red]")
        return 1

    # Check if we're in "work start" mode
    issue_key = extract_issue_key_from_branch(branch)
    if not issue_key:
        rprint(f"[yellow]Error: Branch '{branch}' doesn't contain a Jira issue key.[/yellow]")
        rprint("[cyan]Start work on an issue first:[/cyan]")
        rprint("  pwm work-start ABC-123")
        return 1

    # Get GitHub repo
    github_repo = ctx.github_repo
    if not github_repo:
        rprint("[red]Error: GitHub repo not configured.[/red]")
        rprint("[cyan]Run 'pwm init' to configure your project.[/cyan]")
        return 1

    # Get GitHub client
    github = GitHubClient.from_config(ctx.config)
    if not github:
        rprint("[red]Error: GitHub not configured.[/red]")
        rprint("[cyan]Set GITHUB_TOKEN or PWM_GITHUB_TOKEN environment variable.[/cyan]")
        return 1

    # Check if PR exists (check both open and closed)
    pr = github.get_pr_for_branch(github_repo, branch, state="all")
    if not pr:
        rprint(f"[yellow]Error: No pull request found for branch '{branch}'.[/yellow]")
        rprint("[cyan]Create a PR first:[/cyan]")
        rprint("  pwm pr")
        return 1

    pr_number = pr["number"]
    pr_url = pr["html_url"]

    rprint(f"[cyan]Found PR #{pr_number}:[/cyan] {pr['title']}")
    rprint(f"[dim]{pr_url}[/dim]")

    # Get configured remote
    remote = ctx.config.get("git", {}).get("default_remote", "origin")

    # Get commits since last comment (simplified: get all commits for now)
    # In future, could track last comment timestamp
    commits = get_commits_since_base(repo_root, remote=remote)

    if not commits:
        rprint("[yellow]Warning: No commits found on this branch.[/yellow]")

    # Generate or use custom message
    if message:
        summary = message
    else:
        summary = generate_work_summary(commits)

    rprint(f"[cyan]Summary:[/cyan] {summary}")

    # Comment on PR
    pr_commented = False
    if not no_comment and not no_pr_comment:
        rprint(f"[cyan]Adding comment to PR #{pr_number}...[/cyan]")
        comment_body = f"**Status Update**\n\n{summary}"

        if github.add_pr_comment(github_repo, pr_number, comment_body):
            pr_commented = True
            rprint("[green]✓ Commented on PR[/green]")
        else:
            rprint("[yellow]⚠ Failed to comment on PR[/yellow]")

    # Comment on Jira
    jira_commented = False
    if not no_comment and not no_jira_comment:
        jira = JiraClient.from_config(ctx.config)
        if jira:
            rprint(f"[cyan]Adding comment to Jira {issue_key}...[/cyan]")

            # Add comment with clickable link
            if jira.add_comment_with_link(
                issue_key,
                f"Status update: {summary}",
                f"View PR #{pr_number}",
                pr_url
            ):
                jira_commented = True
                rprint("[green]✓ Commented on Jira[/green]")
            else:
                rprint("[yellow]⚠ Failed to comment on Jira[/yellow]")
        else:
            rprint("[dim]Skipping Jira comment (not configured)[/dim]")

    # Request reviewers if requested
    reviewers_requested = False
    if request_review:
        pr_defaults = ctx.config.get("github", {}).get("pr_defaults", {})
        reviewers = pr_defaults.get("reviewers", [])
        team_reviewers = pr_defaults.get("team_reviewers", [])

        if reviewers or team_reviewers:
            rprint("[cyan]Requesting reviewers...[/cyan]")
            if github.request_reviewers(github_repo, pr_number, reviewers, team_reviewers):
                reviewers_requested = True
                if reviewers:
                    rprint(f"[green]✓ Requested reviewers: {', '.join(reviewers)}[/green]")
                if team_reviewers:
                    rprint(f"[green]✓ Requested team reviewers: {', '.join(team_reviewers)}[/green]")
            else:
                rprint("[yellow]⚠ Failed to request reviewers[/yellow]")
        else:
            rprint("[yellow]No reviewers configured in .pwm.toml[/yellow]")
            rprint("[dim]Add [github.pr_defaults] section with reviewers/team_reviewers[/dim]")

    # Summary
    rprint()
    rprint("[bold green]Work update complete![/bold green]")
    if pr_commented or jira_commented:
        rprint("[dim]Status updates posted[/dim]")
    if reviewers_requested:
        rprint("[dim]Reviewers notified[/dim]")

    return 0
