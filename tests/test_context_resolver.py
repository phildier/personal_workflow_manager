
from pathlib import Path
import pytest
from pwm.context.resolver import slugify, find_git_root

@pytest.mark.parametrize("text,expected", [
    ("Hello, World!", "hello-world"),
    ("A"*80, "a"*50),
    ("Mix Of CAPS_and  spaces", "mix-of-caps-and-spaces"),
])
def test_slugify(text, expected):
    assert slugify(text) == expected

def test_find_git_root(tmp_path):
    child = tmp_path / "a" / "b" / "c"
    child.mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    assert find_git_root(child) == tmp_path
