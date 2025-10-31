
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
    """Test that add_comment_with_link creates proper ADF structure with clickable links."""
    jc = JiraClient(base_url="https://example.atlassian.net", email="u", token="t")

    # Capture the actual payload sent
    captured_payload = None

    class CaptureClient:
        def __enter__(self): return self
        def __exit__(self, *args): pass

        def post(self, url, json=None):
            nonlocal captured_payload
            captured_payload = json
            return FakeResp(201, {"id": "12345"})

    monkeypatch.setattr(JiraClient, "_client", lambda self: CaptureClient())

    result = jc.add_comment_with_link(
        "ABC-1",
        "Status update: Ready for review",
        "View PR #42",
        "https://github.com/org/repo/pull/42"
    )

    assert result is True
    assert captured_payload is not None

    # Validate ADF structure
    body = captured_payload["body"]
    assert body["type"] == "doc"
    assert body["version"] == 1
    assert len(body["content"]) == 2  # Two paragraphs

    # First paragraph - plain text
    first_para = body["content"][0]
    assert first_para["type"] == "paragraph"
    assert first_para["content"][0]["type"] == "text"
    assert first_para["content"][0]["text"] == "Status update: Ready for review"

    # Second paragraph - link
    second_para = body["content"][1]
    assert second_para["type"] == "paragraph"
    assert second_para["content"][0]["type"] == "text"
    assert second_para["content"][0]["text"] == "View PR #42"

    # Validate link markup
    marks = second_para["content"][0]["marks"]
    assert len(marks) == 1
    assert marks[0]["type"] == "link"
    assert marks[0]["attrs"]["href"] == "https://github.com/org/repo/pull/42"
