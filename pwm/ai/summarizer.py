"""
High-level AI summarization functions.

These functions combine prompt templates with commit/diff data
and call the OpenAI API to generate summaries.
"""

from __future__ import annotations
from typing import Optional
from pwm.ai.openai_client import OpenAIClient
from pwm.ai.prompts import (
    PR_DESCRIPTION_SYSTEM,
    PR_DESCRIPTION_PROMPT,
    WORK_END_SYSTEM,
    WORK_END_PROMPT
)


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
    commits: list[dict],
    openai: Optional[OpenAIClient]
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
    commits: list[dict],
    openai: Optional[OpenAIClient]
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
