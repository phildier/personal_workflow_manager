from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import subprocess

from pwm.config.loader import load_merged_config

@dataclass
class ContextMeta:
    user_config_path: Path | None
    project_config_path: Path | None
    source_summary: str

@dataclass
class Context:
    repo_root: Path
    config: dict
    github_repo: str | None
    jira_project_key: str | None
    meta: ContextMeta

    def branch_for_issue(self, issue_key: str, summary: str | None = None) -> str:
        pattern = (
            self.config.get("branch", {}).get("pattern")
            or "feature/{issue_key}-{slug}"
        )
        slug = slugify(summary or issue_key)
        return pattern.format(issue_key=issue_key, slug=slug)

def resolve_context(cwd: Path | None = None) -> Context:
    cwd = cwd or Path.cwd()
    repo_root = find_git_root(cwd)
    config, meta = load_merged_config(repo_root)

    github_repo = infer_github_repo(repo_root, config)
    jira_project_key = (
        config.get("jira", {}).get("project_key")
        or None
    )

    return Context(
        repo_root=repo_root,
        config=config,
        github_repo=github_repo,
        jira_project_key=jira_project_key,
        meta=meta,
    )

def find_git_root(start: Path) -> Path:
    p = start.resolve()
    for parent in [p] + list(p.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"Not inside a git repository: {start}")

def infer_github_repo(repo_root: Path, config: dict) -> str | None:
    # Allow explicit override in config
    explicit = config.get("github", {}).get("repo")
    if explicit:
        return explicit

    # Fallback to git remote
    try:
        url = subprocess.check_output(
            ["git", "-C", str(repo_root), "remote", "get-url", config.get("git", {}).get("default_remote", "origin")],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return None

    # Support SSH and HTTPS forms
    # git@github.com:org/repo.git  or  https://github.com/org/repo.git
    if url.startswith("git@") and ":" in url:
        path = url.split(":", 1)[1]
    elif url.startswith("http://") or url.startswith("https://"):
        path = url.split("//", 1)[1]
        # drop domain
        path = "/".join(path.split("/", 1)[1:])
    else:
        return None

    path = path[:-4] if path.endswith(".git") else path
    # path now like "org/repo"
    if "/" in path:
        return path
    return None

def slugify(s: str) -> str:
    import re
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50]
