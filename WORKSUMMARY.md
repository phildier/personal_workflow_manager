# Daily Work Summary Feature - Implementation Plan

## Overview
New command: `pwm daily-summary` (alias: `pwm ds`)

**Purpose:** Generate a comprehensive summary of work done from the previous business day until now, including:
- GitHub PRs opened and closed (with their commits)
- Jira tickets created and updated

**Example Use Case:** Running `pwm daily-summary` on Monday at noon will show all work from Friday 00:00 through Monday 12:00.

**Note:** We focus on high-level work items (PRs and Jira issues) rather than individual git commits, since PR commits are already shown within GitHub PRs.

## Command Interface

```bash
pwm daily-summary                           # Auto-detect previous business day
pwm daily-summary --since "2025-01-10 09:00"  # Custom start time
pwm daily-summary --no-ai                   # Skip AI summary
pwm daily-summary --format [text|markdown]  # Output format
pwm daily-summary --output report.md        # Save to file
```

## Business Day Logic

- **Monday-Friday**: Previous business day
- **Monday**: Gets Friday's data (skips weekend)
- **Saturday/Sunday**: Gets Friday's data
- **Time range**: Start of previous business day (00:00) to current time

### Business Day Calculation Algorithm

```python
def get_previous_business_day(current_time: datetime) -> datetime:
    """
    Calculate the start of the previous business day.
    
    Monday → Friday 00:00
    Tuesday-Friday → Previous day 00:00
    Saturday/Sunday → Friday 00:00
    """
    weekday = current_time.weekday()  # 0=Monday, 6=Sunday
    
    if weekday == 0:  # Monday
        days_back = 3  # Go back to Friday
    elif weekday in (5, 6):  # Saturday or Sunday
        days_back = weekday - 4  # Go back to Friday
    else:  # Tuesday-Friday
        days_back = 1
    
    previous_day = current_time - timedelta(days=days_back)
    return previous_day.replace(hour=0, minute=0, second=0, microsecond=0)
```

## Architecture

### New Directory: `pwm/summary/`

```
pwm/summary/
├── __init__.py
├── command.py           # CLI command implementation
├── collector.py         # Data collection orchestration
├── formatter.py         # Output formatting (markdown/text)
└── business_days.py     # Business day calculation utilities
```

### File Modifications Required

#### 1. `pwm/github/client.py` - Add PR Search Methods

```python
def search_prs_by_date(
    self,
    repo: str,
    since: datetime,
    author: Optional[str] = None,
    state: str = "all"
) -> list[dict]:
    """
    Search for PRs created since a given date.
    
    Args:
        repo: Repository in "owner/repo" format
        since: Only return PRs created after this timestamp
        author: Filter by PR author (GitHub username)
        state: PR state - "open", "closed", or "all"
    
    Returns list of PR objects.
    """
    # Use GitHub Search API: GET /search/issues
    # Query: repo:owner/repo is:pr created:>=YYYY-MM-DD author:username
    url = f"{self.base_url}/search/issues"
    since_str = since.strftime("%Y-%m-%dT%H:%M:%S")
    query_parts = [
        f"repo:{repo}",
        "is:pr",
        f"created:>={since_str}"
    ]
    if author:
        query_parts.append(f"author:{author}")
    
    params = {"q": " ".join(query_parts), "sort": "created", "order": "desc"}
    # Implementation with pagination...


def get_closed_prs(
    self,
    repo: str,
    since: datetime,
    author: Optional[str] = None
) -> list[dict]:
    """
    Get PRs closed/merged since a given date.
    
    Args:
        repo: Repository in "owner/repo" format
        since: Only return PRs closed after this timestamp
        author: Filter by PR author (GitHub username)
    
    Returns list of closed/merged PR objects.
    """
    # Use GitHub Search API with closed filter
    # Query: repo:owner/repo is:pr is:closed closed:>=YYYY-MM-DD
    # Also check merged_at for merged PRs
```

#### 2. `pwm/jira/client.py` - Add Issue Search Methods

