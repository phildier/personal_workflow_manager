from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import webbrowser
import os
import sys
from typing import Optional, TYPE_CHECKING
from rich import print as rprint
from rich.prompt import Confirm

from pwm.context.resolver import resolve_context
from pwm.vcs.git_cli import (
    current_branch,
    get_default_branch,
    get_commits_since_base,
    get_diff_since_base,
    push_branch,
)
from pwm.github.client import GitHubClient
from pwm.prompt.command import extract_issue_key_from_branch
from pwm.jira.client import JiraClient
from pwm.vcs.remote_url import parse_repo_from_remote_url

if TYPE_CHECKING:
    from pwm.ai.summarizer import SupportsCompletion


def _debug(message: str) -> None:
    """Emit debug diagnostics when PWM_DEBUG is enabled."""
    if os.getenv("PWM_DEBUG") == "1":
        print(f"[DEBUG] pr.open: {message}", file=sys.stderr)


def _normalize_labels(labels: Optional[list[str]]) -> list[str]:
    """Return labels with whitespace removed and duplicates dropped."""
    if not labels:
        return []

    normalized = []
    seen_labels = set()
    for raw_label in labels:
        stripped_label = raw_label.strip()
        if not stripped_label or stripped_label in seen_labels:
            continue
        seen_labels.add(stripped_label)
        normalized.append(stripped_label)
    return normalized


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command and return its completed process result."""
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
    )


def _git_stdout(repo_root: Path, args: list[str]) -> Optional[str]:
    """Return stripped stdout for a successful git command."""
    result = _run_git(repo_root, args)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _get_remote_url(repo_root: Path, remote: str) -> Optional[str]:
    """Return the URL for a git remote when available."""
    return _git_stdout(repo_root, ["remote", "get-url", remote])


def _list_remotes(repo_root: Path) -> list[str]:
    """Return configured remote names for the repository."""
    remotes = _git_stdout(repo_root, ["remote"])
    if not remotes:
        return []
    return [name.strip() for name in remotes.splitlines() if name.strip()]


def _get_upstream_ref(repo_root: Path) -> Optional[str]:
    """Return upstream tracking ref for current branch (for example origin/feat)."""
    return _git_stdout(repo_root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])


def _push_viability(repo_root: Path, remote: str, branch: str) -> tuple[bool, str]:
    """Check whether pushing branch is likely to succeed using dry-run push."""
    result = _run_git(repo_root, ["push", "--dry-run", remote, f"HEAD:{branch}"])
    if result.returncode == 0:
        return True, "ok"

    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout or "git push --dry-run failed"
    return False, detail


def _changed_files_since_base(repo_root: Path, base_branch_ref: str) -> list[str]:
    """Return changed files compared to base...HEAD."""
    output = _git_stdout(repo_root, ["diff", "--name-only", f"{base_branch_ref}...HEAD"])
    if not output:
        return []
    return [line for line in output.splitlines() if line]


def _head_sha(repo_root: Path) -> Optional[str]:
    """Return HEAD commit SHA for current worktree."""
    return _git_stdout(repo_root, ["rev-parse", "HEAD"])


def _git_dir(repo_root: Path) -> Optional[Path]:
    """Resolve the worktree git dir path even when .git is a file."""
    raw = _git_stdout(repo_root, ["rev-parse", "--git-dir"])
    if not raw:
        return None
    git_dir = Path(raw)
    if git_dir.is_absolute():
        return git_dir
    return (repo_root / git_dir).resolve()


def _receipt_path(repo_root: Path) -> Optional[Path]:
    """Return per-worktree PR receipt path (.git/pwm/pr.json)."""
    git_dir = _git_dir(repo_root)
    if not git_dir:
        return None
    return git_dir / "pwm" / "pr.json"


def _read_pr_receipt(repo_root: Path) -> Optional[dict]:
    """Read PR receipt from per-worktree git metadata path."""
    receipt_file = _receipt_path(repo_root)
    if receipt_file is None or not receipt_file.exists():
        return None

    try:
        data = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None
    return data


def _write_pr_receipt(
    repo_root: Path,
    branch: str,
    head_sha: Optional[str],
    pr_url: str,
    labels: list[str],
) -> None:
    """Persist PR discovery/creation receipt under per-worktree .git metadata."""
    receipt_file = _receipt_path(repo_root)
    if receipt_file is None:
        return

    receipt_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "written_at": datetime.now(timezone.utc).isoformat(),
        "branch": branch,
        "head_sha": head_sha,
        "pr_url": pr_url,
        "labels": labels,
    }
    receipt_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _extract_labels(pr: dict) -> list[str]:
    """Extract label names from GitHub PR payload."""
    raw_labels = pr.get("labels")
    if not isinstance(raw_labels, list):
        return []

    labels: list[str] = []
    for item in raw_labels:
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                labels.append(name.strip())
    return _normalize_labels(labels)


def _receipt_can_be_reused(
    receipt: Optional[dict],
    branch: str,
    head_sha: Optional[str],
    requested_labels: list[str],
) -> bool:
    """Return whether receipt still matches current branch/HEAD/metadata request."""
    if not receipt:
        return False

    if receipt.get("branch") != branch:
        return False

    receipt_sha = receipt.get("head_sha")
    if not isinstance(receipt_sha, str) or receipt_sha != head_sha:
        return False

    url = receipt.get("pr_url")
    if not isinstance(url, str) or not url:
        return False

    if requested_labels:
        existing = receipt.get("labels")
        if not isinstance(existing, list):
            return False
        existing_set = {str(item).strip() for item in existing if str(item).strip()}
        if not set(requested_labels).issubset(existing_set):
            return False

    return True


def preflight_pr(
    create_anyway: bool = False,
    labels: Optional[list[str]] = None,
    event_details: Optional[dict] = None,
) -> dict:
    """Collect machine-readable diagnostics for PR creation viability."""
    ctx = resolve_context()
    repo_root = ctx.repo_root
    requested_labels = _normalize_labels(labels)
    remote = ctx.config.get("git", {}).get("default_remote", "origin")

    branch = current_branch(repo_root)
    issue_key = extract_issue_key_from_branch(branch) if branch else None
    upstream = _get_upstream_ref(repo_root) if branch else None
    head_sha = _head_sha(repo_root)

    remote_url = _get_remote_url(repo_root, remote)
    remote_repo = parse_repo_from_remote_url(remote_url) if remote_url else None
    resolved_repo = ctx.github_repo or remote_repo
    configured_repo = ctx.config.get("github", {}).get("repo")

    remote_repo_mismatch = False
    mismatch_reason = None
    matching_remote_for_configured_repo = None
    if configured_repo and remote_repo and configured_repo != remote_repo:
        remote_repo_mismatch = True
        for candidate in _list_remotes(repo_root):
            candidate_url = _get_remote_url(repo_root, candidate)
            candidate_repo = (
                parse_repo_from_remote_url(candidate_url) if candidate_url else None
            )
            if candidate_repo == configured_repo:
                matching_remote_for_configured_repo = candidate
                mismatch_reason = (
                    f"Configured github.repo matches remote '{candidate}', "
                    f"not '{remote}'."
                )
                break
        if mismatch_reason is None:
            mismatch_reason = (
                "Configured github.repo differs from the selected git remote "
                "repository."
            )

    base_branch_ref = get_default_branch(repo_root, remote)
    base_branch = (
        base_branch_ref.split("/")[-1]
        if "/" in base_branch_ref
        else base_branch_ref
    )
    commits = get_commits_since_base(repo_root, base_branch_ref, remote)
    changed_files = _changed_files_since_base(repo_root, base_branch_ref)
    commit_count = len(commits)
    changed_file_count = len(changed_files)

    push_viable, push_message = (False, "Not on a branch")
    if branch:
        push_viable, push_message = _push_viability(repo_root, remote, branch)

    receipt = _read_pr_receipt(repo_root)
    receipt_reusable = _receipt_can_be_reused(
        receipt,
        branch or "",
        head_sha,
        requested_labels,
    )

    existing_pr = {
        "url": None,
        "number": None,
        "title": None,
        "source": "none",
    }
    github_client = GitHubClient.from_config(ctx.config)

    if receipt_reusable and receipt:
        existing_pr["url"] = receipt.get("pr_url")
        existing_pr["source"] = "receipt"
    elif github_client and resolved_repo and branch:
        remote_pr = github_client.get_pr_for_branch(resolved_repo, branch)
        if remote_pr:
            existing_pr = {
                "url": remote_pr.get("html_url"),
                "number": remote_pr.get("number"),
                "title": remote_pr.get("title"),
                "source": "github",
            }

    blocking_issues: list[dict[str, str]] = []

    if not branch:
        _debug("current_branch returned no branch")
        blocking_issues.append(
            {
                "code": "not_on_branch",
                "message": "Not on a git branch.",
                "remediation": "Switch to a branch before running 'pwm pr'.",
            }
        )

    if branch and not issue_key:
        _debug(f"branch '{branch}' does not contain Jira issue key")
        blocking_issues.append(
            {
                "code": "missing_issue_key",
                "message": (
                    f"Branch '{branch}' does not contain a Jira issue key."
                ),
                "remediation": (
                    "Use 'pwm work-start ABC-123' or "
                    "'pwm work-start --new' first."
                ),
            }
        )

    if not remote_url:
        blocking_issues.append(
            {
                "code": "missing_remote",
                "message": f"Git remote '{remote}' is not configured.",
                "remediation": (
                    f"Configure remote '{remote}' or set git.default_remote "
                    "in config."
                ),
            }
        )

    if not resolved_repo:
        blocking_issues.append(
            {
                "code": "missing_github_repo",
                "message": "Unable to resolve GitHub repository.",
                "remediation": (
                    "Set [github].repo in .pwm.toml or fix the remote URL."
                ),
            }
        )

    if not github_client:
        blocking_issues.append(
            {
                "code": "missing_github_credentials",
                "message": "GitHub token is not configured.",
                "remediation": "Set GITHUB_TOKEN or PWM_GITHUB_TOKEN.",
            }
        )

    if branch and not push_viable:
        blocking_issues.append(
            {
                "code": "push_not_viable",
                "message": "Branch is not pushable to configured remote.",
                "remediation": (
                    f"Run 'git push -u {remote} {branch}' and resolve errors."
                ),
            }
        )

    if (
        not create_anyway
        and existing_pr.get("url") is None
        and commit_count == 0
        and changed_file_count == 0
    ):
        blocking_issues.append(
            {
                "code": "no_changes_ahead",
                "message": "No commits or changed files ahead of base branch.",
                "remediation": (
                    "Create at least one commit before opening a PR, or rerun "
                    "with --create-anyway for an intentional empty PR."
                ),
            }
        )

    warnings: list[dict[str, str]] = []
    if remote_repo_mismatch:
        warnings.append(
            {
                "code": "github_repo_mismatch",
                "message": mismatch_reason or "GitHub repo mismatch detected.",
            }
        )

    result = {
        "ok": len(blocking_issues) == 0,
        "create_anyway": create_anyway,
        "repo_root": str(repo_root),
        "remote": {
            "name": remote,
            "url": remote_url,
            "exists": remote_url is not None,
        },
        "branch": {
            "name": branch,
            "issue_key": issue_key,
            "has_issue_key": issue_key is not None,
            "upstream": upstream,
        },
        "push": {
            "viable": push_viable,
            "detail": push_message,
        },
        "base_branch": {
            "ref": base_branch_ref,
            "name": base_branch,
        },
        "ahead": {
            "commit_count": commit_count,
            "commits": [
                {
                    "hash": commit.get("hash"),
                    "subject": commit.get("subject"),
                }
                for commit in commits
            ],
            "changed_file_count": changed_file_count,
            "changed_files": changed_files,
        },
        "existing_pr": existing_pr,
        "github_repository": {
            "configured_repo": configured_repo,
            "resolved_repo": resolved_repo,
            "remote_repo": remote_repo,
            "remote_mismatch": remote_repo_mismatch,
            "matching_remote_for_configured_repo": (
                matching_remote_for_configured_repo
            ),
        },
        "receipt": {
            "path": str(_receipt_path(repo_root)) if _receipt_path(repo_root) else None,
            "head_sha": head_sha,
            "found": receipt is not None,
            "reusable": receipt_reusable,
        },
        "blocking_issues": blocking_issues,
        "warnings": warnings,
    }

    if event_details is not None:
        event_details["preflight_ok"] = result["ok"]
        event_details["preflight_blockers"] = [
            issue["code"] for issue in blocking_issues
        ]

    return result


def display_pr_info(
    github: GitHubClient, github_repo: str, pr_number: int, pr_title: str, pr_url: str
) -> None:
    """
    Display PR information including file stats and reviews.

    Args:
        github: GitHub client
        github_repo: Repository in "owner/repo" format
        pr_number: PR number
        pr_title: PR title
        pr_url: PR URL
    """
    # Get detailed PR info for file stats
    pr_details = github.get_pr_details(github_repo, pr_number)

    # Display PR info
    if pr_details:
        files_changed = pr_details.get("changed_files", 0)
        additions = pr_details.get("additions", 0)
        deletions = pr_details.get("deletions", 0)
        rprint(
            f"[green]PR:[/green] {pr_title} [{files_changed} files, +{additions}, -{deletions}]"
        )
    else:
        rprint(f"[green]PR:[/green] {pr_title}")

    rprint(pr_url)

    # Get and display reviews if any
    reviews = github.get_pr_reviews(github_repo, pr_number)
    if reviews:
        # Group reviews by user (take most recent per user)
        user_reviews = {}
        for review in reviews:
            user = review.get("user", {}).get("login", "unknown")
            state = review.get("state", "")
            if state in ("APPROVED", "COMMENTED"):
                user_reviews[user] = state

        for user, state in user_reviews.items():
            rprint(f"- {user}  {state}")


def generate_pr_title(
    issue_key: str, jira: Optional[JiraClient], commits: Optional[list[dict]] = None
) -> str:
    """
    Generate a succinct PR title from Jira issue or commit messages.

    Format: "[ISSUE-123] Brief summary"

    Priority:
    1. Jira issue summary (if Jira available)
    2. First commit message (if commits available)
    3. Generic "Changes" fallback
    """
    if jira:
        summary = jira.get_issue_summary(issue_key)
        if summary:
            return f"[{issue_key}] {summary}"

    # Fallback to first commit message if available
    if commits and len(commits) > 0:
        first_commit = commits[0]["subject"]
        return f"[{issue_key}] {first_commit}"

    return f"[{issue_key}] Changes"


def generate_pr_description(
    issue_key: str,
    commits: list[dict],
    jira: Optional[JiraClient],
    jira_base_url: Optional[str],
    openai: Optional["SupportsCompletion"] = None,
    use_ai: bool = True,
    diff: Optional[str] = None,
    diff_summary: Optional[str] = None,
) -> str:
    """
    Generate PR description from commits, diff, and Jira issue.

    Includes:
    - Link to Jira issue
    - AI-generated commit summary (if OpenAI configured and use_ai=True)
    - AI-generated diff summary (if OpenAI configured, use_ai=True, and diff provided)
    - Jira issue description (if available)
    - Summary of commits
    """
    lines = []

    # Add Jira link
    if jira_base_url:
        lines.append(f"**Jira:** [{issue_key}]({jira_base_url}/browse/{issue_key})")
        lines.append("")

    # AI-generated summary (try first if enabled)
    ai_summary = None
    if use_ai and openai and commits:
        from pwm.ai.summarizer import summarize_commits_for_pr

        ai_summary = summarize_commits_for_pr(commits, openai)
        if ai_summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(ai_summary)
            lines.append("")

    # AI-generated diff summary
    resolved_diff_summary = diff_summary
    if resolved_diff_summary is None and use_ai and openai and diff:
        from pwm.ai.summarizer import summarize_diff_for_pr

        resolved_diff_summary = summarize_diff_for_pr(diff, openai)

    if resolved_diff_summary:
        lines.append("## Code Changes")
        lines.append("")
        lines.append(resolved_diff_summary)
        lines.append("")

    # Get issue description from Jira if available
    if jira:
        issue_data = jira.get_issue(issue_key)
        if issue_data and issue_data.get("fields", {}).get("description"):
            desc = issue_data["fields"]["description"]
            # Jira API v3 returns ADF format, try to extract text
            if isinstance(desc, dict) and desc.get("content"):
                # Extract plain text from ADF
                text_parts = []
                for content_item in desc.get("content", []):
                    if content_item.get("type") == "paragraph":
                        for para_content in content_item.get("content", []):
                            if para_content.get("type") == "text":
                                text_parts.append(para_content.get("text", ""))
                if text_parts:
                    lines.append("## Description")
                    lines.append("")
                    lines.append(" ".join(text_parts))
                    lines.append("")

    # Add commits summary
    if commits:
        lines.append("## Changes")
        lines.append("")

        # Group commits by type if they follow conventional commit format
        for commit in commits:
            subject = commit["subject"]
            lines.append(f"- {subject}")

        lines.append("")
        lines.append(f"**Total commits:** {len(commits)}")

    return "\n".join(lines)


def open_pr(
    open_browser: bool = True,
    use_ai: bool = True,
    create_anyway: bool = False,
    title_override: Optional[str] = None,
    body_override: Optional[str] = None,
    labels: Optional[list[str]] = None,
    non_interactive: bool = False,
    event_details: Optional[dict] = None,
) -> int:
    """
    Open a pull request for the current branch.

    Workflow:
    1. Check if we're in "work start" mode (branch has Jira issue key)
    2. Check if PR already exists
       - If yes, open in browser
    3. If no PR exists:
       - Generate title and description
       - Create PR
       - Open in browser

    Returns 0 on success, 1 on error.
    """
    preflight = preflight_pr(
        create_anyway=create_anyway,
        labels=labels,
        event_details=event_details,
    )

    if not preflight["ok"]:
        first_issue = preflight["blocking_issues"][0]
        rprint(
            f"[red]Preflight failed ({first_issue['code']}):[/red] "
            f"{first_issue['message']}"
        )
        rprint(f"[cyan]Remediation:[/cyan] {first_issue['remediation']}")
        if event_details is not None:
            event_details["error"] = first_issue["message"]
        return 1

    ctx = resolve_context()
    repo_root = Path(preflight["repo_root"])
    normalized_labels = _normalize_labels(labels)
    if event_details is not None:
        event_details["repo_root"] = str(repo_root)
        event_details["github_repo"] = ctx.github_repo
        event_details["labels"] = normalized_labels

    # Get current branch
    branch = preflight["branch"]["name"]
    if event_details is not None:
        event_details["branch"] = branch

    # Check if we're in "work start" mode (branch has issue key)
    issue_key = preflight["branch"]["issue_key"]
    if event_details is not None:
        event_details["issue_key"] = issue_key

    github_repo = preflight["github_repository"]["resolved_repo"]

    # Get GitHub client
    github = GitHubClient.from_config(ctx.config)
    if not github:
        rprint("[red]Error: GitHub not configured.[/red]")
        rprint(
            "[cyan]Set GITHUB_TOKEN or PWM_GITHUB_TOKEN environment variable.[/cyan]"
        )
        if event_details is not None:
            event_details["error"] = "GitHub not configured"
        return 1

    existing_pr = preflight["existing_pr"]
    if existing_pr["url"] and existing_pr["source"] == "receipt":
        rprint("[cyan]Reusing PR receipt for current branch and HEAD.[/cyan]")
        rprint(existing_pr["url"])
        if event_details is not None:
            event_details["existing_pr"] = True
            event_details["pr_url"] = existing_pr["url"]
            event_details["pr_source"] = "receipt"

        _write_pr_receipt(
            repo_root=repo_root,
            branch=branch,
            head_sha=preflight["receipt"]["head_sha"],
            pr_url=existing_pr["url"],
            labels=normalized_labels,
        )
        if open_browser:
            webbrowser.open(existing_pr["url"])
            rprint("[cyan]Opened in browser[/cyan]")
        return 0

    # Check if PR already exists
    if existing_pr["url"]:
        pr_number = existing_pr["number"]
        pr_url = existing_pr["url"]
        pr_title = existing_pr["title"]

        if normalized_labels and pr_number:
            labels_added = github.add_issue_labels(
                github_repo, pr_number, normalized_labels
            )
            if labels_added:
                rprint(
                    f"[cyan]Applied labels:[/cyan] {', '.join(normalized_labels)}"
                )
            else:
                rprint("[yellow]Warning: Failed to apply PR labels.[/yellow]")
            if event_details is not None:
                event_details["labels_applied"] = labels_added

        if pr_number:
            display_pr_info(github, github_repo, pr_number, pr_title, pr_url)
        else:
            rprint(f"[green]PR:[/green] {pr_title}")
            rprint(pr_url)

        _write_pr_receipt(
            repo_root=repo_root,
            branch=branch,
            head_sha=preflight["receipt"]["head_sha"],
            pr_url=pr_url,
            labels=_normalize_labels(_extract_labels(existing_pr) + normalized_labels),
        )

        if event_details is not None:
            event_details["pr_number"] = pr_number
            event_details["pr_url"] = pr_url
            event_details["existing_pr"] = True
        if open_browser:
            webbrowser.open(pr_url)
            rprint("[cyan]Opened in browser[/cyan]")

        return 0

    # No existing PR - create one
    rprint(f"[cyan]No PR exists for branch '{branch}'[/cyan]")
    if event_details is not None:
        event_details["existing_pr"] = False

    # Get configured remote
    remote = preflight["remote"]["name"]

    # Get base branch
    base_branch_ref = preflight["base_branch"]["ref"]
    base_branch = preflight["base_branch"]["name"]

    # Get commits
    commits = preflight["ahead"]["commits"]
    if event_details is not None:
        event_details["commit_count"] = len(commits)
    if not commits and not create_anyway:
        _debug("no commits found since base branch")
        rprint("[yellow]Warning: No commits found on this branch.[/yellow]")
        if non_interactive:
            rprint(
                "[red]Error: No commits found and non-interactive mode is set. "
                "Use --create-anyway to proceed.[/red]"
            )
            if event_details is not None:
                event_details["error"] = "No commits found"
            return 1

        create_anyway = Confirm.ask("Create PR anyway?", default=False)
        if not create_anyway:
            return 1

    # Get diff (for AI summarization)
    diff = None
    if use_ai:
        diff = get_diff_since_base(repo_root, base_branch_ref, remote)

    # Ensure branch is pushed
    rprint(f"[cyan]Pushing branch '{branch}' to remote...[/cyan]")
    if not push_branch(repo_root, branch, remote):
        _debug(f"push_branch failed for {remote}/{branch}")
        rprint("[red]Error: Failed to push branch to remote.[/red]")
        if event_details is not None:
            event_details["error"] = "Failed to push branch"
        return 1

    # Get Jira client for enhanced title/description
    jira = JiraClient.from_config(ctx.config)
    jira_base_url = ctx.config.get("jira", {}).get("base_url")

    # Get OpenAI client for AI-powered description (optional)
    from pwm.ai.openai_client import OpenAIClient

    openai = OpenAIClient.from_config(ctx.config)

    # Generate AI diff summary once so we can reuse it for terminal output and PR body.
    diff_summary = None
    if openai and use_ai and diff:
        from pwm.ai.summarizer import summarize_diff_for_pr

        diff_summary = summarize_diff_for_pr(diff, openai)

    # Generate title and description
    title = title_override or generate_pr_title(issue_key, jira, commits)
    description = body_override or generate_pr_description(
        issue_key,
        commits,
        jira,
        jira_base_url,
        openai,
        use_ai,
        diff,
        diff_summary=diff_summary,
    )

    if openai and use_ai:
        rprint("[dim]Generated AI summary...[/dim]")

        # Display diff summary if generated
        if diff_summary:
            rprint()
            rprint("[bold cyan]Code Changes:[/bold cyan]")
            rprint(f"[dim]{diff_summary}[/dim]")
            rprint()

    rprint(f"[cyan]Creating PR...[/cyan]")
    rprint(f"  Title: {title}")
    rprint(f"  Base: {base_branch}")
    rprint(f"  Head: {branch}")

    # Create PR
    pr = github.create_pr(
        repo=github_repo, title=title, head=branch, base=base_branch, body=description
    )

    if not pr:
        _debug("github.create_pr returned None")
        rprint("[red]Error: Failed to create PR.[/red]")
        create_error = getattr(github, "last_error", None)
        if create_error:
            rprint(f"[dim]{create_error}[/dim]")
        else:
            rprint("[dim]Check your GitHub permissions and repository access.[/dim]")
        if event_details is not None:
            event_details["error"] = "Failed to create PR"
            if create_error:
                event_details["github_error"] = create_error
        return 1

    pr_number = pr["number"]
    pr_url = pr["html_url"]

    if normalized_labels:
        labels_added = github.add_issue_labels(github_repo, pr_number, normalized_labels)
        if labels_added:
            rprint(f"[cyan]Applied labels:[/cyan] {', '.join(normalized_labels)}")
        else:
            rprint("[yellow]Warning: Failed to apply PR labels.[/yellow]")
        if event_details is not None:
            event_details["labels_applied"] = labels_added

    if event_details is not None:
        event_details["pr_number"] = pr_number
        event_details["pr_url"] = pr_url
        event_details["pr_title"] = title

    display_pr_info(github, github_repo, pr_number, title, pr_url)

    _write_pr_receipt(
        repo_root=repo_root,
        branch=branch,
        head_sha=preflight["receipt"]["head_sha"],
        pr_url=pr_url,
        labels=normalized_labels,
    )

    if open_browser:
        webbrowser.open(pr_url)
        rprint("[cyan]Opened in browser[/cyan]")

    return 0
