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
    WORK_END_PROMPT,
    DAILY_SUMMARY_SYSTEM,
    DAILY_SUMMARY_PROMPT
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


def summarize_daily_work(
    prs: dict[str, list[dict]],
    jira_issues: dict[str, list[dict]],
    openai: Optional[OpenAIClient]
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
        prs.get('opened') or prs.get('closed') or prs.get('merged') or
        jira_issues.get('created') or jira_issues.get('updated')
    )
    if not has_work:
        return None

    # Format PRs
    prs_text = []
    if prs.get('opened'):
        prs_text.append(f"Opened ({len(prs['opened'])} PRs):")
        for pr in prs['opened'][:5]:  # Limit to first 5
            title = pr.get('title', 'Untitled')
            number = pr.get('number', '?')
            prs_text.append(f"  - #{number}: {title}")
        if len(prs['opened']) > 5:
            prs_text.append(f"  ... and {len(prs['opened']) - 5} more")

    if prs.get('merged'):
        prs_text.append(f"Merged ({len(prs['merged'])} PRs):")
        for pr in prs['merged'][:5]:
            title = pr.get('title', 'Untitled')
            number = pr.get('number', '?')
            prs_text.append(f"  - #{number}: {title}")
        if len(prs['merged']) > 5:
            prs_text.append(f"  ... and {len(prs['merged']) - 5} more")

    if prs.get('closed'):
        prs_text.append(f"Closed ({len(prs['closed'])} PRs):")
        for pr in prs['closed'][:5]:
            title = pr.get('title', 'Untitled')
            number = pr.get('number', '?')
            prs_text.append(f"  - #{number}: {title}")
        if len(prs['closed']) > 5:
            prs_text.append(f"  ... and {len(prs['closed']) - 5} more")

    # Format Jira
    jira_text = []
    if jira_issues.get('created'):
        jira_text.append(f"Created ({len(jira_issues['created'])} issues):")
        for issue in jira_issues['created'][:5]:
            key = issue.get('key', 'Unknown')
            summary = issue.get('summary', 'No summary')
            jira_text.append(f"  - {key}: {summary}")
        if len(jira_issues['created']) > 5:
            jira_text.append(f"  ... and {len(jira_issues['created']) - 5} more")

    if jira_issues.get('updated'):
        jira_text.append(f"Updated ({len(jira_issues['updated'])} issues):")
        for issue in jira_issues['updated'][:5]:
            key = issue.get('key', 'Unknown')
            summary = issue.get('summary', 'No summary')
            status = issue.get('status', {})
            status_name = status.get('name', 'Unknown') if isinstance(status, dict) else 'Unknown'
            jira_text.append(f"  - {key}: {summary} (→ {status_name})")
        if len(jira_issues['updated']) > 5:
            jira_text.append(f"  ... and {len(jira_issues['updated']) - 5} more")

    prompt = DAILY_SUMMARY_PROMPT.format(
        prs="\n".join(prs_text) if prs_text else "(no PR activity)",
        jira="\n".join(jira_text) if jira_text else "(no Jira activity)"
    )

    return openai.complete(prompt, system=DAILY_SUMMARY_SYSTEM)
