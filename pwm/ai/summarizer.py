"""
High-level AI summarization functions.

These functions combine prompt templates with commit/diff data
and call the OpenAI API to generate summaries.
"""

from __future__ import annotations
from typing import Optional, Protocol
from pwm.ai.prompts import (
    PR_DESCRIPTION_SYSTEM,
    PR_DESCRIPTION_PROMPT,
    WORK_END_SYSTEM,
    WORK_END_PROMPT,
    DAILY_SUMMARY_SYSTEM,
    DAILY_SUMMARY_PROMPT,
)


class SupportsCompletion(Protocol):
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs: object,
    ) -> Optional[str]: ...


def format_commits_for_prompt(commits: list[dict], max_commits: int = 10) -> str:
    """
    Format commits for inclusion in AI prompts.

    Args:
        commits: List of commit dicts with 'subject' and 'body' keys
        max_commits: Maximum number of commits to include

    Returns:
        Formatted commit list as string
    """
    if not commits:
        return "(no commits)"

    lines = []
    for i, commit in enumerate(commits[:max_commits]):
        subject = commit.get("subject", "")
        body = commit.get("body", "").strip()

        lines.append(f"- {subject}")
        if body and len(body) < 200:  # Include body if short
            lines.append(f"  {body}")

    if len(commits) > max_commits:
        lines.append(f"... and {len(commits) - max_commits} more commits")

    return "\n".join(lines)


def summarize_commits_for_pr(
    commits: list[dict], openai: Optional[SupportsCompletion]
) -> Optional[str]:
    """
    Generate PR description from commits using AI.

    Args:
        commits: List of commit objects with 'subject' and 'body' keys
        openai: OpenAI client (None if not configured)

    Returns:
        AI-generated summary or None if OpenAI not configured or call failed
    """
    if not openai or not commits:
        return None

    commits_text = format_commits_for_prompt(commits)
    prompt = PR_DESCRIPTION_PROMPT.format(commits=commits_text)

    return openai.complete(prompt, system=PR_DESCRIPTION_SYSTEM)


def summarize_work_end(
    commits: list[dict], openai: Optional[SupportsCompletion]
) -> Optional[str]:
    """
    Generate work-end status update from commits using AI.

    Args:
        commits: List of commit objects with 'subject' and 'body' keys
        openai: OpenAI client (None if not configured)

    Returns:
        AI-generated summary or None if OpenAI not configured or call failed
    """
    if not openai or not commits:
        return None

    commits_text = format_commits_for_prompt(commits)
    prompt = WORK_END_PROMPT.format(commits=commits_text)

    return openai.complete(prompt, system=WORK_END_SYSTEM)


def summarize_daily_work(
    prs: dict[str, list[dict]],
    jira_issues: dict[str, list[dict]],
    openai: Optional[SupportsCompletion],
) -> Optional[str]:
    """
    Generate AI summary of daily work activity.

    Args:
        prs: Dict with 'opened', 'closed', 'merged' keys containing PR lists
        jira_issues: Dict with 'created', 'updated' keys containing issue lists
        openai: OpenAI client (None if not configured)

    Returns:
        AI-generated summary or None if OpenAI not configured or call failed
    """
    if not openai:
        return None

    # Check if there's any work to summarize
    has_work = (
        prs.get("opened")
        or prs.get("closed")
        or prs.get("merged")
        or jira_issues.get("created")
        or jira_issues.get("updated")
    )
    if not has_work:
        return None

    # Format PRs
    prs_text = []
    if prs.get("opened"):
        prs_text.append(f"Opened ({len(prs['opened'])} PRs):")
        for pr in prs["opened"][:5]:  # Limit to first 5
            title = pr.get("title", "Untitled")
            number = pr.get("number", "?")
            prs_text.append(f"  - #{number}: {title}")
        if len(prs["opened"]) > 5:
            prs_text.append(f"  ... and {len(prs['opened']) - 5} more")

    if prs.get("merged"):
        prs_text.append(f"Merged ({len(prs['merged'])} PRs):")
        for pr in prs["merged"][:5]:
            title = pr.get("title", "Untitled")
            number = pr.get("number", "?")
            prs_text.append(f"  - #{number}: {title}")
        if len(prs["merged"]) > 5:
            prs_text.append(f"  ... and {len(prs['merged']) - 5} more")

    if prs.get("closed"):
        prs_text.append(f"Closed ({len(prs['closed'])} PRs):")
        for pr in prs["closed"][:5]:
            title = pr.get("title", "Untitled")
            number = pr.get("number", "?")
            prs_text.append(f"  - #{number}: {title}")
        if len(prs["closed"]) > 5:
            prs_text.append(f"  ... and {len(prs['closed']) - 5} more")

    # Format Jira
    jira_text = []
    if jira_issues.get("created"):
        jira_text.append(f"Created ({len(jira_issues['created'])} issues):")
        for issue in jira_issues["created"][:5]:
            key = issue.get("key", "Unknown")
            summary = issue.get("summary", "No summary")
            jira_text.append(f"  - {key}: {summary}")
        if len(jira_issues["created"]) > 5:
            jira_text.append(f"  ... and {len(jira_issues['created']) - 5} more")

    if jira_issues.get("updated"):
        jira_text.append(f"Updated ({len(jira_issues['updated'])} issues):")
        for issue in jira_issues["updated"][:5]:
            key = issue.get("key", "Unknown")
            summary = issue.get("summary", "No summary")
            status = issue.get("status", {})
            status_name = (
                status.get("name", "Unknown") if isinstance(status, dict) else "Unknown"
            )
            jira_text.append(f"  - {key}: {summary} (→ {status_name})")
        if len(jira_issues["updated"]) > 5:
            jira_text.append(f"  ... and {len(jira_issues['updated']) - 5} more")

    prompt = DAILY_SUMMARY_PROMPT.format(
        prs="\n".join(prs_text) if prs_text else "(no PR activity)",
        jira="\n".join(jira_text) if jira_text else "(no Jira activity)",
    )

    return openai.complete(prompt, system=DAILY_SUMMARY_SYSTEM)


