
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
        # Jira API v3 requires Atlassian Document Format (ADF)
        adf_body = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": body
                        }
                    ]
                }
            ]
        }
        with self._client() as c:
            r = c.post(url, json={"body": adf_body})
            return r.status_code in (201, 200)

    def add_comment_with_link(self, key: str, text: str, link_text: str, link_url: str) -> bool:
        """
        Add a comment with a clickable link.

        Args:
            key: Jira issue key
            text: Main comment text
            link_text: Text to display for the link
            link_url: URL for the link

        Returns True if successful, False otherwise.
        """
        url = f"{self.base_url}/rest/api/3/issue/{key}/comment"
        # Build ADF with text and clickable link
        adf_body = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": link_text,
                            "marks": [
                                {
                                    "type": "link",
                                    "attrs": {
                                        "href": link_url
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        with self._client() as c:
            r = c.post(url, json={"body": adf_body})
            return r.status_code in (201, 200)

    def get_issue_types(self, project_key: str) -> list[dict]:
        """
        Get available issue types for a project.

        Returns a list of dicts with 'id', 'name', and 'description'.
        """
        url = f"{self.base_url}/rest/api/3/issue/createmeta"
        params = {"projectKeys": project_key, "expand": "projects.issuetypes"}
        with self._client() as c:
            r = c.get(url, params=params)
            if r.status_code != 200:
                return []
            data = r.json()
            projects = data.get("projects", [])
            if not projects:
                return []
            issue_types = projects[0].get("issuetypes", [])
            return [
                {
                    "id": it.get("id"),
                    "name": it.get("name"),
                    "description": it.get("description", "")
                }
                for it in issue_types
            ]

    def get_create_metadata(self, project_key: str, issue_type_name: str) -> dict:
        """
        Get field metadata for creating an issue.

        Returns a dict with field information including required fields and allowed values.
        """
        url = f"{self.base_url}/rest/api/3/issue/createmeta"
        params = {
            "projectKeys": project_key,
            "issuetypeNames": issue_type_name,
            "expand": "projects.issuetypes.fields"
        }
        with self._client() as c:
            r = c.get(url, params=params)
            if r.status_code != 200:
                return {}
            data = r.json()
            projects = data.get("projects", [])
            if not projects:
                return {}
            issue_types = projects[0].get("issuetypes", [])
            if not issue_types:
                return {}
            return issue_types[0].get("fields", {})

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Story",
        description: Optional[str] = None,
        labels: Optional[list[str]] = None,
        custom_fields: Optional[dict] = None
    ) -> Optional[str]:
        """
        Create a new Jira issue.

        Args:
            project_key: Jira project key
            summary: Issue summary
            issue_type: Issue type name (e.g., "Story", "Bug")
            description: Issue description
            labels: List of labels
            custom_fields: Dict of custom field IDs to values (e.g., {"customfield_10370": {"value": "Team A"}})

        Returns the issue key (e.g., "ABC-123") if successful, None otherwise.
        """
        url = f"{self.base_url}/rest/api/3/issue"

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type}
        }

        if description:
            # Jira API v3 uses Atlassian Document Format (ADF)
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            }

        if labels:
            fields["labels"] = labels

        # Add custom fields
        if custom_fields:
            fields.update(custom_fields)

        payload = {"fields": fields}

        try:
            with self._client() as c:
                r = c.post(url, json=payload)
                if r.status_code in (201, 200):
                    data = r.json()
                    return data.get("key")
                else:
                    # Log the error for debugging
                    import sys
                    print(f"[DEBUG] Jira API error {r.status_code}: {r.text}", file=sys.stderr)
                    return None
        except Exception as e:
            import sys
            print(f"[DEBUG] Exception creating issue: {e}", file=sys.stderr)
            return None
