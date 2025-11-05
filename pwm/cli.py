
import typer

from pwm.context.command import show_context
from pwm.setup.init import init_project
from pwm.prompt.command import prompt_command, PromptFormat
from pwm.work.start import work_start
from pwm.work.end import work_end
from pwm.check.self_check import self_check
from pwm.pr.open import open_pr

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
@app.command("ws")
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

@app.command("work-end")
@app.command("we")
def work_end_cmd(
    message: str = typer.Option(None, "--message", "-m", help="Custom status message"),
    no_comment: bool = typer.Option(False, "--no-comment", help="Skip all comments"),
    no_pr_comment: bool = typer.Option(False, "--no-pr-comment", help="Skip PR comment"),
    no_jira_comment: bool = typer.Option(False, "--no-jira-comment", help="Skip Jira comment"),
    request_review: bool = typer.Option(False, "--request-review", help="Request reviewers from config")
) -> None:
    """Post status update to PR and Jira issue."""
    raise SystemExit(work_end(
        message=message,
        no_comment=no_comment,
        no_pr_comment=no_pr_comment,
        no_jira_comment=no_jira_comment,
        request_review=request_review
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

@app.command()
def pr(
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI-generated summary")
) -> None:
    """Open or create a pull request for the current branch."""
    raise SystemExit(open_pr(use_ai=not no_ai))

if __name__ == "__main__":
    app()
