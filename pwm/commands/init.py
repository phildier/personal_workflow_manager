from pathlib import Path
import subprocess
import typer
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from pwm.context.resolver import find_git_root


def _infer_github_repo(repo_root: Path) -> str | None:
    """Try to detect org/repo from the git remote."""
    try:
        url = subprocess.check_output(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return None

    # Parse ssh or https form into org/repo
    if url.startswith("git@") and ":" in url:
        path = url.split(":", 1)[1]
    elif url.startswith("http://") or url.startswith("https://"):
        path = url.split("//", 1)[1]
        path = "/".join(path.split("/", 1)[1:])
    else:
        return None

    path = path[:-4] if path.endswith(".git") else path
    if "/" in path:
        return path
    return None


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
        overwrite = Confirm.ask(
            f"[yellow]{config_path} already exists[/yellow]. Overwrite?", default=False
        )
        if not overwrite:
            rprint("[green]Aborted.[/green]")
            raise typer.Exit()

    # Detect defaults
    inferred_repo = _infer_github_repo(repo_root)
    default_branch_pattern = "feature/{issue_key}-{slug}"

    # Interactive setup
    rprint("[bold cyan]Let's set up your project config...[/bold cyan]")
    jira_key = Prompt.ask("Jira project key (e.g., ABC)", default="")
    github_repo = Prompt.ask(
        f"GitHub repo (org/repo)", default=inferred_repo or ""
    )
    branch_pattern = Prompt.ask("Branch pattern", default=default_branch_pattern)

    # Build TOML
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