```python
def search_issues_by_date(
    self,
    jql: str,
    max_results: int = 100
) -> list[dict]:
    """
    Search Jira issues using JQL.
    
    Args:
        jql: JQL query string
        max_results: Maximum number of results to return
    
    Returns list of issue objects with fields: key, summary, status, created, updated
    """
    url = f"{self.base_url}/rest/api/3/search"
    params = {
        "jql": jql,
        "maxResults": max_results,
        "fields": "key,summary,status,created,updated,assignee"
    }
    # Implementation...


def get_issues_created_since(
    self,
    project_key: str,
    since: datetime,
    assignee: Optional[str] = "currentUser()"
) -> list[dict]:
    """
    Get issues created since a given date.
    
    Args:
        project_key: Jira project key (e.g., "ABC")
        since: Only return issues created after this timestamp
        assignee: Filter by assignee (default: current user)
    
    Returns list of issue objects.
    """
    since_str = since.strftime("%Y-%m-%d %H:%M")
    jql = f'project = {project_key} AND created >= "{since_str}"'
    if assignee:
        jql += f" AND assignee = {assignee}"
    return self.search_issues_by_date(jql)


def get_issues_updated_since(
    self,
    project_key: str,
    since: datetime,
    assignee: Optional[str] = "currentUser()"
) -> list[dict]:
    """
    Get issues updated since a given date (excluding newly created).
    
    Args:
        project_key: Jira project key (e.g., "ABC")
        since: Only return issues updated after this timestamp
        assignee: Filter by assignee (default: current user)
    
    Returns list of issue objects.
    """
    since_str = since.strftime("%Y-%m-%d %H:%M")
    jql = f'project = {project_key} AND updated >= "{since_str}" AND created < "{since_str}"'
    if assignee:
        jql += f" AND assignee = {assignee}"
    return self.search_issues_by_date(jql)
```

#### 3. `pwm/vcs/git_cli.py` - Add Commit Search Method

```python
def get_all_commits_since(
    repo_root: Path,
    since: datetime,
    author: Optional[str] = None,
    all_branches: bool = True
) -> list[dict]:
    """
    Get all commits since a given date, optionally across all branches.
    
    Args:
        repo_root: Repository root path
        since: Only include commits after this timestamp
        author: Filter by commit author (git name or email)
        all_branches: Search all branches (default: True)
    
    Returns list of dicts with 'hash', 'subject', 'body', 'timestamp', 'branch' keys.
    """
    # Format: %H = hash, %s = subject, %b = body, %ct = timestamp, %D = refs
    args = [
        "log",
        "--format=%H%x00%s%x00%b%x00%ct%x00%D%x1e",
        f"--since={int(since.timestamp())}"
    ]
    
    if all_branches:
        args.append("--all")
    
    if author:
        args.append(f"--author={author}")
    
    r = _run(args, repo_root)
    
    if r.returncode != 0:
        return []
    
    commits = []
    for entry in r.stdout.strip().split("\x1e"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("\x00", 4)
        if len(parts) >= 2:
            commit_dict = {
                "hash": parts[0],
                "subject": parts[1],
                "body": parts[2] if len(parts) > 2 else "",
                "timestamp": datetime.fromtimestamp(int(parts[3])) if len(parts) > 3 else None,
                "refs": parts[4] if len(parts) > 4 else ""
            }
            commits.append(commit_dict)
    
    return commits


def get_branch_for_commit(repo_root: Path, commit_hash: str) -> list[str]:
    """
    Get all branches that contain a specific commit.
    
    Returns list of branch names.
    """
    args = ["branch", "--contains", commit_hash, "--format=%(refname:short)"]
    r = _run(args, repo_root)
    if r.returncode == 0:
        return [b.strip() for b in r.stdout.strip().split("\n") if b.strip()]
    return []
```

#### 4. `pwm/ai/prompts.py` - Add Daily Summary Prompt

```python
DAILY_SUMMARY_SYSTEM = """You are a technical assistant that summarizes daily engineering work.
Given information about commits, pull requests, and Jira issues, generate a concise 
2-3 sentence executive summary that highlights the key themes and accomplishments.

Focus on:
- Main areas of work (features, bug fixes, refactoring, etc.)
- Key milestones (PRs merged, issues completed)
- Overall productivity and progress

Be concise, technical, and professional."""

DAILY_SUMMARY_PROMPT = """
Based on the following work activity, generate a 2-3 sentence executive summary:

## Commits
{commits}

## Pull Requests
{prs}

## Jira Issues
{jira}

Generate a concise summary that captures the key themes and accomplishments.
"""
```

