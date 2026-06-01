import typer
from typing import Optional
from time import perf_counter

from pwm.context.command import show_context
from pwm.setup.init import init_project
from pwm.prompt.command import prompt_command, PromptFormat
from pwm.work.start import work_start
from pwm.work.create import issue_create
from pwm.work.create_issue import parse_custom_field_values
from pwm.work.end import work_end
from pwm.check.self_check import self_check
from pwm.pr.open import open_pr
from pwm.summary.command import daily_summary
from pwm.log.events import append_event
from pwm.work.epic_history import epic_history_command

app = typer.Typer(help="Personal Workflow Manager")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show top-level help when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def context():
    """Show resolved project context (repo root, GitHub repo, Jira project, config paths)."""
    show_context()


@app.command()
def init():
    """Scaffold a .pwm.toml in the current project."""
    init_project()


@app.command("work-start")
@app.command("ws")
def work_start_cmd(
    ctx: typer.Context,
    issue_key: str = typer.Argument(
        None, help="Jira issue key (e.g., ABC-123). Omit if using --new."
    ),
    new: bool = typer.Option(
        False, "--new", help="Create a new Jira issue interactively"
    ),
    no_transition: bool = typer.Option(False, help="Do not transition Jira issue"),
    no_comment: bool = typer.Option(False, help="Do not add Jira comment"),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Fail instead of prompting for missing values when using --new",
    ),
    summary: Optional[str] = typer.Option(
        None,
        "--summary",
        help="Jira summary for --new (required with --non-interactive)",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        help="Jira description for --new",
    ),
    issue_type: Optional[str] = typer.Option(
        None,
        "--issue-type",
        help="Jira issue type for --new (for example: Story, Task, Bug)",
    ),
    labels: Optional[str] = typer.Option(
        None,
        "--labels",
        help="Comma-separated labels for --new",
    ),
    story_points: Optional[float] = typer.Option(
        None,
        "--story-points",
        help="Story points for --new",
    ),
    epic: Optional[str] = typer.Option(
        None,
        "--epic",
        help="Parent epic key for --new (for example: ABC-123)",
    ),
    custom_field: list[str] = typer.Option(
        None,
        "--custom-field",
        help="Repeatable KEY=VALUE pairs for Jira custom fields",
    ),
    save_defaults: bool = typer.Option(
        False,
        "--save-defaults",
        help="Save provided issue values as defaults after creation",
    ),
    no_save_defaults: bool = typer.Option(
        False,
        "--no-save-defaults",
        help="Do not save issue values as defaults after creation",
    ),
):
    """Start work on a Jira issue: create or switch branch and optionally update Jira."""
    started_at = perf_counter()
    if not issue_key and not new:
        append_event(
            command="ws",
            args={
                "issue_key": issue_key,
                "new": new,
                "non_interactive": non_interactive,
            },
            details={
                "status": "success",
                "exit_code": 0,
                "note": "Displayed command help",
            },
        )
        typer.echo(ctx.get_help())
        raise typer.Exit(0)

    if save_defaults and no_save_defaults:
        append_event(
            command="ws",
            args={"new": new},
            details={
                "status": "error",
                "exit_code": 2,
                "error": "Conflicting save-default flags",
            },
        )
        raise typer.BadParameter(
            "Cannot use both --save-defaults and --no-save-defaults"
        )

    parsed_labels = None
    if labels is not None:
        parsed_labels = [label.strip() for label in labels.split(",") if label.strip()]

    parsed_custom_fields = None
    if custom_field:
        try:
            parsed_custom_fields = parse_custom_field_values(custom_field)
        except ValueError as exc:
            append_event(
                command="ws",
                args={"new": new, "custom_field": custom_field},
                details={
                    "status": "error",
                    "exit_code": 2,
                    "error": str(exc),
                },
            )
            raise typer.BadParameter(str(exc)) from exc

    resolved_save_defaults = None
    if save_defaults:
        resolved_save_defaults = True
    elif no_save_defaults:
        resolved_save_defaults = False

    run_details: dict = {}
    exit_code = work_start(
        issue_key=issue_key,
        create_new=new,
        transition=not no_transition,
        comment=not no_comment,
        non_interactive=non_interactive,
        summary=summary,
        description=description,
        issue_type=issue_type,
        labels=parsed_labels,
        story_points=story_points,
        epic=epic,
        custom_fields=parsed_custom_fields,
        save_defaults=resolved_save_defaults,
        event_details=run_details,
    )

    duration_ms = int((perf_counter() - started_at) * 1000)
    append_event(
        command="ws",
        args={
            "issue_key": issue_key,
            "new": new,
            "no_transition": no_transition,
            "no_comment": no_comment,
            "non_interactive": non_interactive,
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "labels": parsed_labels,
            "story_points": story_points,
            "epic": epic,
            "custom_fields": parsed_custom_fields,
            "save_defaults": resolved_save_defaults,
        },
        details={
            "status": "success" if exit_code == 0 else "error",
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            **run_details,
        },
    )
    raise SystemExit(exit_code)


