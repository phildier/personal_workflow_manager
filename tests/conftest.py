
import contextlib
from pathlib import Path

class DummyRunResult:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""

@contextlib.contextmanager
def temp_cwd(tmp_path):
    old = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        yield tmp_path
    finally:
        os.chdir(old)

def make_git_repo(tmp_path):
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)
    return tmp_path
