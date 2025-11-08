"""CLI command for daily work summary."""

from datetime import datetime
from typing import Optional
from pathlib import Path
from rich import print as rprint

from pwm.context.resolver import resolve_context
from pwm.summary.business_days import get_previous_business_day
from pwm.summary.collector import collect_work_data
from pwm.summary.formatter import format_markdown, format_text
from pwm.github.client import GitHubClient
from pwm.jira.client import JiraClient
from pwm.ai.openai_client import OpenAIClient
from pwm.ai.summarizer import summarize_daily_work


def daily_summary(
    since: Optional[datetime] = None,
    use_ai: bool = True,
    format: Optional[str] = None,
    output_file: Optional[str] = None,
    show_links: bool = False
) -> int:
    """
    Generate daily work summary from previous business day to now.

    Args:
        since: Start time for summary (defaults to previous business day)
        use_ai: Whether to include AI-generated summary
        format: Output format ("markdown" or "text", defaults to config)
        output_file: Path to save output (optional)
        show_links: Whether to show URLs for PRs and Jira issues

    Returns:
        0 on success, 1 on error
    """
    try:
        ctx = resolve_context()
    except RuntimeError as e:
        rprint(f"[red]Error:[/red] {e}")
        return 1

    repo_root = ctx.repo_root

    # Determine start time
    if since is None:
        since = get_previous_business_day(datetime.now())
        rprint(f"[cyan]Generating summary from previous business day...[/cyan]")
    else:
        rprint(f"[cyan]Generating summary from {since.strftime('%Y-%m-%d %H:%M')}...[/cyan]")

    rprint(f"[dim]Period: {since.strftime('%Y-%m-%d %H:%M')} to now[/dim]")
    rprint()

    # Initialize clients
    github_client = GitHubClient.from_config(ctx.config)
    jira_client = JiraClient.from_config(ctx.config)
    openai_client = OpenAIClient.from_config(ctx.config) if use_ai else None

    # Check if any service is configured
    if not github_client and not jira_client:
        rprint("[yellow]Warning:[/yellow] Neither GitHub nor Jira is configured.")
        rprint("[dim]Configure at least one service in .pwm.toml or ~/.config/pwm/config.toml[/dim]")
        rprint()

    # Collect data
    rprint("[cyan]Collecting data...[/cyan]")
    data = collect_work_data(
        github_repo=ctx.github_repo,
        jira_project=ctx.jira_project_key,
        since=since,
        github_client=github_client,
        jira_client=jira_client,
        config=ctx.config
    )

    # Generate AI summary
    ai_summary = None
    if openai_client:
        rprint("[cyan]Generating AI summary...[/cyan]")
        prs_dict = {
            'opened': data.prs_opened,
            'closed': data.prs_closed,
            'merged': data.prs_merged
        }
        jira_dict = {
            'created': data.jira_created,
            'updated': data.jira_updated
        }
        ai_summary = summarize_daily_work(prs_dict, jira_dict, openai_client)

        if ai_summary:
            rprint("[green]✓[/green] AI summary generated")
        else:
            rprint("[dim]No AI summary generated (insufficient data or API error)[/dim]")
    rprint()

    # Format output
    output_format = format or ctx.config.get("daily_summary", {}).get("default_format", "markdown")

    # Get Jira base URL if needed for links
    jira_base_url = None
    if show_links and jira_client:
        jira_base_url = jira_client.base_url

    if output_format == "text":
        output = format_text(data, ai_summary, show_links=show_links, jira_base_url=jira_base_url)
    else:
        output = format_markdown(data, ai_summary, show_links=show_links, jira_base_url=jira_base_url)

    # Display or save
    if output_file:
        output_path = Path(output_file)
        output_path.write_text(output)
        rprint(f"[green]✓[/green] Summary saved to {output_file}")
    else:
        rprint(output)

    # Print statistics
    total_prs = len(data.prs_opened) + len(data.prs_closed) + len(data.prs_merged)
    total_jira = len(data.jira_created) + len(data.jira_updated)

    rprint()
    rprint("[bold green]Summary complete![/bold green]")
    rprint(f"[dim]PRs: {total_prs} (opened: {len(data.prs_opened)}, merged: {len(data.prs_merged)}, closed: {len(data.prs_closed)})[/dim]")
    rprint(f"[dim]Jira: {total_jira} (created: {len(data.jira_created)}, updated: {len(data.jira_updated)})[/dim]")

    return 0
