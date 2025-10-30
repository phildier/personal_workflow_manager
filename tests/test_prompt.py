
from pathlib import Path
import json
import time
from pwm.commands.prompt import (
    extract_issue_key_from_branch,
    format_prompt,
    PromptFormat,
    get_status_emoji,
    get_status_color,
    Colors,
    get_cached_status,
    set_cached_status,
    CACHE_FILE
)

def test_extract_issue_key_from_branch():
    """Test extracting Jira issue keys from various branch name formats."""
    assert extract_issue_key_from_branch("feature/ABC-123-add-feature") == "ABC-123"
    assert extract_issue_key_from_branch("ABC-123-bug-fix") == "ABC-123"
    assert extract_issue_key_from_branch("bugfix/PROJECT-456") == "PROJECT-456"
    assert extract_issue_key_from_branch("feature/XYZ-999-some-description") == "XYZ-999"
    assert extract_issue_key_from_branch("main") is None
    assert extract_issue_key_from_branch("develop") is None
    assert extract_issue_key_from_branch("feature/no-issue-key") is None

def test_format_prompt_default():
    """Test default format (with brackets)."""
    assert format_prompt("ABC-123", format_type=PromptFormat.DEFAULT) == "[ABC-123]"
    assert format_prompt("ABC-123", status="In Progress", format_type=PromptFormat.DEFAULT) == "[ABC-123: In Progress]"

def test_format_prompt_minimal():
    """Test minimal format (no brackets)."""
    assert format_prompt("ABC-123", format_type=PromptFormat.MINIMAL) == "ABC-123"
    assert format_prompt("ABC-123", status="In Progress", format_type=PromptFormat.MINIMAL) == "ABC-123: In Progress"

def test_format_prompt_emoji():
    """Test emoji format."""
    result = format_prompt("ABC-123", format_type=PromptFormat.EMOJI)
    assert "ABC-123" in result
    assert "🔹" in result

    result_with_status = format_prompt("ABC-123", status="In Progress", format_type=PromptFormat.EMOJI)
    assert "ABC-123" in result_with_status
    assert "🎯" in result_with_status

def test_format_prompt_with_color():
    """Test color formatting."""
    result = format_prompt("ABC-123", use_color=True)
    assert Colors.BLUE in result
    assert Colors.RESET in result
    assert "ABC-123" in result

    result_with_status = format_prompt("ABC-123", status="In Progress", use_color=True)
    assert Colors.YELLOW in result_with_status
    assert Colors.RESET in result_with_status

def test_get_status_emoji():
    """Test emoji selection based on status."""
    assert get_status_emoji("In Progress") == "🎯"
    assert get_status_emoji("Doing") == "🎯"
    assert get_status_emoji("Code Review") == "👀"
    assert get_status_emoji("Testing") == "👀"
    assert get_status_emoji("Done") == "✅"
    assert get_status_emoji("Closed") == "✅"
    assert get_status_emoji("Resolved") == "✅"
    assert get_status_emoji("Blocked") == "🚫"
    assert get_status_emoji("To Do") == "📝"
    assert get_status_emoji("Backlog") == "📝"
    assert get_status_emoji("Unknown Status") == "🔹"

def test_get_status_color():
    """Test color selection based on status."""
    assert get_status_color("In Progress") == Colors.YELLOW
    assert get_status_color("Code Review") == Colors.CYAN
    assert get_status_color("Done") == Colors.GREEN
    assert get_status_color("Blocked") == Colors.RED
    assert get_status_color("To Do") == Colors.BLUE
    assert get_status_color("Unknown") == Colors.GRAY

def test_cache_operations(tmp_path, monkeypatch):
    """Test cache get and set operations."""
    # Use temporary cache file
    cache_file = tmp_path / "test_cache.json"
    monkeypatch.setattr("pwm.commands.prompt.CACHE_FILE", cache_file)
    monkeypatch.setattr("pwm.commands.prompt.CACHE_DIR", tmp_path)

    # Initially no cache
    assert get_cached_status("ABC-123") is None

    # Set cache
    set_cached_status("ABC-123", "In Progress")

    # Should retrieve cached value
    assert get_cached_status("ABC-123") == "In Progress"

    # Test cache expiry
    # Manually modify timestamp to be old
    with cache_file.open('r') as f:
        cache = json.load(f)
    cache["ABC-123"]["timestamp"] = time.time() - 400  # Older than TTL (300s)
    with cache_file.open('w') as f:
        json.dump(cache, f)

    # Should not return expired cache
    assert get_cached_status("ABC-123") is None

def test_cache_file_corruption(tmp_path, monkeypatch):
    """Test that corrupted cache files are handled gracefully."""
    cache_file = tmp_path / "test_cache.json"
    monkeypatch.setattr("pwm.commands.prompt.CACHE_FILE", cache_file)
    monkeypatch.setattr("pwm.commands.prompt.CACHE_DIR", tmp_path)

    # Write corrupted JSON
    cache_file.write_text("{invalid json")

    # Should handle gracefully and return None
    assert get_cached_status("ABC-123") is None

    # Should be able to write new cache
    set_cached_status("ABC-123", "In Progress")
    assert get_cached_status("ABC-123") == "In Progress"