#### 5. `pwm/ai/summarizer.py` - Add Summary Function

```python
def summarize_daily_work(
    commits: list[dict],
    prs: dict,
    jira_issues: dict,
    openai: Optional[OpenAIClient]
) -> Optional[str]:
    """
    Generate AI summary of daily work activity.
    
    Args:
        commits: List of commit objects
        prs: Dict with 'opened', 'closed', 'merged' keys containing PR lists
        jira_issues: Dict with 'created', 'updated' keys containing issue lists
        openai: OpenAI client (None if not configured)
    
    Returns:
        AI-generated summary or None if OpenAI not configured or call failed
    """
    if not openai:
        return None
    
    # Format commits
    commits_text = format_commits_for_prompt(commits, max_commits=20)
    
    # Format PRs
    prs_text = []
    if prs.get('opened'):
        prs_text.append(f"Opened: {len(prs['opened'])} PRs")
        for pr in prs['opened'][:5]:
            prs_text.append(f"  - #{pr['number']}: {pr['title']}")
    if prs.get('merged'):
        prs_text.append(f"Merged: {len(prs['merged'])} PRs")
        for pr in prs['merged'][:5]:
            prs_text.append(f"  - #{pr['number']}: {pr['title']}")
    
    # Format Jira
    jira_text = []
    if jira_issues.get('created'):
        jira_text.append(f"Created: {len(jira_issues['created'])} issues")
        for issue in jira_issues['created'][:5]:
            jira_text.append(f"  - {issue['key']}: {issue['summary']}")
    if jira_issues.get('updated'):
        jira_text.append(f"Updated: {len(jira_issues['updated'])} issues")
    
    prompt = DAILY_SUMMARY_PROMPT.format(
        commits=commits_text,
        prs="\n".join(prs_text) if prs_text else "(no PRs)",
        jira="\n".join(jira_text) if jira_text else "(no Jira activity)"
    )
    
    return openai.complete(prompt, system=DAILY_SUMMARY_SYSTEM)
```

#### 6. `pwm/config/models.py` - Add Configuration

```python
class DailySummaryConfig(BaseModel):
    """Configuration for daily summary feature."""
    
    # Filter options
    include_own_commits_only: bool = True
    include_own_prs_only: bool = True
    include_own_issues_only: bool = True
    
    # Display options
    default_format: str = "markdown"  # "text" or "markdown"
    show_commit_details: bool = True
    group_commits_by_branch: bool = True
    max_commits_per_branch: int = 10
    
    # Business day configuration
    work_start_hour: int = 0
    work_end_hour: int = 23

# Add to PWMConfig
class PWMConfig(BaseModel):
    jira: JiraConfig = Field(default_factory=JiraConfig)
    github: GithubConfig = Field(default_factory=GithubConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    branch: BranchConfig = Field(default_factory=BranchConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    daily_summary: DailySummaryConfig = Field(default_factory=DailySummaryConfig)  # NEW
```

#### 7. `pwm/cli.py` - Register Command

```python
from pwm.summary.command import daily_summary

@app.command("daily-summary")
@app.command("ds")
def daily_summary_cmd(
    since: Optional[str] = typer.Option(None, "--since", help="Start time (YYYY-MM-DD HH:MM)"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI-generated summary"),
    format: str = typer.Option(None, "--format", help="Output format: text or markdown"),
    output: Optional[str] = typer.Option(None, "--output", help="Save to file")
) -> None:
    """Generate summary of work from previous business day to now."""
    # Parse since if provided
    since_dt = None
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d %H:%M")
        except ValueError:
            rprint("[red]Invalid date format. Use: YYYY-MM-DD HH:MM[/red]")
            raise typer.Exit(1)
    
    raise SystemExit(daily_summary(
        since=since_dt,
        use_ai=not no_ai,
        format=format,
        output_file=output
    ))
```

## Core Implementation Files

### `pwm/summary/business_days.py`

