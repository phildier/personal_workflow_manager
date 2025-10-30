
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import httpx

@dataclass
class JiraClient:
    base_url: str
    email: str
    token: str

    @classmethod
    def from_config(cls, cfg: dict) -> Optional['JiraClient']:
        jira = cfg.get("jira", {})
        base_url, email, token = jira.get("base_url"), jira.get("email"), jira.get("token")
        if not (base_url and email and token):
            return None
        return cls(base_url=base_url.rstrip("/"), email=email, token=token)

    def _client(self) -> httpx.Client:
        return httpx.Client(auth=(self.email, self.token), timeout=20.0)

    def ping(self) -> tuple[bool, str]:
        url = f"{self.base_url}/rest/api/3/myself"
        try:
            with self._client() as c:
                r = c.get(url)
        except Exception as e:
            return False, f"network error: {e}"
        if r.status_code == 200:
            acc = r.json().get("displayName") or r.json().get("emailAddress", "<unknown>")
            return True, f"ok (as {acc})"
        elif r.status_code == 401:
            return False, "unauthorized (bad token)"
        else:
            return False, f"HTTP {r.status_code}"

    def get_issue(self, key: str) -> Optional[dict]:
        url = f"{self.base_url}/rest/api/3/issue/{key}"
        with self._client() as c:
            r = c.get(url)
            if r.status_code == 200:
                return r.json()
        return None

    def get_issue_summary(self, key: str) -> Optional[str]:
        data = self.get_issue(key)
        if not data:
            return None
        fields = data.get("fields") or {}
        return fields.get("summary")

    def _transitions(self, key: str) -> list[dict]:
        url = f"{self.base_url}/rest/api/3/issue/{key}/transitions"
        with self._client() as c:
            r = c.get(url)
            if r.status_code == 200:
                return r.json().get("transitions", [])
        return []

    def transition_by_name(self, key: str, name: str) -> bool:
        transitions = self._transitions(key)
        tid = None
        for t in transitions:
            if t.get("name", "").lower() == name.lower():
                tid = t.get("id")
                break
        if not tid:
            return False
        url = f"{self.base_url}/rest/api/3/issue/{key}/transitions"
        with self._client() as c:
            r = c.post(url, json={"transition": {"id": tid}})
            return r.status_code in (204, 200)

    def add_comment(self, key: str, body: str) -> bool:
        url = f"{self.base_url}/rest/api/3/issue/{key}/comment"
        with self._client() as c:
            r = c.post(url, json={"body": body})
            return r.status_code in (201, 200)
