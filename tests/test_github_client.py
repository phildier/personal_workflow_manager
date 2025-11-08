
import httpx
from pwm.github.client import GitHubClient

class FakeResp:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}
    def json(self):
        return self._json

class FakeClient:
    def __init__(self, resp):
        self.resp = resp
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def get(self, url, headers=None):
        return self.resp

def test_ping_ok(monkeypatch):
    gh = GitHubClient(base_url="https://api.github.com", token="t")
    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: FakeClient(FakeResp(200, {"login": "me"})))
    ok, msg = gh.ping()
    assert ok is True
    assert "ok" in msg

def test_ping_unauthorized(monkeypatch):
    gh = GitHubClient(base_url="https://api.github.com", token="t")
    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: FakeClient(FakeResp(401, {})))
    ok, msg = gh.ping()
    assert ok is False

def test_get_current_user_success(monkeypatch):
    gh = GitHubClient(base_url="https://api.github.com", token="t")
    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: FakeClient(FakeResp(200, {"login": "testuser"})))
    username = gh.get_current_user()
    assert username == "testuser"

def test_get_current_user_failure(monkeypatch):
    gh = GitHubClient(base_url="https://api.github.com", token="t")
    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: FakeClient(FakeResp(401, {})))
    username = gh.get_current_user()
    assert username is None

def test_search_prs_by_date(monkeypatch):
    from datetime import datetime
    gh = GitHubClient(base_url="https://api.github.com", token="t")

    class FakeSearchClient:
        def __init__(self):
            pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, headers=None, params=None):
            # Verify query contains expected parameters
            if "/search/issues" in url and params:
                query = params.get("q", "")
                assert "repo:org/repo" in query
                assert "is:pr" in query
                assert "created:>=" in query
                return FakeResp(200, {
                    "items": [
                        {"number": 1, "title": "Test PR 1"},
                        {"number": 2, "title": "Test PR 2"}
                    ]
                })
            return FakeResp(404, {})

    monkeypatch.setattr(httpx, "Client", lambda timeout=30.0: FakeSearchClient())
    since = datetime(2025, 1, 10, 0, 0)
    results = gh.search_prs_by_date("org/repo", since)

    assert len(results) == 2
    assert results[0]["number"] == 1
    assert results[1]["title"] == "Test PR 2"

def test_search_prs_by_date_with_author(monkeypatch):
    from datetime import datetime
    gh = GitHubClient(base_url="https://api.github.com", token="t")

    class FakeSearchClient:
        def __init__(self):
            pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, headers=None, params=None):
            if "/search/issues" in url and params:
                query = params.get("q", "")
                assert "author:testuser" in query
                return FakeResp(200, {"items": [{"number": 1, "title": "My PR"}]})
            return FakeResp(404, {})

    monkeypatch.setattr(httpx, "Client", lambda timeout=30.0: FakeSearchClient())
    since = datetime(2025, 1, 10, 0, 0)
    results = gh.search_prs_by_date("org/repo", since, author="testuser")

    assert len(results) == 1
    assert results[0]["number"] == 1

def test_get_closed_prs(monkeypatch):
    from datetime import datetime
    gh = GitHubClient(base_url="https://api.github.com", token="t")

    call_count = {"search": 0, "details": 0}

    class FakeClosedPRClient:
        def __init__(self):
            pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, headers=None, params=None):
            # Handle search API call - now expects 2 searches: merged and unmerged
            if "/search/issues" in url and params:
                call_count["search"] += 1
                query = params.get("q", "")
                # First search: merged PRs
                if "is:merged" in query:
                    assert "merged:>=" in query
                    return FakeResp(200, {
                        "items": [
                            {"number": 2, "title": "Merged PR", "html_url": "https://github.com/org/repo/pull/2"}
                        ]
                    })
                # Second search: closed but not merged PRs
                elif "is:unmerged" in query:
                    assert "is:closed" in query
                    assert "closed:>=" in query
                    return FakeResp(200, {
                        "items": [
                            {"number": 1, "title": "Closed PR", "html_url": "https://github.com/org/repo/pull/1"}
                        ]
                    })
            # Handle PR details calls
            elif "/repos/org/repo/pulls/" in url:
                call_count["details"] += 1
                if "/pulls/1" in url:
                    return FakeResp(200, {"number": 1, "title": "Closed PR", "merged_at": None})
                elif "/pulls/2" in url:
                    return FakeResp(200, {"number": 2, "title": "Merged PR", "merged_at": "2025-01-11T10:00:00Z"})
            return FakeResp(404, {})

    monkeypatch.setattr(httpx, "Client", lambda timeout=30.0: FakeClosedPRClient())
    since = datetime(2025, 1, 10, 0, 0)
    results = gh.get_closed_prs("org/repo", since)

    assert len(results) == 2
    assert call_count["search"] == 2  # Now expects 2 searches (merged + unmerged)
    assert call_count["details"] == 2  # Should fetch details for each PR