@app.command("work-end")
@app.command("we")
def work_end_cmd(
    message: str = typer.Option(None, "--message", "-m", help="Custom status message"),
    no_comment: bool = typer.Option(False, "--no-comment", help="Skip all comments"),
    no_pr_comment: bool = typer.Option(
        False, "--no-pr-comment", help="Skip PR comment"
    ),
    no_jira_comment: bool = typer.Option(
        False, "--no-jira-comment", help="Skip Jira comment"
    ),
    request_review: bool = typer.Option(
        False, "--request-review", help="Request reviewers from config"
    ),
) -> None:
    """Post status update to PR and Jira issue."""
    raise SystemExit(
        work_end(
            message=message,
            no_comment=no_comment,
            no_pr_comment=no_pr_comment,
            no_jira_comment=no_jira_comment,
            request_review=request_review,
        )
    )


@app.command("issue-create")
@app.command("ic")
def issue_create_cmd(
    ctx: typer.Context,
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Fail instead of prompting for missing values",
    ),
    summary: Optional[str] = typer.Option(
        None,
        "--summary",
        help="Jira summary (required with --non-interactive)",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        help="Jira description",
    ),
    issue_type: Optional[str] = typer.Option(
        None,
        "--issue-type",
        help="Jira issue type (for example: Story, Task, Bug)",
    ),
    labels: Optional[str] = typer.Option(
        None,
        "--labels",
        help="Comma-separated labels",
    ),
    story_points: Optional[float] = typer.Option(
        None,
        "--story-points",
        help="Story points",
    ),
    epic: Optional[str] = typer.Option(
        None,
        "--epic",
        help="Parent epic key (for example: ABC-123)",
    ),
    custom_field: list[str] = typer.Option(
        None,
        "--custom-field",
        help="Repeatable KEY=VALUE pairs for Jira custom fields",
    ),
    save_defaults: bool = typer.Option(
        False,
        "--save-defaults",
        help="Save provided issue values as defaults after creation",
    ),
    no_save_defaults: bool = typer.Option(
        False,
        "--no-save-defaults",
        help="Do not save issue values as defaults after creation",
    ),
) -> None:
    """Create a Jira issue without branch or transition actions."""
    started_at = perf_counter()

    has_intent = any(
        [
            non_interactive,
            summary is not None,
            description is not None,
            issue_type is not None,
            labels is not None,
            story_points is not None,
            epic is not None,
            bool(custom_field),
            save_defaults,
            no_save_defaults,
        ]
    )
    if not has_intent:
        append_event(
            command="ic",
            args={},
            details={
                "status": "success",
                "exit_code": 0,
                "note": "Displayed command help",
            },
        )
        typer.echo(ctx.get_help())
        raise typer.Exit(0)

    if save_defaults and no_save_defaults:
        append_event(
            command="ic",
            args={},
            details={
                "status": "error",
                "exit_code": 2,
                "error": "Conflicting save-default flags",
            },
        )
        raise typer.BadParameter(
            "Cannot use both --save-defaults and --no-save-defaults"
        )

    parsed_labels = None
    if labels is not None:
        parsed_labels = [label.strip() for label in labels.split(",") if label.strip()]

    parsed_custom_fields = None
    if custom_field:
        try:
            parsed_custom_fields = parse_custom_field_values(custom_field)
        except ValueError as exc:
            append_event(
                command="ic",
                args={"custom_field": custom_field},
                details={
                    "status": "error",
                    "exit_code": 2,
                    "error": str(exc),
                },
            )
            raise typer.BadParameter(str(exc)) from exc

    resolved_save_defaults = None
    if save_defaults:
        resolved_save_defaults = True
    elif no_save_defaults:
        resolved_save_defaults = False

    run_details: dict = {}
    exit_code = issue_create(
        non_interactive=non_interactive,
        summary=summary,
        description=description,
        issue_type=issue_type,
        labels=parsed_labels,
        story_points=story_points,
        epic=epic,
        custom_fields=parsed_custom_fields,
        save_defaults=resolved_save_defaults,
        event_details=run_details,
    )

    duration_ms = int((perf_counter() - started_at) * 1000)
    append_event(
        command="ic",
        args={
            "non_interactive": non_interactive,
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "labels": parsed_labels,
            "story_points": story_points,
            "epic": epic,
            "custom_fields": parsed_custom_fields,
            "save_defaults": resolved_save_defaults,
        },
        details={
            "status": "success" if exit_code == 0 else "error",
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            **run_details,
        },
    )
    raise SystemExit(exit_code)


