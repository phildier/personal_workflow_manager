
from __future__ import annotations
from pathlib import Path
import subprocess

def _run(args: list[str], repo_root: Path, capture: bool = True):
    return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=capture, text=True)

def current_branch(repo_root: Path) -> str | None:
    r = _run(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    return r.stdout.strip() if r.returncode == 0 else None

def create_branch(repo_root: Path, branch_name: str, from_ref: str | None = None) -> bool:
    if from_ref is None:
        from_ref = get_default_branch(repo_root)
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

def get_default_branch(repo_root: Path, remote: str = "origin") -> str:
    """
    Determine the default branch for the repository.

    Strategy:
    1. Try to read from remote HEAD reference (git symbolic-ref)
    2. If not set, automatically configure it (git remote set-head)
    3. Fall back to checking common branch names that exist remotely
    4. Default to "main" if all else fails

    Returns the default branch name with remote prefix (e.g., "origin/main")
    """
    # Try to get the default branch from remote HEAD
    r = _run(["symbolic-ref", f"refs/remotes/{remote}/HEAD"], repo_root)
    if r.returncode == 0 and r.stdout.strip():
        # Output is like "refs/remotes/origin/main"
        ref = r.stdout.strip()
        if ref.startswith(f"refs/remotes/{remote}/"):
            branch = ref[len(f"refs/remotes/{remote}/"):]
            return f"{remote}/{branch}"

    # If remote HEAD is not set, try to set it by fetching remote info (suppress stderr)
    r = _run(["remote", "set-head", remote, "-a"], repo_root, capture=True)
    if r.returncode == 0:
        r = _run(["symbolic-ref", f"refs/remotes/{remote}/HEAD"], repo_root)
        if r.returncode == 0 and r.stdout.strip():
            ref = r.stdout.strip()
            if ref.startswith(f"refs/remotes/{remote}/"):
                branch = ref[len(f"refs/remotes/{remote}/"):]
                return f"{remote}/{branch}"

    # Fall back to checking for common default branches
    for candidate in ["main", "master", "develop"]:
        r = _run(["rev-parse", "--verify", f"{remote}/{candidate}"], repo_root)
        if r.returncode == 0:
            return f"{remote}/{candidate}"

    # Ultimate fallback
    return f"{remote}/main"