```python
from datetime import datetime, timedelta

def get_previous_business_day(current_time: datetime) -> datetime:
    """
    Calculate the start of the previous business day.
    
    Monday → Friday 00:00
    Tuesday-Friday → Previous day 00:00
    Saturday/Sunday → Friday 00:00
    """
    weekday = current_time.weekday()  # 0=Monday, 6=Sunday
    
    if weekday == 0:  # Monday
        days_back = 3
    elif weekday == 5:  # Saturday
        days_back = 1
    elif weekday == 6:  # Sunday
        days_back = 2
    else:  # Tuesday-Friday
        days_back = 1
    
    previous_day = current_time - timedelta(days=days_back)
    return previous_day.replace(hour=0, minute=0, second=0, microsecond=0)


def format_date_range(start: datetime, end: datetime) -> str:
    """Format a date range for display."""
    start_str = start.strftime("%A, %b %d %Y %H:%M")
    end_str = end.strftime("%A, %b %d %Y %H:%M")
    return f"{start_str} - {end_str}"
```

### `pwm/summary/collector.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path

@dataclass
class WorkSummaryData:
    """Container for collected work summary data."""
    commits: list[dict]
    prs_opened: list[dict]
    prs_closed: list[dict]
    prs_merged: list[dict]
    jira_created: list[dict]
    jira_updated: list[dict]
    start_time: datetime
    end_time: datetime
    

def collect_work_data(
    repo_root: Path,
    github_repo: Optional[str],
    jira_project: Optional[str],
    since: datetime,
    github_client: Optional[GitHubClient],
    jira_client: Optional[JiraClient],
    config: dict
) -> WorkSummaryData:
    """
    Collect all work data from Git, GitHub, and Jira.
    
    Handles graceful degradation when services are not configured.
    """
    end_time = datetime.now()
    
    # Get configuration
    summary_config = config.get("daily_summary", {})
    include_own_commits = summary_config.get("include_own_commits_only", True)
    include_own_prs = summary_config.get("include_own_prs_only", True)
    include_own_issues = summary_config.get("include_own_issues_only", True)
    
    # Collect Git commits
    author = get_git_user_name(repo_root) if include_own_commits else None
    commits = get_all_commits_since(repo_root, since, author=author)
    
    # Collect GitHub PRs
    prs_opened = []
    prs_closed = []
    prs_merged = []
    
    if github_client and github_repo:
        github_user = github_client.get_current_user() if include_own_prs else None
        prs_opened = github_client.search_prs_by_date(github_repo, since, author=github_user)
        all_closed = github_client.get_closed_prs(github_repo, since, author=github_user)
        
        # Separate closed vs merged
        for pr in all_closed:
            if pr.get("merged_at"):
                prs_merged.append(pr)
            else:
                prs_closed.append(pr)
    
    # Collect Jira issues
    jira_created = []
    jira_updated = []
    
    if jira_client and jira_project:
        assignee = "currentUser()" if include_own_issues else None
        jira_created = jira_client.get_issues_created_since(jira_project, since, assignee)
        jira_updated = jira_client.get_issues_updated_since(jira_project, since, assignee)
    
    return WorkSummaryData(
        commits=commits,
        prs_opened=prs_opened,
        prs_closed=prs_closed,
        prs_merged=prs_merged,
        jira_created=jira_created,
        jira_updated=jira_updated,
        start_time=since,
        end_time=end_time
    )
```

### `pwm/summary/formatter.py`

```python
from typing import Optional

