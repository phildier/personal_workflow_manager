from __future__ import annotations


def parse_repo_from_remote_url(url: str) -> str | None:
    """Extract owner/repo from a git remote URL."""
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