@app.command("self-check")
def self_check_cmd() -> None:
    """Run connectivity and setup checks for git, Jira, and GitHub."""
    raise SystemExit(self_check())


@app.command("epic-history")
def epic_history_cmd(
    project: Optional[str] = typer.Option(
        None, "--project", help="Filter history by Jira project key"
    ),
    limit: int = typer.Option(50, "--limit", min=1, help="Maximum rows to show"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    clear: bool = typer.Option(False, "--clear", help="Clear epic history cache"),
    set_default: Optional[str] = typer.Option(
        None,
        "--set-default",
        help="Set repo-local default parent epic key",
    ),
    clear_default: bool = typer.Option(
        False,
        "--clear-default",
        help="Clear repo-local default parent epic key",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Skip confirmation when used with --clear",
    ),
) -> None:
    """Inspect or clear cached parent epic history."""
    raise SystemExit(
        epic_history_command(
            project=project,
            limit=limit,
            as_json=json_output,
            clear=clear,
            yes=yes,
            set_default=set_default,
            clear_default=clear_default,
        )
    )


@app.command()
def prompt(
    with_status: bool = typer.Option(
        False, "--with-status", help="Fetch and display Jira issue status"
    ),
    format: PromptFormat = typer.Option(
        PromptFormat.DEFAULT,
        "--format",
        help="Output format: default, minimal, or emoji",
    ),
    color: bool = typer.Option(False, "--color", help="Use ANSI color codes"),
) -> None:
    """Generate shell prompt information for current work context."""
    raise SystemExit(
        prompt_command(with_status=with_status, format_type=format, use_color=color)
    )


@app.command()
def pr(
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI-generated summary"),
    create_anyway: bool = typer.Option(
        False,
        "--create-anyway",
        "-y",
        help="Create PR even when no commits are detected",
    ),
    no_open_browser: bool = typer.Option(
        False,
        "--no-open-browser",
        help="Do not open PR URL in a browser",
    ),
    title: Optional[str] = typer.Option(None, "--title", help="Override PR title"),
    body: Optional[str] = typer.Option(None, "--body", help="Override PR body"),
    label: Optional[list[str]] = typer.Option(
        None,
        "--label",
        help="Repeatable PR label (for example: --label bug)",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Fail instead of prompting for confirmation",
    ),
) -> None:
    """Open or create a pull request for the current branch."""
    started_at = perf_counter()
    normalized_labels = None
    if label:
        seen_labels = set()
        normalized_labels = []
        for raw_label in label:
            stripped_label = raw_label.strip()
            if not stripped_label or stripped_label in seen_labels:
                continue
            seen_labels.add(stripped_label)
            normalized_labels.append(stripped_label)

    run_details: dict = {}
    exit_code = open_pr(
        use_ai=not no_ai,
        create_anyway=create_anyway,
        open_browser=not no_open_browser,
        title_override=title,
        body_override=body,
        labels=normalized_labels,
        non_interactive=non_interactive,
        event_details=run_details,
    )
    duration_ms = int((perf_counter() - started_at) * 1000)
    append_event(
        command="pr",
        args={
            "no_ai": no_ai,
            "create_anyway": create_anyway,
            "no_open_browser": no_open_browser,
            "title": title,
            "body": body,
            "labels": normalized_labels,
            "non_interactive": non_interactive,
        },
        details={
            "status": "success" if exit_code == 0 else "error",
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            **run_details,
        },
    )
    raise SystemExit(exit_code)


@app.command("daily-summary")
@app.command("ds")
def daily_summary_cmd(
    since: str = typer.Option(
        None,
        "--since",
        help="Start time (YYYY-MM-DD or YYYY-MM-DD HH:MM)",
    ),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI-generated summary"),
    format: str = typer.Option(
        None, "--format", help="Output format: text or markdown"
    ),
    output: str = typer.Option(None, "--output", "-o", help="Save to file"),
    links: bool = typer.Option(
        False, "--links", help="Show URLs for PRs and Jira issues"
    ),
) -> None:
    """Generate summary of work from previous business day to now."""
    # Parse since if provided
    since_dt = None
    if since:
        from datetime import datetime

        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                since_dt = datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                from rich import print as rprint

                rprint(
                    "[red]Error:[/red] Invalid date format. "
                    "Use: YYYY-MM-DD or YYYY-MM-DD HH:MM"
                )
                raise typer.Exit(1)

    raise SystemExit(
        daily_summary(
            since=since_dt,
            use_ai=not no_ai,
            format=format,
            output_file=output,
            show_links=links,
        )
    )


if __name__ == "__main__":
    app()
