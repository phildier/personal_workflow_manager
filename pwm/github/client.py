
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import httpx

DEFAULT_GH_API = "https://api.github.com"

@dataclass
class GitHubClient:
    base_url: str
    token: str

    @classmethod
    def from_config(cls, cfg: dict) -> Optional['GitHubClient']:
        gh = cfg.get("github", {})
        token = gh.get("token")
        base_url = gh.get("base_url") or DEFAULT_GH_API
        if not token:
            return None
        return cls(base_url=base_url.rstrip("/"), token=token)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"}

    def ping(self) -> Tuple[bool, str]:
        url = f"{self.base_url}/user"
        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(url, headers=self._headers())
        except Exception as e:
            return False, f"network error: {e}"
        if r.status_code == 200:
            login = r.json().get("login", "<unknown>")
            return True, f"ok (as {login})"
        elif r.status_code == 401:
            return False, "unauthorized (bad token)"
        else:
            return False, f"HTTP {r.status_code}"

    def list_prs(self, repo: str, head: Optional[str] = None, state: str = "open") -> list[dict]:
        """
        List pull requests for a repository.

        Args:
            repo: Repository in "owner/repo" format
            head: Filter by head branch (e.g., "owner:branch-name")
            state: PR state - "open", "closed", or "all"

        Returns list of PR objects with keys: number, title, html_url, head, base, etc.
        """
        url = f"{self.base_url}/repos/{repo}/pulls"
        params = {"state": state}
        if head:
            params["head"] = head

        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(url, headers=self._headers(), params=params)
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return []

    def create_pr(
        self,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None
    ) -> Optional[dict]:
        """
        Create a pull request.

        Args:
            repo: Repository in "owner/repo" format
            title: PR title
            head: Branch containing changes
            base: Base branch to merge into
            body: PR description (optional)

        Returns PR object with keys: number, html_url, etc., or None on failure.
        """
        url = f"{self.base_url}/repos/{repo}/pulls"
        payload = {
            "title": title,
            "head": head,
            "base": base
        }
        if body:
            payload["body"] = body

        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.post(url, headers=self._headers(), json=payload)
                if r.status_code == 201:
                    return r.json()
        except Exception:
            pass
        return None

    def get_pr_for_branch(self, repo: str, branch: str) -> Optional[dict]:
        """
        Get the open PR for a specific branch.

        Args:
            repo: Repository in "owner/repo" format
            branch: Branch name

        Returns PR object or None if no open PR exists.
        """
        # GitHub expects head in "owner:branch" format
        # Extract owner from repo
        owner = repo.split("/")[0] if "/" in repo else repo
        head = f"{owner}:{branch}"

        prs = self.list_prs(repo, head=head, state="open")
        return prs[0] if prs else None
