"""Output formatting for work summaries."""

from typing import Optional

from pwm.summary.collector import WorkSummaryData
from pwm.summary.business_days import format_date_range


def format_markdown(data: WorkSummaryData, ai_summary: Optional[str] = None) -> str:
    """
    Format work summary data as markdown.

    Args:
        data: WorkSummaryData containing collected work information
        ai_summary: Optional AI-generated summary text

    Returns:
        Formatted markdown string
    """
    lines = []

    # Header
    lines.append("# Daily Work Summary")
    date_range = format_date_range(data.start_time, data.end_time)
    lines.append(f"**Period:** {date_range}")
    lines.append("")

    # AI Summary (at the top if present)
    if ai_summary:
        lines.append("## Summary")
        lines.append(ai_summary)
        lines.append("")

    # Pull Requests section
    if data.prs_opened or data.prs_closed or data.prs_merged:
        lines.append("## Pull Requests")
        lines.append("")

        if data.prs_opened:
            lines.append(f"### Opened ({len(data.prs_opened)})")
            for pr in data.prs_opened:
                title = pr.get('title', 'Untitled')
                number = pr.get('number')
                html_url = pr.get('html_url', '')
                if html_url:
                    lines.append(f"- [#{number}]({html_url}) {title}")
                else:
                    lines.append(f"- #{number} {title}")
            lines.append("")

        if data.prs_merged:
            lines.append(f"### Merged ({len(data.prs_merged)})")
            for pr in data.prs_merged:
                title = pr.get('title', 'Untitled')
                number = pr.get('number')
                html_url = pr.get('html_url', '')
                if html_url:
                    lines.append(f"- [#{number}]({html_url}) {title}")
                else:
                    lines.append(f"- #{number} {title}")
            lines.append("")

        if data.prs_closed:
            lines.append(f"### Closed ({len(data.prs_closed)})")
            for pr in data.prs_closed:
                title = pr.get('title', 'Untitled')
                number = pr.get('number')
                html_url = pr.get('html_url', '')
                if html_url:
                    lines.append(f"- [#{number}]({html_url}) {title}")
                else:
                    lines.append(f"- #{number} {title}")
            lines.append("")

    # Jira section
    if data.jira_created or data.jira_updated:
        lines.append("## Jira Issues")
        lines.append("")

        if data.jira_created:
            lines.append(f"### Created ({len(data.jira_created)})")
            for issue in data.jira_created:
                key = issue.get('key', 'Unknown')
                summary = issue.get('summary', 'No summary')
                lines.append(f"- {key}: {summary}")
            lines.append("")

        if data.jira_updated:
            lines.append(f"### Updated ({len(data.jira_updated)})")
            for issue in data.jira_updated:
                key = issue.get('key', 'Unknown')
                summary = issue.get('summary', 'No summary')
                status = issue.get('status', {})
                status_name = status.get('name', 'Unknown') if isinstance(status, dict) else 'Unknown'
                lines.append(f"- {key}: {summary} → {status_name}")
            lines.append("")

    # Handle empty case
    if not (data.prs_opened or data.prs_closed or data.prs_merged or
            data.jira_created or data.jira_updated):
        lines.append("No work activity found for this period.")
        lines.append("")

    return "\n".join(lines)


def format_text(data: WorkSummaryData, ai_summary: Optional[str] = None) -> str:
    """
    Format work summary data as plain text.

    Args:
        data: WorkSummaryData containing collected work information
        ai_summary: Optional AI-generated summary text

    Returns:
        Formatted plain text string
    """
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("DAILY WORK SUMMARY")
    lines.append("=" * 60)
    date_range = format_date_range(data.start_time, data.end_time)
    lines.append(f"Period: {date_range}")
    lines.append("")

    # AI Summary (at the top if present)
    if ai_summary:
        lines.append("SUMMARY")
        lines.append("-" * 60)
        lines.append(ai_summary)
        lines.append("")

    # Pull Requests section
    if data.prs_opened or data.prs_closed or data.prs_merged:
        lines.append("PULL REQUESTS")
        lines.append("-" * 60)

        if data.prs_opened:
            lines.append(f"Opened ({len(data.prs_opened)}):")
            for pr in data.prs_opened:
                title = pr.get('title', 'Untitled')
                number = pr.get('number')
                lines.append(f"  • #{number} {title}")
            lines.append("")

        if data.prs_merged:
            lines.append(f"Merged ({len(data.prs_merged)}):")
            for pr in data.prs_merged:
                title = pr.get('title', 'Untitled')
                number = pr.get('number')
                lines.append(f"  • #{number} {title}")
            lines.append("")

        if data.prs_closed:
            lines.append(f"Closed ({len(data.prs_closed)}):")
            for pr in data.prs_closed:
                title = pr.get('title', 'Untitled')
                number = pr.get('number')
                lines.append(f"  • #{number} {title}")
            lines.append("")

    # Jira section
    if data.jira_created or data.jira_updated:
        lines.append("JIRA ISSUES")
        lines.append("-" * 60)

        if data.jira_created:
            lines.append(f"Created ({len(data.jira_created)}):")
            for issue in data.jira_created:
                key = issue.get('key', 'Unknown')
                summary = issue.get('summary', 'No summary')
                lines.append(f"  • {key}: {summary}")
            lines.append("")

        if data.jira_updated:
            lines.append(f"Updated ({len(data.jira_updated)}):")
            for issue in data.jira_updated:
                key = issue.get('key', 'Unknown')
                summary = issue.get('summary', 'No summary')
                status = issue.get('status', {})
                status_name = status.get('name', 'Unknown') if isinstance(status, dict) else 'Unknown'
                lines.append(f"  • {key}: {summary} → {status_name}")
            lines.append("")

    # Handle empty case
    if not (data.prs_opened or data.prs_closed or data.prs_merged or
            data.jira_created or data.jira_updated):
        lines.append("No work activity found for this period.")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
