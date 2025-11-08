
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime
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

    def get_current_user(self) -> Optional[str]:
        """
        Get the current authenticated user's login (username).

        Returns the GitHub username or None on failure.
        """
        url = f"{self.base_url}/user"
        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(url, headers=self._headers())
                if r.status_code == 200:
                    return r.json().get("login")
        except Exception:
            pass
        return None

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

    def get_pr_for_branch(self, repo: str, branch: str, state: str = "open") -> Optional[dict]:
        """
        Get the PR for a specific branch.

        Args:
            repo: Repository in "owner/repo" format
            branch: Branch name
            state: PR state - "open", "closed", or "all" (default: "open")

        Returns PR object or None if no PR exists.
        """
        # GitHub expects head in "owner:branch" format
        # Extract owner from repo
        owner = repo.split("/")[0] if "/" in repo else repo
        head = f"{owner}:{branch}"

        prs = self.list_prs(repo, head=head, state=state)
        return prs[0] if prs else None

    def get_pr_details(self, repo: str, pr_number: int) -> Optional[dict]:
        """
        Get detailed PR information including file stats.

        Args:
            repo: Repository in "owner/repo" format
            pr_number: PR number

        Returns PR object with additions, deletions, changed_files, etc.
        """
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"

        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(url, headers=self._headers())
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return None

    def get_pr_reviews(self, repo: str, pr_number: int) -> list[dict]:
        """
        Get reviews for a pull request.

        Args:
            repo: Repository in "owner/repo" format
            pr_number: PR number

        Returns list of review objects with user, state, etc.
        """
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}/reviews"

        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(url, headers=self._headers())
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return []

    def get_pr_comments(self, repo: str, pr_number: int) -> list[dict]:
        """
        Get comments on a pull request.

        Args:
            repo: Repository in "owner/repo" format
            pr_number: PR number

        Returns list of comment objects with keys: id, body, created_at, user, etc.
        """
        url = f"{self.base_url}/repos/{repo}/issues/{pr_number}/comments"

        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(url, headers=self._headers())
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return []

    def add_pr_comment(self, repo: str, pr_number: int, body: str) -> Optional[dict]:
        """
        Add a comment to a pull request.

        Args:
            repo: Repository in "owner/repo" format
            pr_number: PR number
            body: Comment text

        Returns comment object or None on failure.
        """
        url = f"{self.base_url}/repos/{repo}/issues/{pr_number}/comments"

        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.post(url, headers=self._headers(), json={"body": body})
                if r.status_code == 201:
                    return r.json()
        except Exception:
            pass
        return None

    def request_reviewers(
        self,
        repo: str,
        pr_number: int,
        reviewers: Optional[list[str]] = None,
        team_reviewers: Optional[list[str]] = None
    ) -> bool:
        """
        Request reviewers for a pull request.

        Args:
            repo: Repository in "owner/repo" format
            pr_number: PR number
            reviewers: List of user logins
            team_reviewers: List of team slugs

        Returns True if successful, False otherwise.
        """
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}/requested_reviewers"
        payload = {}
        if reviewers:
            payload["reviewers"] = reviewers
        if team_reviewers:
            payload["team_reviewers"] = team_reviewers

        if not payload:
            return False

        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.post(url, headers=self._headers(), json=payload)
                return r.status_code in (201, 200)
        except Exception:
            pass
        return False

    def get_last_pwm_comment_time(self, repo: str, pr_number: int) -> Optional[datetime]:
        """
        Get the timestamp of the most recent pwm-generated comment on a PR.

        Looks for comments containing the marker "<!-- pwm:work-end -->" and
        returns the created_at timestamp of the most recent one.

        Args:
            repo: Repository in "owner/repo" format
            pr_number: PR number

        Returns datetime of the most recent pwm comment, or None if no pwm comments found.
        """
        comments = self.get_pr_comments(repo, pr_number)

        pwm_comments = []
        for comment in comments:
            body = comment.get("body", "")
            if "<!-- pwm:work-end -->" in body:
                created_at_str = comment.get("created_at")
                if created_at_str:
                    try:
                        # GitHub returns ISO 8601 format: "2024-01-15T10:30:45Z"
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        pwm_comments.append(created_at)
                    except Exception:
                        continue

        return max(pwm_comments) if pwm_comments else None

    def search_prs_by_date(
        self,
        repo: Optional[str],
        since: datetime,
        author: Optional[str] = None,
        state: str = "all",
        org: Optional[str] = None
    ) -> list[dict]:
        """
        Search for PRs created since a given date.

        Args:
            repo: Repository in "owner/repo" format (optional if org provided)
            since: Only return PRs created after this timestamp
            author: Filter by PR author (GitHub username)
            state: PR state - "open", "closed", or "all"
            org: Organization to search across (searches all repos if provided instead of repo)

        Returns list of PR objects.
        """
        # Use GitHub Search API: GET /search/issues
        # Query: repo:owner/repo is:pr created:>=YYYY-MM-DDTHH:MM:SS
        # Or:    org:owner is:pr created:>=YYYY-MM-DDTHH:MM:SS
        url = f"{self.base_url}/search/issues"
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S")

        query_parts = [
            "is:pr",
            f"created:>={since_str}"
        ]

        # Either search by org or by specific repo
        if org:
            query_parts.insert(0, f"org:{org}")
        elif repo:
            query_parts.insert(0, f"repo:{repo}")
        else:
            # Must have either org or repo
            return []

        if author:
            query_parts.append(f"author:{author}")

        if state != "all":
            query_parts.append(f"is:{state}")

        params = {
            "q": " ".join(query_parts),
            "sort": "created",
            "order": "desc",
            "per_page": 100
        }

        results = []
        try:
            with httpx.Client(timeout=30.0) as c:
                # Handle pagination
                page = 1
                while True:
                    params["page"] = page
                    r = c.get(url, headers=self._headers(), params=params)

                    if r.status_code != 200:
                        break

                    data = r.json()
                    items = data.get("items", [])

                    if not items:
                        break

                    results.extend(items)

                    # Check if there are more pages
                    if len(items) < params["per_page"]:
                        break

                    page += 1

                    # Safety limit: max 10 pages (1000 results)
                    if page > 10:
                        break
        except Exception:
            pass

        return results

    def get_closed_prs(
        self,
        repo: Optional[str],
        since: datetime,
        author: Optional[str] = None,
        org: Optional[str] = None
    ) -> list[dict]:
        """
        Get PRs closed/merged since a given date.

        Args:
            repo: Repository in "owner/repo" format (optional if org provided)
            since: Only return PRs closed after this timestamp
            author: Filter by PR author (GitHub username)
            org: Organization to search across (searches all repos if provided instead of repo)

        Returns list of closed/merged PR objects.
        """
        # Use GitHub Search API with merged filter for merged PRs
        # Query: repo:owner/repo is:pr is:merged merged:>=YYYY-MM-DDTHH:MM:SS
        # Or:    org:owner is:pr is:merged merged:>=YYYY-MM-DDTHH:MM:SS
        # Then do a second search for closed-but-not-merged
        url = f"{self.base_url}/search/issues"
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S")

        # First search: merged PRs
        query_parts_merged = [
            "is:pr",
            "is:merged",
            f"merged:>={since_str}"
        ]

        # Second search: closed but not merged PRs
        query_parts_closed = [
            "is:pr",
            "is:closed",
            "is:unmerged",
            f"closed:>={since_str}"
        ]

        # Add scope (org or repo) to both queries
        scope_part = []
        if org:
            scope_part = [f"org:{org}"]
        elif repo:
            scope_part = [f"repo:{repo}"]
        else:
            # Must have either org or repo
            return []

        # Add author filter if specified
        author_part = [f"author:{author}"] if author else []

        # Build complete queries
        query_merged = " ".join(scope_part + query_parts_merged + author_part)
        query_closed = " ".join(scope_part + query_parts_closed + author_part)

        results = []

        # Helper function to fetch PRs for a query
        def fetch_prs_for_query(query: str) -> list[dict]:
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 100
            }
            prs = []
            try:
                with httpx.Client(timeout=30.0) as c:
                    page = 1
                    while True:
                        params["page"] = page
                        r = c.get(url, headers=self._headers(), params=params)

                        if r.status_code != 200:
                            break

                        data = r.json()
                        items = data.get("items", [])

                        if not items:
                            break

                        # Extract repo from html_url for cross-repo searches
                        for item in items:
                            html_url = item.get("html_url", "")
                            if html_url:
                                # Parse repo from URL: https://github.com/org/repo/pull/123
                                parts = html_url.split("/")
                                if len(parts) >= 7:
                                    item_repo = f"{parts[3]}/{parts[4]}"
                                    pr_number = item.get("number")
                                    if pr_number:
                                        pr_details = self.get_pr_details(item_repo, pr_number)
                                        if pr_details:
                                            prs.append(pr_details)
                                        else:
                                            prs.append(item)

                        # Check if there are more pages
                        if len(items) < params["per_page"]:
                            break

                        page += 1

                        # Safety limit: max 10 pages (1000 results)
                        if page > 10:
                            break
            except Exception:
                pass
            return prs

        # Fetch both merged and closed PRs
        results.extend(fetch_prs_for_query(query_merged))
        results.extend(fetch_prs_for_query(query_closed))

        return results
