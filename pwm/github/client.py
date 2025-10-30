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
