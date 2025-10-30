
from __future__ import annotations
from pathlib import Path
import re
import sys
from enum import Enum
from typing import Optional
import time
import json

from pwm.context.resolver import find_git_root
from pwm.vcs.git_cli import current_branch
from pwm.jira.client import JiraClient
from pwm.context.resolver import resolve_context

class PromptFormat(str, Enum):
    DEFAULT = "default"
    MINIMAL = "minimal"
    EMOJI = "emoji"

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    RED = "\033[31m"
    GRAY = "\033[90m"

# Cache file location
CACHE_DIR = Path.home() / ".cache" / "pwm"
CACHE_FILE = CACHE_DIR / "prompt_cache.json"
CACHE_TTL = 300  # 5 minutes

def extract_issue_key_from_branch(branch_name: str) -> Optional[str]:
    """
    Extract Jira issue key from branch name.

    Looks for patterns like ABC-123, PROJECT-456, etc.
    Common formats:
    - feature/ABC-123-description
    - ABC-123-description
    - bugfix/ABC-123
    """
    # Match Jira issue key pattern: 1+ uppercase letters, dash, 1+ digits
    match = re.search(r'([A-Z]+)-(\d+)', branch_name)
    if match:
        return match.group(0)
    return None

def get_cached_status(issue_key: str) -> Optional[str]:
    """Get cached Jira status if available and not expired."""
    if not CACHE_FILE.exists():
        return None

    try:
        with CACHE_FILE.open('r') as f:
            cache = json.load(f)

        if issue_key in cache:
            entry = cache[issue_key]
            if time.time() - entry['timestamp'] < CACHE_TTL:
                return entry['status']
    except (json.JSONDecodeError, KeyError, OSError):
        pass

    return None

def set_cached_status(issue_key: str, status: str) -> None:
    """Cache Jira status for an issue."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache = {}
    if CACHE_FILE.exists():
        try:
            with CACHE_FILE.open('r') as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    cache[issue_key] = {
        'status': status,
        'timestamp': time.time()
    }

    try:
        with CACHE_FILE.open('w') as f:
            json.dump(cache, f)
    except OSError:
        pass  # Silent fail if we can't write cache

def get_status_emoji(status: str) -> str:
    """Get emoji for Jira status."""
    status_lower = status.lower().replace(' ', '')
    if 'progress' in status_lower or 'doing' in status_lower:
        return '🎯'
    elif 'review' in status_lower or 'testing' in status_lower:
        return '👀'
    elif 'done' in status_lower or 'closed' in status_lower or 'resolved' in status_lower:
        return '✅'
    elif 'blocked' in status_lower:
        return '🚫'
    elif 'todo' in status_lower or 'backlog' in status_lower or 'open' in status_lower:
        return '📝'
    else:
        return '🔹'

def get_status_color(status: str) -> str:
    """Get ANSI color code for Jira status."""
    status_lower = status.lower().replace(' ', '')
    if 'progress' in status_lower or 'doing' in status_lower:
        return Colors.YELLOW
    elif 'review' in status_lower or 'testing' in status_lower:
        return Colors.CYAN
    elif 'done' in status_lower or 'closed' in status_lower or 'resolved' in status_lower:
        return Colors.GREEN
    elif 'blocked' in status_lower:
        return Colors.RED
    elif 'todo' in status_lower or 'backlog' in status_lower or 'open' in status_lower:
        return Colors.BLUE
    else:
        return Colors.GRAY

def fetch_jira_status(issue_key: str) -> Optional[str]:
    """Fetch current status from Jira API with caching."""
    # Check cache first
    cached = get_cached_status(issue_key)
    if cached:
        return cached

    # Fetch from Jira
    try:
        ctx = resolve_context()
        jira = JiraClient.from_config(ctx.config)
        if not jira:
            return None

        # Get issue details
        issue = jira.get_issue(issue_key)
        if issue and 'fields' in issue and 'status' in issue['fields']:
            status = issue['fields']['status']['name']
            set_cached_status(issue_key, status)
            return status
    except Exception:
        pass

    return None

def format_prompt(
    issue_key: str,
    status: Optional[str] = None,
    format_type: PromptFormat = PromptFormat.DEFAULT,
    use_color: bool = False
) -> str:
    """
    Format the prompt output based on options.

    Args:
        issue_key: Jira issue key (e.g., "ABC-123")
        status: Optional Jira status (e.g., "In Progress")
        format_type: Output format style
        use_color: Whether to use ANSI color codes

    Returns:
        Formatted prompt string
    """
    if format_type == PromptFormat.MINIMAL:
        # Just the issue key, no brackets
        output = issue_key
        if status:
            output = f"{issue_key}: {status}"
    elif format_type == PromptFormat.EMOJI:
        # Use emoji based on status
        if status:
            emoji = get_status_emoji(status)
            output = f"{emoji} {issue_key}"
        else:
            output = f"🔹 {issue_key}"
    else:  # DEFAULT
        # Bracketed format
        output = f"[{issue_key}]"
        if status:
            output = f"[{issue_key}: {status}]"

    # Apply color if requested
    if use_color and status:
        color = get_status_color(status)
        output = f"{color}{output}{Colors.RESET}"
    elif use_color:
        # Default color for issue without status
        output = f"{Colors.BLUE}{output}{Colors.RESET}"

    return output

def prompt_command(
    with_status: bool = False,
    format_type: PromptFormat = PromptFormat.DEFAULT,
    use_color: bool = False
) -> int:
    """
    Generate shell prompt information for current work context.

    Returns:
        0 if successful (with output), 1 if no work in progress (no output)
    """
    try:
        # Find git repo
        repo_root = find_git_root(Path.cwd())

        # Get current branch
        branch = current_branch(repo_root)
        if not branch:
            return 1

        # Extract issue key from branch
        issue_key = extract_issue_key_from_branch(branch)
        if not issue_key:
            return 1

        # Optionally fetch status
        status = None
        if with_status:
            status = fetch_jira_status(issue_key)

        # Format and output
        output = format_prompt(issue_key, status, format_type, use_color)
        print(f" {output}", end="")
        return 0

    except Exception:
        # Silent fail - not in a git repo or other error
        return 1