def truncate_diff(diff: str, max_chars: int = 10000) -> tuple[str, bool]:
    """
    Intelligently truncate diff to avoid token limits.

    Strategy:
    1. If diff is under limit, return as-is
    2. If over limit, split into file chunks and prioritize:
       - Skip generated/minified files (package-lock.json, *.min.js, etc.)
       - Prioritize source code files (.py, .ts, .js, .go, etc.)
       - Include beginning and end of diff for context
    3. Return truncated diff and flag indicating truncation

    Args:
        diff: Full git diff string
        max_chars: Maximum characters to keep (default: 10000)

    Returns:
        Tuple of (truncated_diff, was_truncated)
    """
    if len(diff) <= max_chars:
        return diff, False

    # Patterns for files to skip (generated, minified, lock files)
    skip_patterns = [
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.lock",
        "Gemfile.lock",
        "poetry.lock",
        ".min.js",
        ".min.css",
        ".bundle.js",
        ".map",
        "dist/",
        "build/",
        "__pycache__/",
        ".pyc",
        "node_modules/",
    ]

    # Split diff into file chunks (split on "diff --git")
    file_chunks = []
    current_chunk = []

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            if current_chunk:
                file_chunks.append("\n".join(current_chunk))
            current_chunk = [line]
        else:
            current_chunk.append(line)

    if current_chunk:
        file_chunks.append("\n".join(current_chunk))

    # Filter and prioritize chunks
    prioritized_chunks = []

    for chunk in file_chunks:
        # Extract filename from "diff --git a/path b/path" line
        first_line = chunk.split("\n")[0] if chunk else ""

        # Check if this is a file we should skip
        should_skip = any(pattern in first_line for pattern in skip_patterns)

        if not should_skip:
            prioritized_chunks.append(chunk)

    # If we still have too much, truncate smartly
    result_chunks = []
    current_length = 0

    for chunk in prioritized_chunks:
        if current_length + len(chunk) + 1 <= max_chars:  # +1 for newline
            result_chunks.append(chunk)
            current_length += len(chunk) + 1
        else:
            # Add partial chunk if there's room
            remaining = max_chars - current_length
            if remaining > 100:  # Only add if meaningful space left
                result_chunks.append(chunk[:remaining] + "\n[... truncated]")
            break

    truncated = "\n".join(result_chunks)
    return truncated, True


def summarize_diff_for_pr(
    diff: str, openai: Optional[SupportsCompletion]
) -> Optional[str]:
    """
    Generate PR description from git diff using AI.

    Args:
        diff: Git diff string
        openai: OpenAI client (None if not configured)

    Returns:
        AI-generated 4-5 sentence summary or None if OpenAI not configured or call failed
    """
    if not openai or not diff:
        return None

    # Truncate diff if too large
    truncated_diff, was_truncated = truncate_diff(diff)

    # Prepare truncation note
    truncation_note = ""
    if was_truncated:
        truncation_note = "(Note: Diff was truncated to focus on source code files. Generated/minified files excluded.)"

    # Format prompt
    from pwm.ai.prompts import PR_DIFF_SUMMARY_SYSTEM, PR_DIFF_SUMMARY_PROMPT

    prompt = PR_DIFF_SUMMARY_PROMPT.format(
        truncation_note=truncation_note, diff=truncated_diff
    )

    return openai.complete(prompt, system=PR_DIFF_SUMMARY_SYSTEM)
