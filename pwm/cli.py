from pathlib import Path
import typer
from rich import print as rprint
from rich.table import Table

from pwm.context.resolver import resolve_context
from pwm.commands.init import init_project
from pwm.work.start import work_start

app = typer.Typer(help="Personal Workflow Manager")

@app.command()
def context():
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

if __name__ == "__main__":
    app()


@app.command()
def init():
    """Scaffold a .pwm.toml in the current project."""
    init_project()


@app.command("work-start")
def work_start_cmd(issue_key: str, no_transition: bool = typer.Option(False, help="Do not transition Jira issue"),
                   no_comment: bool = typer.Option(False, help="Do not add Jira comment")):
    """Start work on a Jira issue: create/switch branch and (optionally) update Jira."""
    work_start(issue_key, transition=not no_transition, comment=not no_comment)
