
from pwm.jira.client import JiraClient

class FakeResp:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}
    def json(self):
        return self._json

class FakeClient:
    def __init__(self, routes):
        self.routes = routes
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def get(self, url):
        for suffix, resp in self.routes.items():
            if url.endswith(suffix):
                return resp
        return FakeResp(404, {})
    def post(self, url, json=None):
        return self.get(url)

def test_ping_ok(monkeypatch):
    jc = JiraClient(base_url="https://example.atlassian.net", email="u", token="t")
    routes = {"/rest/api/3/myself": FakeResp(200, {"displayName": "User"})}
    monkeypatch.setattr(JiraClient, "_client", lambda self: FakeClient(routes))
    ok, msg = jc.ping()
    assert ok is True
    assert "ok" in msg

def test_get_issue_summary(monkeypatch):
    jc = JiraClient(base_url="https://example.atlassian.net", email="u", token="t")
    routes = {"/rest/api/3/issue/ABC-1": FakeResp(200, {"fields": {"summary": "Do the thing"}})}
    monkeypatch.setattr(JiraClient, "_client", lambda self: FakeClient(routes))
    assert jc.get_issue_summary("ABC-1") == "Do the thing"

def test_add_comment_with_link(monkeypatch):
    jc = JiraClient(base_url="https://example.atlassian.net", email="u", token="t")
    routes = {"/rest/api/3/issue/ABC-1/comment": FakeResp(201, {"id": "12345"})}
    monkeypatch.setattr(JiraClient, "_client", lambda self: FakeClient(routes))
    result = jc.add_comment_with_link("ABC-1", "Status update", "View PR", "https://github.com/org/repo/pull/1")
    assert result is True
