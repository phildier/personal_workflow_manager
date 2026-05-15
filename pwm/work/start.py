
from __future__ import annotations
from pathlib import Path
from typing import Optional
from rich import print as rprint
from rich.table import Table

from pwm.context.resolver import resolve_context, slugify
from pwm.vcs.git_cli import current_branch, branch_exists, create_branch, switch_branch
from pwm.jira.client import JiraClient
from pwm.work.create_issue import create_new_issue

def work_start(
    issue_key: Optional[str] = None,
    create_new: bool = False,
    transition: bool = True,
    comment: bool = True,
    non_interactive: bool = False,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    issue_type: Optional[str] = None,
    labels: Optional[list[str]] = None,
    story_points: Optional[float] = None,
    custom_fields: Optional[dict] = None,
    save_defaults: Optional[bool] = None,
    event_details: Optional[dict] = None,
) -> int:
    ctx = resolve_context()
    repo_root = ctx.repo_root

    # Validate inputs
    if create_new and issue_key:
        rprint("[red]Error: Cannot specify both --new and an issue key[/red]")
        if event_details is not None:
            event_details["error"] = "Cannot specify both --new and issue_key"
        return 1

    if not create_new and not issue_key:
        rprint("[red]Error: Must specify either an issue key or --new flag[/red]")
        if event_details is not None:
            event_details["error"] = "Must specify issue_key or --new"
        return 1

    jira = JiraClient.from_config(ctx.config)

    # Handle creating new issue
    if create_new:
        if not jira:
            rprint("[red]Error: Jira not configured. Run 'pwm init' or set Jira environment variables.[/red]")
            if event_details is not None:
                event_details["error"] = "Jira not configured for --new"
            return 1

        project_key = ctx.jira_project_key
        if not project_key:
            rprint("[red]Error: No Jira project configured. Run 'pwm init' to set project key.[/red]")
            if event_details is not None:
                event_details["error"] = "No Jira project key configured"
            return 1

        issue_key = create_new_issue(
            jira,
            project_key,
            repo_root,
            ctx.config,
            non_interactive=non_interactive,
            summary=summary,
            description=description,
            issue_type=issue_type,
            labels=labels,
            story_points=story_points,
            custom_fields=custom_fields,
            save_defaults=save_defaults,
        )
        if not issue_key:
            rprint("[yellow]Issue creation cancelled or failed.[/yellow]")
            if event_details is not None:
                event_details["error"] = "Issue creation cancelled or failed"
            return 1

    # Get issue summary for branch naming
    summary = jira.get_issue_summary(issue_key) if jira else None

    slug = slugify(summary or issue_key)
    pattern = ctx.config.get("branch", {}).get("pattern") or "{issue_key}-{slug}"
    branch_name = pattern.format(issue_key=issue_key, slug=slug)

    # Get configured remote
    remote = ctx.config.get("git", {}).get("default_remote", "origin")

    current = current_branch(repo_root)
    created = False
    switched = False
    if current == branch_name:
        pass
    elif branch_exists(repo_root, branch_name):
        switched = switch_branch(repo_root, branch_name)
    else:
        created = create_branch(repo_root, branch_name, remote=remote)
        switched = True if created else False

    transitioned = False
    commented = False
    assigned = False
    repo_name = ctx.github_repo or repo_root.name
    if jira:
        # Assign issue to current user
        account_id = jira.get_current_account_id()
        if account_id:
            assigned = jira.assign_issue(issue_key, account_id)
        if transition:
            transitioned = jira.transition_by_name(issue_key, "In Progress") or False
        if comment:
            comment_text = (
                f"Started work on branch `{branch_name}` in repo `{repo_name}`"
            )
            commented = jira.add_comment(issue_key, comment_text) or False

    table = Table(title="pwm work start")
    table.add_column("Action", style="bold cyan")
    table.add_column("Result", style="white")
    table.add_row("Branch name", branch_name)
    table.add_row("Branch created", "yes" if created else "no")
    table.add_row("Switched to branch", "yes" if (switched or current == branch_name) else "no")
    table.add_row("Jira summary", summary or "<unknown>")
    table.add_row("Jira assigned to me", ("yes" if assigned else "no") if jira else "<skipped>")
    table.add_row("Jira transitioned -> In Progress", ("yes" if transitioned else "no") if jira else "<skipped>")
    table.add_row("Jira comment added", ("yes" if commented else "no") if jira else "<skipped>")
    rprint(table)

    if event_details is not None:
        event_details["issue_key"] = issue_key
        event_details["branch_name"] = branch_name
        event_details["repo_root"] = str(repo_root)
        event_details["github_repo"] = ctx.github_repo
        event_details["jira_assigned"] = assigned if jira else None
        event_details["jira_transitioned"] = transitioned if jira else None
        event_details["jira_commented"] = commented if jira else None

    return 0
