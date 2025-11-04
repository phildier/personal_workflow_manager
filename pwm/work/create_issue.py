
from __future__ import annotations
from pathlib import Path
from typing import Optional
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from pwm.jira.client import JiraClient
from pwm.config.loader import load_merged_config

def prompt_for_issue_details(
    jira: JiraClient,
    project_key: str,
    default_issue_type: str = "Story",
    default_labels: Optional[list[str]] = None,
    default_custom_fields: Optional[dict] = None
) -> Optional[dict]:
    """
    Interactively prompt for issue details.

    Returns a dict with 'summary', 'description', 'issue_type', 'labels', 'custom_fields' or None if cancelled.
    """
    rprint("[bold cyan]Create new Jira issue[/bold cyan]")

    # Get available issue types
    issue_types = jira.get_issue_types(project_key)
    issue_type_names = [it["name"] for it in issue_types] if issue_types else ["Story", "Task", "Bug"]

    # Summary (required)
    summary = Prompt.ask("[yellow]Summary[/yellow] (required)")
    if not summary.strip():
        rprint("[red]Summary is required. Cancelled.[/red]")
        return None

    # Description (optional)
    description = Prompt.ask("[yellow]Description[/yellow] (optional, press Enter to skip)", default="")

    # Issue type
    if default_issue_type in issue_type_names:
        default_type = default_issue_type
    elif issue_type_names:
        default_type = issue_type_names[0]
    else:
        default_type = "Story"

    if len(issue_type_names) > 1:
        rprint(f"[dim]Available types: {', '.join(issue_type_names)}[/dim]")
        issue_type = Prompt.ask("[yellow]Issue type[/yellow]", default=default_type)
    else:
        issue_type = default_type
        rprint(f"[dim]Using issue type: {issue_type}[/dim]")

    # Labels (optional, comma-separated)
    default_labels_str = ",".join(default_labels) if default_labels else ""
    labels_input = Prompt.ask(
        "[yellow]Labels[/yellow] (comma-separated, optional)",
        default=default_labels_str
    )
    labels = [l.strip() for l in labels_input.split(",") if l.strip()] if labels_input else []

    # Story points (optional, numeric)
    # Check if we have a story points field in defaults
    story_points_field_id = None
    default_story_points = None
    for field_id, value in (default_custom_fields or {}).items():
        if field_id.startswith("customfield_") and isinstance(value, (int, float)):
            # This might be story points - we'll verify against metadata later
            story_points_field_id = field_id
            default_story_points = value
            break

    story_points_str = str(default_story_points) if default_story_points else ""
    story_points_input = Prompt.ask(
        "[yellow]Story points[/yellow] (optional, press Enter to skip)",
        default=story_points_str
    )
    story_points = None
    if story_points_input.strip():
        try:
            story_points = float(story_points_input)
        except ValueError:
            rprint("[yellow]Invalid story points value, skipping.[/yellow]")

    # Get field metadata to discover required custom fields
    rprint("[dim]Checking for required fields...[/dim]")
    metadata = jira.get_create_metadata(project_key, issue_type)

    custom_fields = {}
    default_custom_fields = default_custom_fields or {}

    # Find story points field in metadata and add it if user provided a value
    if story_points is not None and metadata:
        for field_id, field_info in metadata.items():
            field_name = field_info.get("name", "")
            field_schema = field_info.get("schema", {})
            field_type = field_schema.get("type", "")

            # Look for story points field (common names and numeric type)
            if field_type == "number" and field_name.lower() in ["story points", "storypoints", "story point estimate"]:
                custom_fields[field_id] = story_points
                story_points_field_id = field_id
                break

    if metadata:
        for field_id, field_info in metadata.items():
            # Skip standard fields we already handle
            if field_id in ["summary", "description", "issuetype", "project", "labels"]:
                continue

            # Skip story points field if we already processed it
            if field_id == story_points_field_id:
                continue

            # Only prompt for required fields
            if not field_info.get("required", False):
                continue

            field_name = field_info.get("name", field_id)
            field_schema = field_info.get("schema", {})
            field_type = field_schema.get("type", "")

            # Check if we have a default value for this field
            default_value = default_custom_fields.get(field_id)

            # Handle different field types
            if field_type == "string":
                default_str = default_value if isinstance(default_value, str) else ""
                value = Prompt.ask(f"[yellow]{field_name}[/yellow] (required)", default=default_str)
                if value.strip():
                    custom_fields[field_id] = value
            elif field_type == "number":
                # Numeric field (e.g., story points if it's required)
                default_str = str(default_value) if isinstance(default_value, (int, float)) else ""
                value_str = Prompt.ask(f"[yellow]{field_name}[/yellow] (required, numeric)", default=default_str)
                if value_str.strip():
                    try:
                        custom_fields[field_id] = float(value_str)
                    except ValueError:
                        rprint(f"[red]Invalid numeric value for {field_name}[/red]")
            elif field_type == "option":
                # Single-select field
                allowed_values = field_info.get("allowedValues", [])
                if allowed_values:
                    options = [v.get("value") or v.get("name") for v in allowed_values]
                    rprint(f"[dim]Available options: {', '.join(options)}[/dim]")
                    # Extract default from config if it exists
                    default_str = ""
                    if isinstance(default_value, dict) and "value" in default_value:
                        default_str = default_value["value"]
                    elif not default_str and options:
                        default_str = options[0]
                    value = Prompt.ask(f"[yellow]{field_name}[/yellow] (required)", default=default_str)
                    if value:
                        # Find the matching option
                        for av in allowed_values:
                            if (av.get("value") == value or av.get("name") == value):
                                custom_fields[field_id] = {"value": av.get("value") or av.get("name")}
                                break
            elif field_type == "array" and field_schema.get("items") == "option":
                # Multi-select field
                allowed_values = field_info.get("allowedValues", [])
                if allowed_values:
                    options = [v.get("value") or v.get("name") for v in allowed_values]
                    rprint(f"[dim]Available options: {', '.join(options)}[/dim]")
                    # Extract default from config if it exists
                    default_str = ""
                    if isinstance(default_value, list):
                        default_str = ",".join([v.get("value", "") if isinstance(v, dict) else str(v) for v in default_value])
                    elif not default_str and options:
                        default_str = options[0]
                    value = Prompt.ask(f"[yellow]{field_name}[/yellow] (comma-separated)", default=default_str)
                    if value:
                        selected = [v.strip() for v in value.split(",")]
                        custom_fields[field_id] = [{"value": s} for s in selected if s]
            else:
                # Unsupported field type, show warning
                rprint(f"[yellow]Warning: Required field '{field_name}' (type: {field_type}) cannot be set automatically.[/yellow]")
                rprint(f"[yellow]You may need to update the issue manually in Jira.[/yellow]")

    return {
        "summary": summary,
        "description": description or None,
        "issue_type": issue_type,
        "labels": labels,
        "custom_fields": custom_fields
    }

