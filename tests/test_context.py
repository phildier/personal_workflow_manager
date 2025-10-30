from pathlib import Path
import pytest
from pwm.context.resolver import slugify

@pytest.mark.parametrize("text,expected", [
    ("Hello, World!", "hello-world"),
    ("A"*80, ("a"*50)),
])
def test_slugify(text, expected):
    assert slugify(text) == expected
