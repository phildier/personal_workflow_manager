from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich import print as rprint

from pwm.context.resolver import resolve_context
from pwm.jira.client import JiraClient
from pwm.work.create_issue import create_new_issue


def issue_create(
    *,
    non_interactive: bool = False,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    issue_type: Optional[str] = None,
    labels: Optional[list[str]] = None,
    story_points: Optional[float] = None,
    epic: Optional[str] = None,
    custom_fields: Optional[dict] = None,
    save_defaults: Optional[bool] = None,
    event_details: Optional[dict] = None,
) -> int:
    """Create a Jira issue without branch operations."""
    ctx = resolve_context()
    repo_root = ctx.repo_root

    jira = JiraClient.from_config(ctx.config)
    if not jira:
        rprint(
            "[red]Error: Jira not configured. Run 'pwm init' or set Jira environment variables.[/red]"
        )
        if event_details is not None:
            event_details["error"] = "Jira not configured"
        return 1

    project_key = ctx.jira_project_key
    if not project_key:
        rprint(
            "[red]Error: No Jira project configured. Run 'pwm init' to set project key.[/red]"
        )
        if event_details is not None:
            event_details["error"] = "No Jira project key configured"
        return 1

    issue_key = create_new_issue(
        jira=jira,
        project_key=project_key,
        repo_root=repo_root,
        config=ctx.config,
        non_interactive=non_interactive,
        summary=summary,
        description=description,
        issue_type=issue_type,
        labels=labels,
        story_points=story_points,
        epic=epic,
        custom_fields=custom_fields,
        save_defaults=save_defaults,
    )
    if not issue_key:
        rprint("[yellow]Issue creation cancelled or failed.[/yellow]")
        if event_details is not None:
            event_details["error"] = "Issue creation cancelled or failed"
        return 1

    if event_details is not None:
        event_details["issue_key"] = issue_key
        event_details["repo_root"] = str(repo_root)
        event_details["jira_project_key"] = project_key

    return 0