def save_issue_defaults(repo_root: Path, issue_type: str, labels: list[str]) -> None:
    """
    Save issue defaults to project config.

    Updates the .pwm.toml file with the new defaults.
    """
    config_path = repo_root / ".pwm.toml"

    # Read existing config
    existing_lines = []
    if config_path.exists():
        existing_lines = config_path.read_text().splitlines()

    # Remove old [jira.issue_defaults] section if it exists
    new_lines = []
    skip_section = False
    for line in existing_lines:
        if line.strip() == "[jira.issue_defaults]":
            skip_section = True
            continue
        elif line.strip().startswith("[") and skip_section:
            skip_section = False
        if not skip_section:
            new_lines.append(line)

    # Add new defaults section
    new_lines.append("")
    new_lines.append("[jira.issue_defaults]")
    new_lines.append(f'issue_type = "{issue_type}"')
    if labels:
        labels_str = ", ".join(f'"{l}"' for l in labels)
        new_lines.append(f"labels = [{labels_str}]")

    config_path.write_text("\n".join(new_lines) + "\n")
    rprint(f"[dim]Saved defaults to {config_path}[/dim]")

def create_new_issue(
    jira: JiraClient,
    project_key: str,
    repo_root: Path,
    config: dict
) -> Optional[str]:
    """
    Create a new Jira issue interactively.

    Returns the issue key if successful, None otherwise.
    """
    # Get defaults from config
    defaults = config.get("jira", {}).get("issue_defaults", {})
    default_issue_type = defaults.get("issue_type", "Story")
    default_labels = defaults.get("labels", [])
    default_custom_fields = defaults.get("custom_fields", {})

    # Prompt for details
    details = prompt_for_issue_details(jira, project_key, default_issue_type, default_labels, default_custom_fields)
    if not details:
        return None

    # Create issue
    rprint("[cyan]Creating issue...[/cyan]")
    issue_key = jira.create_issue(
        project_key=project_key,
        summary=details["summary"],
        issue_type=details["issue_type"],
        description=details["description"],
        labels=details["labels"],
        custom_fields=details.get("custom_fields", {})
    )

    if not issue_key:
        rprint("[red]Failed to create issue.[/red]")
        return None

    rprint(f"[green]Created issue: {issue_key}[/green]")
    rprint(f"[dim]{jira.base_url}/browse/{issue_key}[/dim]")

    # Save defaults for next time
    if details["issue_type"] != default_issue_type or details["labels"] != default_labels:
        save_defaults = Confirm.ask("Save issue type and labels as defaults?", default=True)
        if save_defaults:
            save_issue_defaults(repo_root, details["issue_type"], details["labels"])

    return issue_key
