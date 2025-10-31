
import typer

from pwm.context.command import show_context
from pwm.setup.init import init_project
from pwm.prompt.command import prompt_command, PromptFormat
from pwm.work.start import work_start
from pwm.check.self_check import self_check

app = typer.Typer(help="Personal Workflow Manager")

@app.command()
def context():
    """Show resolved project context (repo root, GitHub repo, Jira project, config paths)."""
    show_context()

@app.command()
def init():
    """Scaffold a .pwm.toml in the current project."""
    init_project()

@app.command("work-start")
def work_start_cmd(
    issue_key: str = typer.Argument(None, help="Jira issue key (e.g., ABC-123). Omit if using --new."),
    new: bool = typer.Option(False, "--new", help="Create a new Jira issue interactively"),
    no_transition: bool = typer.Option(False, help="Do not transition Jira issue"),
    no_comment: bool = typer.Option(False, help="Do not add Jira comment")
):
    """Start work on a Jira issue: create or switch branch and optionally update Jira."""
    raise SystemExit(work_start(
        issue_key=issue_key,
        create_new=new,
        transition=not no_transition,
        comment=not no_comment
    ))

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
