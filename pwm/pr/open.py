
from __future__ import annotations
from pathlib import Path
import webbrowser
from typing import Optional
from rich import print as rprint
from rich.prompt import Confirm

from pwm.context.resolver import resolve_context
from pwm.vcs.git_cli import (
    current_branch,
    get_default_branch,
    get_commits_since_base,
    push_branch
)
from pwm.github.client import GitHubClient
from pwm.prompt.command import extract_issue_key_from_branch
from pwm.jira.client import JiraClient


def generate_pr_title(issue_key: str, jira: Optional[JiraClient]) -> str:
    """
    Generate a succinct PR title from Jira issue.

    Format: "[ISSUE-123] Brief summary"
    """
    if jira:
        summary = jira.get_issue_summary(issue_key)
        if summary:
            return f"[{issue_key}] {summary}"

    return f"[{issue_key}] Changes"


def generate_pr_description(
    issue_key: str,
    commits: list[dict],
    jira: Optional[JiraClient],
    jira_base_url: Optional[str]
) -> str:
    """
    Generate PR description from commits and Jira issue.

    Includes:
    - Link to Jira issue
    - Summary of commits
    """
    lines = []

    # Add Jira link
    if jira_base_url:
        lines.append(f"**Jira:** [{issue_key}]({jira_base_url}/browse/{issue_key})")
        lines.append("")

    # Get issue description from Jira if available
    if jira:
        issue_data = jira.get_issue(issue_key)
        if issue_data and issue_data.get("fields", {}).get("description"):
            desc = issue_data["fields"]["description"]
            # Jira API v3 returns ADF format, try to extract text
            if isinstance(desc, dict) and desc.get("content"):
                # Extract plain text from ADF
                text_parts = []
                for content_item in desc.get("content", []):
                    if content_item.get("type") == "paragraph":
                        for para_content in content_item.get("content", []):
                            if para_content.get("type") == "text":
                                text_parts.append(para_content.get("text", ""))
                if text_parts:
                    lines.append("## Description")
                    lines.append("")
                    lines.append(" ".join(text_parts))
                    lines.append("")

    # Add commits summary
    if commits:
        lines.append("## Changes")
        lines.append("")

        # Group commits by type if they follow conventional commit format
        for commit in commits:
            subject = commit["subject"]
            lines.append(f"- {subject}")

        lines.append("")
        lines.append(f"**Total commits:** {len(commits)}")

    return "\n".join(lines)


def open_pr(open_browser: bool = True) -> int:
    """
    Open a pull request for the current branch.

    Workflow:
    1. Check if we're in "work start" mode (branch has Jira issue key)
    2. Check if PR already exists
       - If yes, open in browser
    3. If no PR exists:
       - Generate title and description
       - Create PR
       - Open in browser

    Returns 0 on success, 1 on error.
    """
    ctx = resolve_context()
    repo_root = ctx.repo_root

    # Get current branch
    branch = current_branch(repo_root)
    if not branch:
        rprint("[red]Error: Not on a git branch[/red]")
        return 1

    # Check if we're in "work start" mode (branch has issue key)
    issue_key = extract_issue_key_from_branch(branch)
    if not issue_key:
        rprint(f"[yellow]Branch '{branch}' doesn't contain a Jira issue key.[/yellow]")
        rprint("[cyan]Start work on an issue first:[/cyan]")
        rprint("  pwm work-start ABC-123")
        rprint("  pwm work-start --new")
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

    # Check if PR already exists
    existing_pr = github.get_pr_for_branch(github_repo, branch)
    if existing_pr:
        pr_url = existing_pr["html_url"]
        rprint(f"[green]PR already exists:[/green] {pr_url}")
        rprint(f"[dim]#{existing_pr['number']}: {existing_pr['title']}[/dim]")

        if open_browser:
            webbrowser.open(pr_url)
            rprint("[cyan]Opened in browser[/cyan]")

        return 0

    # No existing PR - create one
    rprint(f"[cyan]No PR exists for branch '{branch}'[/cyan]")

    # Get base branch
    base_branch_ref = get_default_branch(repo_root)
    # Extract just the branch name (remove "origin/" prefix)
    base_branch = base_branch_ref.split("/")[-1] if "/" in base_branch_ref else base_branch_ref

    # Get commits
    commits = get_commits_since_base(repo_root, base_branch_ref)
    if not commits:
        rprint("[yellow]Warning: No commits found on this branch.[/yellow]")
        create_anyway = Confirm.ask("Create PR anyway?", default=False)
        if not create_anyway:
            return 1

    # Ensure branch is pushed
    rprint(f"[cyan]Pushing branch '{branch}' to remote...[/cyan]")
    if not push_branch(repo_root, branch):
        rprint("[red]Error: Failed to push branch to remote.[/red]")
        return 1

    # Get Jira client for enhanced title/description
    jira = JiraClient.from_config(ctx.config)
    jira_base_url = ctx.config.get("jira", {}).get("base_url")

    # Generate title and description
    title = generate_pr_title(issue_key, jira)
    description = generate_pr_description(issue_key, commits, jira, jira_base_url)

    rprint(f"[cyan]Creating PR...[/cyan]")
    rprint(f"  Title: {title}")
    rprint(f"  Base: {base_branch}")
    rprint(f"  Head: {branch}")

    # Create PR
    pr = github.create_pr(
        repo=github_repo,
        title=title,
        head=branch,
        base=base_branch,
        body=description
    )

    if not pr:
        rprint("[red]Error: Failed to create PR.[/red]")
        rprint("[dim]Check that your GitHub token has the 'repo' scope.[/dim]")
        return 1

    pr_url = pr["html_url"]
    rprint(f"[green]✓ PR created successfully![/green]")
    rprint(f"  {pr_url}")

    if open_browser:
        webbrowser.open(pr_url)
        rprint("[cyan]Opened in browser[/cyan]")

    return 0
