
from __future__ import annotations
from pathlib import Path
from rich import print as rprint
from rich.table import Table

from pwm.context.resolver import resolve_context, slugify
from pwm.vcs.git_cli import current_branch, branch_exists, create_branch, switch_branch
from pwm.jira.client import JiraClient

def work_start(issue_key: str, transition: bool = True, comment: bool = True) -> int:
    ctx = resolve_context()
    repo_root = ctx.repo_root

    jira = JiraClient.from_config(ctx.config)
    summary = jira.get_issue_summary(issue_key) if jira else None

    slug = slugify(summary or issue_key)
    pattern = ctx.config.get("branch", {}).get("pattern") or "feature/{issue_key}-{slug}"
    branch_name = pattern.format(issue_key=issue_key, slug=slug)

    current = current_branch(repo_root)
    created = False
    switched = False
    if current == branch_name:
        pass
    elif branch_exists(repo_root, branch_name):
        switched = switch_branch(repo_root, branch_name)
    else:
        created = create_branch(repo_root, branch_name)
        switched = True if created else False

    transitioned = False
    commented = False
    if jira:
        if transition:
            transitioned = jira.transition_by_name(issue_key, "In Progress") or False
        if comment:
            commented = jira.add_comment(issue_key, f"Started work on branch `{branch_name}`") or False

    table = Table(title="pwm work start")
    table.add_column("Action", style="bold cyan")
    table.add_column("Result", style="white")
    table.add_row("Branch name", branch_name)
    table.add_row("Branch created", "yes" if created else "no")
    table.add_row("Switched to branch", "yes" if (switched or current == branch_name) else "no")
    table.add_row("Jira summary", summary or "<unknown>")
    table.add_row("Jira transitioned -> In Progress", ("yes" if transitioned else "no") if jira else "<skipped>")
    table.add_row("Jira comment added", ("yes" if commented else "no") if jira else "<skipped>")
    rprint(table)

    return 0
