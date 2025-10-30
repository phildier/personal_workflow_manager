from pathlib import Path
import typer
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from pwm.context.resolver import find_git_root

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

    # Gather settings
    rprint("[bold cyan]Let's set up your project config...[/bold cyan]")
    jira_key = Prompt.ask("Jira project key (e.g., ABC)", default="")
    github_repo = Prompt.ask("GitHub repo (e.g., your-org/your-repo)", default="")
    branch_pattern = Prompt.ask("Branch pattern", default="feature/{issue_key}-{slug}")

    content = ["# pwm project configuration"]
    if jira_key:
        content += [
            "[jira]",
            f'project_key = "{jira_key}"',
            "",
        ]
    if github_repo:
        content += [
            "[github]",
            f'repo = "{github_repo}"',
            "",
        ]
    if branch_pattern:
        content += [
            "[branch]",
            f'pattern = "{branch_pattern}"',
            "",
        ]

    config_path.write_text("\n".join(content))
    rprint(f"[green]Created[/green] {config_path}")
