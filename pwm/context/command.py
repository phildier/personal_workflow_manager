
from rich import print as rprint
from rich.table import Table

from pwm.context.resolver import resolve_context

def show_context():
    """Show resolved project context (repo root, GitHub repo, Jira project, config paths)."""
    ctx = resolve_context()
    table = Table(title="pwm context", show_lines=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="white")
    table.add_row("repo_root", str(ctx.repo_root))
    table.add_row("github_repo", ctx.github_repo or "<unknown>")
    table.add_row("jira_project", ctx.jira_project_key or "<unknown>")
    table.add_row("user_config", str(ctx.meta.user_config_path) if ctx.meta.user_config_path else "<none>")
    table.add_row("project_config", str(ctx.meta.project_config_path) if ctx.meta.project_config_path else "<none>")
    table.add_row("config_source", ctx.meta.source_summary)
    rprint(table)
