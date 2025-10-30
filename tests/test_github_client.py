
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