def format_markdown(data: WorkSummaryData, ai_summary: Optional[str] = None) -> str:
    """Format work summary data as markdown."""
    lines = []
    
    # Header
    lines.append("# Daily Work Summary")
    date_range = format_date_range(data.start_time, data.end_time)
    lines.append(f"**Period:** {date_range}")
    lines.append("")
    
    # Pull Requests section
    if data.prs_opened or data.prs_closed or data.prs_merged:
        lines.append("## Pull Requests")
        
        if data.prs_opened:
            lines.append(f"### Opened ({len(data.prs_opened)})")
            for pr in data.prs_opened:
                lines.append(f"- #{pr['number']} {pr['title']}")
            lines.append("")
        
        if data.prs_merged:
            lines.append(f"### Merged ({len(data.prs_merged)})")
            for pr in data.prs_merged:
                lines.append(f"- #{pr['number']} {pr['title']}")
            lines.append("")
        
        if data.prs_closed:
            lines.append(f"### Closed ({len(data.prs_closed)})")
            for pr in data.prs_closed:
                lines.append(f"- #{pr['number']} {pr['title']}")
            lines.append("")
    
    # Jira section
    if data.jira_created or data.jira_updated:
        lines.append("## Jira Issues")
        
        if data.jira_created:
            lines.append(f"### Created ({len(data.jira_created)})")
            for issue in data.jira_created:
                lines.append(f"- {issue['key']}: {issue['summary']}")
            lines.append("")
        
        if data.jira_updated:
            lines.append(f"### Updated ({len(data.jira_updated)})")
            for issue in data.jira_updated:
                status = issue.get('status', {}).get('name', 'Unknown')
                lines.append(f"- {issue['key']}: {issue['summary']} → {status}")
            lines.append("")
    
    # Commits section
    if data.commits:
        lines.append(f"## Commits ({len(data.commits)} total)")
        lines.append("")
        
        # Group by branch
        commits_by_branch = group_commits_by_branch(data.commits)
        
        for branch, commits in commits_by_branch.items():
            lines.append(f"### Branch: {branch} ({len(commits)} commits)")
            for commit in commits[:10]:  # Limit per branch
                lines.append(f"- {commit['subject']}")
            if len(commits) > 10:
                lines.append(f"- ... and {len(commits) - 10} more commits")
            lines.append("")
    
    # AI Summary
    if ai_summary:
        lines.append("## AI Summary")
        lines.append(ai_summary)
        lines.append("")
    
    return "\n".join(lines)


def format_text(data: WorkSummaryData, ai_summary: Optional[str] = None) -> str:
    """Format work summary data as plain text."""
    # Similar to markdown but without markdown syntax
    pass


def group_commits_by_branch(commits: list[dict]) -> dict[str, list[dict]]:
    """Group commits by their branch."""
    # Use git branch --contains to determine which branch each commit is on
    pass
