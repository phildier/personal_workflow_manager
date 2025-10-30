
from pathlib import Path
import typer
from rich import print as rprint
from rich.table import Table

from pwm.context.resolver import resolve_context
from pwm.commands.init import init_project
from pwm.commands.prompt import prompt_command, PromptFormat
from pwm.work.start import work_start
from pwm.check.self_check import self_check

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

@app.command()
def init():
    """Scaffold a .pwm.toml in the current project."""
    init_project()

@app.command("work-start")
def work_start_cmd(issue_key: str, no_transition: bool = typer.Option(False, help="Do not transition Jira issue"),
                   no_comment: bool = typer.Option(False, help="Do not add Jira comment")):
    """Start work on a Jira issue: create or switch branch and optionally update Jira."""
    raise SystemExit(work_start(issue_key, transition=not no_transition, comment=not no_comment))

@app.command("self-check")
def self_check_cmd() -> None:
    """Run connectivity and setup checks for git, Jira, and GitHub."""
    raise SystemExit(self_check())

@app.command()
def prompt(
    with_status: bool = typer.Option(False, "--with-status", help="Fetch and display Jira issue status"),
    format: PromptFormat = typer.Option(PromptFormat.DEFAULT, "--format", help="Output format: default, minimal, or emoji"),
    color: bool = typer.Option(False, "--color", help="Use ANSI color codes")
) -> None:
    """Generate shell prompt information for current work context."""
    raise SystemExit(prompt_command(with_status=with_status, format_type=format, use_color=color))

if __name__ == "__main__":
    app()
