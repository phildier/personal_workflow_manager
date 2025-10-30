from __future__ import annotations
from pathlib import Path
from rich import print as rprint
from rich.table import Table

from pwm.context.resolver import find_git_root, resolve_context
from pwm.vcs.git_cli import current_branch, infer_github_repo_from_remote
from pwm.jira.client import JiraClient
from pwm.github.client import GitHubClient

def self_check() -> int:
    """Run connectivity & setup checks for git, Jira, and GitHub."""
    git_ok = False
    git_msg = ""
    try:
        repo_root = find_git_root(Path.cwd())
        cur = current_branch(repo_root)
        if cur:
            git_ok = True
            inferred = infer_github_repo_from_remote(repo_root) or "<none>"
            git_msg = f"ok (branch: {cur}, remote: {inferred})"
        else:
            git_msg = "unable to determine current branch"
    except Exception as e:
        git_msg = f"not a git repo ({e})"

    try:
        ctx = resolve_context()
    except Exception:
        ctx = None

    # Jira
    jira_ok = False
    jira_status = "<skipped>"
    jira_hint = ""
    if ctx:
        jira = JiraClient.from_config(ctx.config)
        if jira:
            ok, msg = jira.ping()
            jira_ok, jira_status = ok, msg
            if not ok:
                jira_hint = "set PWM_JIRA_TOKEN, PWM_JIRA_EMAIL, PWM_JIRA_BASE_URL"
        else:
            jira_status = "missing config/token"
            jira_hint = "set PWM_JIRA_TOKEN, PWM_JIRA_EMAIL, PWM_JIRA_BASE_URL"
    else:
        jira_status = "context resolution failed"

    # GitHub
    gh_ok = False
    gh_status = "<skipped>"
    gh_hint = ""
    if ctx:
        gh = GitHubClient.from_config(ctx.config)
        if gh:
            ok, msg = gh.ping()
            gh_ok, gh_status = ok, msg
            if not ok:
                gh_hint = "set GITHUB_TOKEN or PWM_GITHUB_TOKEN"
        else:
            gh_status = "missing token"
            gh_hint = "set GITHUB_TOKEN or PWM_GITHUB_TOKEN"
    else:
        gh_status = "context resolution failed"

    table = Table(title="pwm self-check")
    table.add_column("Check", style="bold cyan")
    table.add_column("Status", style="white")
    table.add_column("Hint", style="yellow")

    table.add_row("Local git", "ok" if git_ok else f"[red]{git_msg}[/red]", "")
    table.add_row("Jira API", "ok" if jira_ok else f"[red]{jira_status}[/red]", jira_hint)
    table.add_row("GitHub API", "ok" if gh_ok else f"[red]{gh_status}[/red]", gh_hint)

    rprint(table)

    return 0 if (git_ok and (jira_ok or jira_status.startswith("<skipped>")) and (gh_ok or gh_status.startswith("<skipped>"))) else 1