```

### `pwm/summary/command.py`

```python
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
    output_file: Optional[str] = None
) -> int:
    """
    Generate daily work summary from previous business day to now.
    
    Returns 0 on success, 1 on error.
    """
    ctx = resolve_context()
    repo_root = ctx.repo_root
    
    # Determine start time
    if since is None:
        since = get_previous_business_day(datetime.now())
        rprint(f"[cyan]Calculating summary from previous business day...[/cyan]")
    
    rprint(f"[dim]Period: {since.strftime('%Y-%m-%d %H:%M')} to now[/dim]")
    
    # Initialize clients
    github = GitHubClient.from_config(ctx.config)
    jira = JiraClient.from_config(ctx.config)
    openai_client = OpenAIClient.from_config(ctx.config) if use_ai else None
    
    # Collect data
    rprint("[cyan]Collecting data...[/cyan]")
    data = collect_work_data(
        repo_root=repo_root,
        github_repo=ctx.github_repo,
        jira_project=ctx.jira_project,
        since=since,
        github_client=github,
        jira_client=jira,
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
        ai_summary = summarize_daily_work(data.commits, prs_dict, jira_dict, openai_client)
    
    # Format output
    output_format = format or ctx.config.get("daily_summary", {}).get("default_format", "markdown")
    
    if output_format == "text":
        output = format_text(data, ai_summary)
    else:
        output = format_markdown(data, ai_summary)
    
    # Display or save
    if output_file:
        Path(output_file).write_text(output)
        rprint(f"[green]✓ Summary saved to {output_file}[/green]")
    else:
        rprint()
        rprint(output)
    
    # Print statistics
    rprint()
    rprint("[bold green]Summary generated![/bold green]")
    rprint(f"[dim]Commits: {len(data.commits)}, PRs: {len(data.prs_opened + data.prs_closed + data.prs_merged)}, Jira: {len(data.jira_created + data.jira_updated)}[/dim]")
    
    return 0
```

## Test Files

### `tests/test_business_days.py`

```python
from datetime import datetime
from pwm.summary.business_days import get_previous_business_day

def test_monday_gets_friday():
    monday = datetime(2025, 1, 13, 12, 0)  # Monday Jan 13, 2025 at noon
    result = get_previous_business_day(monday)
    assert result.weekday() == 4  # Friday
    assert result.day == 10
    assert result.hour == 0

def test_tuesday_gets_monday():
    tuesday = datetime(2025, 1, 14, 12, 0)
    result = get_previous_business_day(tuesday)
    assert result.weekday() == 0  # Monday
    assert result.day == 13

def test_saturday_gets_friday():
    saturday = datetime(2025, 1, 11, 12, 0)
    result = get_previous_business_day(saturday)
    assert result.weekday() == 4  # Friday
    assert result.day == 10
```

## Configuration Example

Add to `example.pwm.toml`:

```toml
[daily_summary]
# Filter options - only show your own work
include_own_commits_only = true
include_own_prs_only = true
include_own_issues_only = true

# Display options
default_format = "markdown"  # or "text"
show_commit_details = true
group_commits_by_branch = true
max_commits_per_branch = 10

# Business day configuration
work_start_hour = 0   # 00:00
work_end_hour = 23    # 23:59
```

## Implementation Phases

### Phase 1: Core Infrastructure (2-3 hours)
- [ ] Create `pwm/summary/` directory
- [ ] Implement `business_days.py` with calculation logic
- [ ] Add `DailySummaryConfig` to `config/models.py`
- [ ] Write tests for business day calculations

### Phase 2: Data Collection (3-4 hours)
- [ ] Add `search_prs_by_date()` to `GitHubClient`
- [ ] Add `get_closed_prs()` to `GitHubClient`
- [ ] Add `search_issues_by_date()` to `JiraClient`
- [ ] Add `get_issues_created_since()` to `JiraClient`
- [ ] Add `get_issues_updated_since()` to `JiraClient`
- [ ] Add `get_all_commits_since()` to `git_cli.py`
- [ ] Write tests for all new client methods

### Phase 3: Data Aggregation (2-3 hours)
- [ ] Implement `collector.py` with `collect_work_data()`
- [ ] Handle graceful degradation for missing services
- [ ] Implement user filtering logic
- [ ] Write tests for collector

### Phase 4: Output Formatting (2-3 hours)
- [ ] Implement `formatter.py` with markdown formatter
- [ ] Implement text formatter
- [ ] Add commit grouping by branch
- [ ] Write tests for formatting

### Phase 5: AI Integration (1-2 hours)
- [ ] Add daily summary prompts to `ai/prompts.py`
- [ ] Implement `summarize_daily_work()` in `ai/summarizer.py`
- [ ] Test AI integration

### Phase 6: Command Integration (1-2 hours)
- [ ] Implement `command.py` with CLI logic
- [ ] Add command registration to `cli.py`
- [ ] Add command-line options
- [ ] Add rich console output

### Phase 7: Documentation (1 hour)
- [ ] Update README.md
- [ ] Update ROADMAP.md (if it exists)
- [ ] Add examples to `example.pwm.toml`
- [ ] Integration testing

**Total Estimated Time:** 12-18 hours

## Design Decisions

1. **Graceful Degradation:** Feature works without Jira, GitHub, or AI configured
2. **User Filtering:** Default to showing only current user's work (configurable)
3. **Business Day Logic:** Monday always gets Friday; weekends get Friday
4. **Output Formats:** Markdown (default) and plain text
5. **File Output:** Optional `--output` flag to save report
6. **AI Integration:** Optional, follows existing `--no-ai` pattern
7. **Performance:** Parallel API calls where possible (GitHub + Jira)
8. **Time Range:** Inclusive from start of previous business day (00:00) to current time

## Usage Examples

```bash
# Basic usage - Monday at noon gets Friday 00:00 to Monday 12:00
pwm daily-summary

# Alias
pwm ds

# Custom date range
pwm daily-summary --since "2025-01-10 09:00"

# Skip AI summary
pwm daily-summary --no-ai

# Save to file
pwm daily-summary --output daily-report.md

# Plain text format
pwm daily-summary --format text

# Markdown format with AI and save
pwm daily-summary --format markdown --output report.md
```

## Notes

- Follows existing pwm architectural patterns
- Reuses existing clients (GitHub, Jira, OpenAI)
- Follows security best practices (token redaction)
- Comprehensive test coverage required
- Rich console output for progress indicators
- Handles timezones consistently (use UTC where possible)
