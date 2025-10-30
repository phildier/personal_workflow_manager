
from __future__ import annotations
from pathlib import Path
import subprocess

def _run(args: list[str], repo_root: Path, capture: bool = True):
    return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=capture, text=True)

def current_branch(repo_root: Path) -> str | None:
    r = _run(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    return r.stdout.strip() if r.returncode == 0 else None

def create_branch(repo_root: Path, branch_name: str, from_ref: str = "origin/main") -> bool:
    r = _run(["checkout", "-b", branch_name, from_ref], repo_root, capture=False)
    return r.returncode == 0

def switch_branch(repo_root: Path, branch_name: str) -> bool:
    r = _run(["checkout", branch_name], repo_root, capture=False)
    return r.returncode == 0

def branch_exists(repo_root: Path, branch_name: str) -> bool:
    r = _run(["rev-parse", "--verify", branch_name], repo_root)
    return r.returncode == 0

def infer_github_repo_from_remote(repo_root: Path, remote: str = "origin") -> str | None:
    r = _run(["remote", "get-url", remote], repo_root)
    if r.returncode != 0:
        return None
    url = r.stdout.strip()
    if url.startswith("git@") and ":" in url:
        path = url.split(":", 1)[1]
    elif url.startswith("http://") or url.startswith("https://"):
        part = url.split("//", 1)[1]
        path = "/".join(part.split("/", 1)[1:])
    else:
        return None
    if path.endswith(".git"):
        path = path[:-4]
    return path if "/" in path else None
