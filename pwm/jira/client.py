from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import os
import sys
import httpx


@dataclass
class JiraClient:
    base_url: str
    email: str
    token: str

    def _debug(self, message: str) -> None:
        """Emit debug diagnostics when PWM_DEBUG is enabled."""
        if os.getenv("PWM_DEBUG") == "1":
            print(f"[DEBUG] JiraClient: {message}", file=sys.stderr)

    @classmethod
    def from_config(cls, cfg: dict) -> Optional["JiraClient"]:
        jira = cfg.get("jira", {})
        base_url, email, token = (
            jira.get("base_url"),
            jira.get("email"),
            jira.get("token"),
        )
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
            self._debug(f"ping network error: {type(e).__name__}")
            return False, f"network error: {e}"
        if r.status_code == 200:
            acc = r.json().get("displayName") or r.json().get(
                "emailAddress", "<unknown>"
            )
            return True, f"ok (as {acc})"
        elif r.status_code == 401:
            self._debug("ping unauthorized (401)")
            return False, "unauthorized (bad token)"
        else:
            self._debug(f"ping returned HTTP {r.status_code}")
            return False, f"HTTP {r.status_code}"

    def get_current_account_id(self) -> Optional[str]:
        """
        Get the accountId of the current authenticated user.

        Returns the accountId (required for setting assignee in Jira Cloud) or None on failure.
        """
        url = f"{self.base_url}/rest/api/3/myself"
        try:
            with self._client() as c:
                r = c.get(url)
                if r.status_code == 200:
                    return r.json().get("accountId")
                self._debug(f"get_current_account_id returned HTTP {r.status_code}")
        except Exception:
            self._debug("get_current_account_id request raised exception")
        return None

    def get_issue(self, key: str) -> Optional[dict]:
        url = f"{self.base_url}/rest/api/3/issue/{key}"
        try:
            with self._client() as c:
                r = c.get(url)
                if r.status_code == 200:
                    return r.json()
                self._debug(f"get_issue {key} returned HTTP {r.status_code}")
        except Exception:
            self._debug(f"get_issue {key} request raised exception")
        return None

    def get_issue_summary(self, key: str) -> Optional[str]:
        data = self.get_issue(key)
        if not data:
            return None
        fields = data.get("fields") or {}
        return fields.get("summary")

    def _transitions(self, key: str) -> list[dict]:
        url = f"{self.base_url}/rest/api/3/issue/{key}/transitions"
        try:
            with self._client() as c:
                r = c.get(url)
                if r.status_code == 200:
                    return r.json().get("transitions", [])
                self._debug(f"_transitions for {key} returned HTTP {r.status_code}")
        except Exception:
            self._debug(f"_transitions for {key} request raised exception")
        return []

    def transition_by_name(self, key: str, name: str) -> bool:
        transitions = self._transitions(key)
        tid = None
        for t in transitions:
            if t.get("name", "").lower() == name.lower():
                tid = t.get("id")
                break
        if not tid:
            self._debug(f"transition '{name}' not found for {key}")
            return False
        url = f"{self.base_url}/rest/api/3/issue/{key}/transitions"
        try:
            with self._client() as c:
                r = c.post(url, json={"transition": {"id": tid}})
                return r.status_code in (204, 200)
        except Exception:
            self._debug(f"transition_by_name {key} request raised exception")
        return False

    def assign_issue(self, key: str, account_id: str) -> bool:
        """
        Assign an issue to a user.

        Args:
            key: Issue key (e.g., "ABC-123")
            account_id: User's accountId (required for Jira Cloud)

        Returns True if successful, False otherwise.
        """
        url = f"{self.base_url}/rest/api/3/issue/{key}/assignee"
        try:
            with self._client() as c:
                r = c.put(url, json={"accountId": account_id})
                return r.status_code in (204, 200)
        except Exception:
            self._debug(f"assign_issue {key} request raised exception")
        return False

    def add_comment(self, key: str, body: str) -> bool:
        url = f"{self.base_url}/rest/api/3/issue/{key}/comment"
        # Jira API v3 requires Atlassian Document Format (ADF)
        adf_body = {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": body}]}
            ],
        }
        try:
            with self._client() as c:
                r = c.post(url, json={"body": adf_body})
                return r.status_code in (201, 200)
        except Exception:
            self._debug(f"add_comment {key} request raised exception")
        return False

    def add_comment_with_link(
        self, key: str, text: str, link_text: str, link_url: str
    ) -> bool:
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
                {"type": "paragraph", "content": [{"type": "text", "text": text}]},
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": link_text,
                            "marks": [{"type": "link", "attrs": {"href": link_url}}],
                        }
                    ],
                },
            ],
        }
        try:
            with self._client() as c:
                r = c.post(url, json={"body": adf_body})
                return r.status_code in (201, 200)
        except Exception:
            self._debug(f"add_comment_with_link {key} request raised exception")
        return False

    def get_issue_types(self, project_key: str) -> list[dict]:
        """
        Get available issue types for a project.

        Returns a list of dicts with 'id', 'name', and 'description'.
        """
        url = f"{self.base_url}/rest/api/3/issue/createmeta"
        params = {"projectKeys": project_key, "expand": "projects.issuetypes"}
        try:
            with self._client() as c:
                r = c.get(url, params=params)
                if r.status_code != 200:
                    self._debug(
                        f"get_issue_types for {project_key} returned HTTP {r.status_code}"
                    )
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
                        "description": it.get("description", ""),
                    }
                    for it in issue_types
                ]
        except Exception:
            self._debug(f"get_issue_types for {project_key} request raised exception")
        return []

    def get_create_metadata(self, project_key: str, issue_type_name: str) -> dict:
        """
        Get field metadata for creating an issue.

        Returns a dict with field information including required fields and allowed values.
        """
        url = f"{self.base_url}/rest/api/3/issue/createmeta"
        params = {
            "projectKeys": project_key,
            "issuetypeNames": issue_type_name,
            "expand": "projects.issuetypes.fields",
        }
        try:
            with self._client() as c:
                r = c.get(url, params=params)
                if r.status_code != 200:
                    self._debug(
                        "get_create_metadata for "
                        f"{project_key}/{issue_type_name} returned HTTP {r.status_code}"
                    )
                    return {}
                data = r.json()
                projects = data.get("projects", [])
                if not projects:
                    return {}
                issue_types = projects[0].get("issuetypes", [])
                if not issue_types:
                    return {}
                return issue_types[0].get("fields", {})
        except Exception:
            self._debug(
                f"get_create_metadata for {project_key}/{issue_type_name} request raised exception"
            )
        return {}

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Story",
        description: Optional[str] = None,
        labels: Optional[list[str]] = None,
        custom_fields: Optional[dict] = None,
        assign_to_self: bool = True,
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
            assign_to_self: Assign the issue to the current user (default: True)

        Returns the issue key (e.g., "ABC-123") if successful, None otherwise.
        """
        url = f"{self.base_url}/rest/api/3/issue"

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        # Assign to current user if requested
        if assign_to_self:
            account_id = self.get_current_account_id()
            if account_id:
                fields["assignee"] = {"accountId": account_id}

        if description:
            # Jira API v3 uses Atlassian Document Format (ADF)
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
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
                    # Keep logs concise and avoid leaking response bodies.
                    self._debug(
                        f"create_issue for {project_key} returned HTTP {r.status_code}"
                    )
                    print(f"[DEBUG] Jira API error {r.status_code}", file=sys.stderr)
                    return None
        except Exception as e:
            self._debug(
                f"create_issue for {project_key} raised {type(e).__name__}"
            )
            print(
                f"[DEBUG] Exception creating issue: {type(e).__name__}",
                file=sys.stderr,
            )
            return None

    def search_issues_by_date(self, jql: str, max_results: int = 100) -> list[dict]:
        """
        Search Jira issues using JQL.

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return (default: 100)

        Returns list of issue objects with fields: key, summary, status, created, updated, assignee
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "key,summary,status,created,updated,assignee",
        }

        try:
            with self._client() as c:
                r = c.get(url, params=params)
                if r.status_code == 200:
                    data = r.json()
                    issues = data.get("issues", [])
                    # Flatten the structure for easier use
                    result = []
                    for issue in issues:
                        fields = issue.get("fields", {})
                        result.append(
                            {
                                "key": issue.get("key"),
                                "summary": fields.get("summary"),
                                "status": fields.get("status"),
                                "created": fields.get("created"),
                                "updated": fields.get("updated"),
                                "assignee": fields.get("assignee"),
                            }
                        )
                    return result
                self._debug(f"search_issues_by_date returned HTTP {r.status_code}")
        except Exception:
            self._debug("search_issues_by_date request raised exception")

        return []

    def get_issues_created_since(
        self,
        project_keys: str | list[str],
        since: datetime,
        assignee: Optional[str] = "currentUser()",
    ) -> list[dict]:
        """
        Get issues created since a given date.

        Args:
            project_keys: Jira project key(s) (e.g., "ABC" or ["ABC", "XYZ"])
            since: Only return issues created after this timestamp
            assignee: Filter by assignee (default: "currentUser()") - use None for all users

        Returns list of issue objects.
        """
        since_str = since.strftime("%Y-%m-%d %H:%M")

        # Handle multiple projects
        if isinstance(project_keys, list):
            if not project_keys:
                return []
            project_filter = f"project in ({', '.join(project_keys)})"
        else:
            project_filter = f"project = {project_keys}"

        jql = f'{project_filter} AND created >= "{since_str}"'
        if assignee:
            jql += f" AND assignee = {assignee}"

        return self.search_issues_by_date(jql)

    def get_issues_updated_since(
        self,
        project_keys: str | list[str],
        since: datetime,
        assignee: Optional[str] = "currentUser()",
    ) -> list[dict]:
        """
        Get issues updated since a given date (excluding newly created).

        Args:
            project_keys: Jira project key(s) (e.g., "ABC" or ["ABC", "XYZ"])
            since: Only return issues updated after this timestamp
            assignee: Filter by assignee (default: "currentUser()") - use None for all users

        Returns list of issue objects.
        """
        since_str = since.strftime("%Y-%m-%d %H:%M")

        # Handle multiple projects
        if isinstance(project_keys, list):
            if not project_keys:
                return []
            project_filter = f"project in ({', '.join(project_keys)})"
        else:
            project_filter = f"project = {project_keys}"

        jql = (
            f'{project_filter} AND updated >= "{since_str}" AND created < "{since_str}"'
        )
        if assignee:
            jql += f" AND assignee = {assignee}"

        return self.search_issues_by_date(jql)
