
from pathlib import Path
import typer
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from pwm.context.resolver import find_git_root
from pwm.vcs.git_cli import infer_github_repo_from_remote

def init_project():
    """Initialize a .pwm.toml config in the current repo."""
    cwd = Path.cwd()
    try:
        repo_root = find_git_root(cwd)
    except RuntimeError:
        rprint("[red]Error:[/red] Not inside a git repository.")
        raise typer.Exit(1)

    config_path = repo_root / ".pwm.toml"
    if config_path.exists():
        overwrite = Confirm.ask(f"[yellow]{config_path} already exists[/yellow]. Overwrite?", default=False)
        if not overwrite:
            rprint("[green]Aborted.[/green]")
            raise typer.Exit()

    # Try to infer from "origin" since config doesn't exist yet during init
    inferred_repo = infer_github_repo_from_remote(repo_root, "origin")
    default_branch_pattern = "{issue_key}-{slug}"

    rprint("[bold cyan]Let's set up your project config...[/bold cyan]")
    jira_key = Prompt.ask("Jira project key (e.g., ABC)", default="")
    github_repo = Prompt.ask("GitHub repo (org/repo)", default=inferred_repo or "")
    branch_pattern = Prompt.ask("Branch pattern", default=default_branch_pattern)

    content = ["# pwm project configuration"]
    if jira_key:
        content += ["[jira]", f'project_key = "{jira_key}"', ""]
    if github_repo:
        content += ["[github]", f'repo = "{github_repo}"', ""]
    if branch_pattern:
        content += ["[branch]", f'pattern = "{branch_pattern}"', ""]

    config_path.write_text("\n".join(content))
    rprint(f"[green]Created[/green] {config_path}")
    rprint(f"[dim]Detected repo root:[/dim] {repo_root}")
    if inferred_repo:
        rprint(f"[dim]Detected remote:[/dim] {inferred_repo}")
