from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from pwm.jira.client import JiraClient
from pwm.work.epic_history import load_epic_history, upsert_epic_history
from pwm.work.terminal import ensure_backspace_support


STANDARD_CREATE_FIELDS = {
    "summary",
    "description",
    "issuetype",
    "project",
    "labels",
}

PARENT_COMPATIBLE_ISSUE_TYPES = {"story", "bug", "spike", "task", "incident"}


def _is_parent_compatible_issue_type(issue_type: str) -> bool:
    """Return True when issue type can link to a parent epic."""
    return issue_type.strip().lower() in PARENT_COMPATIBLE_ISSUE_TYPES


def record_epic_in_history(epic_key: str, title: str, project_key: str) -> None:
    """Store or refresh an epic entry in history."""
    upsert_epic_history(epic_key, title, project_key)


def _prompt_for_parent_epic(
    issue_type: str,
    project_key: str,
    default_parent_epic_key: Optional[str],
) -> Optional[str]:
    """Prompt for optional parent epic using prompt_toolkit search."""
    if not _is_parent_compatible_issue_type(issue_type):
        return None

    history = [
        entry
        for entry in load_epic_history()
        if not project_key or entry.get("project_key") in {"", project_key}
    ]
    if not history:
        return None

    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
    except Exception:
        rprint("[yellow]Warning: prompt_toolkit unavailable; skipping epic picker.[/yellow]")
        return None

    labels = [f"{entry['key']} {entry['title']}" for entry in history]
    completer = FuzzyCompleter(WordCompleter(labels, ignore_case=True))

    if default_parent_epic_key:
        rprint(
            "[dim]Tip: type 'default' to use saved parent epic "
            f"{default_parent_epic_key}.[/dim]"
        )

    while True:
        query = pt_prompt(
            "Parent epic (search key/title, Enter for none): ",
            completer=completer,
            complete_while_typing=True,
        ).strip()

        if not query:
            return None
        if default_parent_epic_key and query.lower() == "default":
            return default_parent_epic_key

        for entry in history:
            if query.upper() == entry["key"].upper():
                return entry["key"]

        query_lower = query.lower()
        matches = [
            entry
            for entry in history
            if query_lower in entry["key"].lower()
            or query_lower in entry["title"].lower()
        ]
        if len(matches) == 1:
            return matches[0]["key"]

        if len(matches) > 1:
            preview = ", ".join(
                [f"{entry['key']} ({entry['title']})" for entry in matches[:5]]
            )
            rprint(f"[yellow]Multiple matches:[/yellow] {preview}")
            rprint("[dim]Keep typing to narrow, or enter exact epic key.[/dim]")
            continue

        rprint("[yellow]No epic match found. Try again, or press Enter for none.[/yellow]")


def build_non_interactive_issue_details(
    jira: JiraClient,
    project_key: str,
    config: dict,
    summary: str,
    description: Optional[str] = None,
    issue_type: Optional[str] = None,
    labels: Optional[list[str]] = None,
    story_points: Optional[float] = None,
    parent_epic_key: Optional[str] = None,
    custom_fields: Optional[dict] = None,
) -> Optional[dict]:
    """Build issue details without interactive prompts."""
    defaults = config.get("jira", {}).get("issue_defaults", {})
    resolved_issue_type = issue_type or defaults.get("issue_type", "Story")
    resolved_labels = labels if labels is not None else defaults.get("labels", [])

    default_custom_fields = defaults.get("custom_fields", {})
    resolved_custom_fields = dict(default_custom_fields)
    if custom_fields:
        resolved_custom_fields.update(custom_fields)

    metadata = jira.get_create_metadata(project_key, resolved_issue_type)
    resolved_parent_epic_key = None
    if parent_epic_key and _is_parent_compatible_issue_type(resolved_issue_type):
        resolved_parent_epic_key = parent_epic_key.strip() or None
    elif parent_epic_key:
        rprint(
            "[yellow]Warning: --epic is ignored for issue type "
            f"{resolved_issue_type}.[/yellow]"
        )

    # Map story points into the proper custom field if available.
    if story_points is not None and metadata:
        story_points_field_id = None
        for field_id, field_info in metadata.items():
            field_name = field_info.get("name", "")
            field_schema = field_info.get("schema", {})
            field_type = field_schema.get("type", "")
            if field_type == "number" and field_name.lower() in {
                "story points",
                "storypoints",
                "story point estimate",
            }:
                story_points_field_id = field_id
                break

        if story_points_field_id:
            resolved_custom_fields[story_points_field_id] = story_points
        else:
            rprint(
                "[yellow]Warning: Story points field not found in Jira metadata; "
                "ignoring --story-points.[/yellow]"
            )

    missing_required_fields: list[str] = []
    for field_id, field_info in metadata.items():
        if field_id in STANDARD_CREATE_FIELDS:
            continue
        if not field_info.get("required", False):
            continue
        if field_id not in resolved_custom_fields:
            field_name = field_info.get("name", field_id)
            missing_required_fields.append(field_name)

    if missing_required_fields:
        joined = ", ".join(sorted(missing_required_fields))
        rprint(
            "[red]Error: Missing required Jira fields for non-interactive "
            f"issue creation: {joined}[/red]"
        )
        return None

    return {
        "summary": summary,
        "description": description or None,
        "issue_type": resolved_issue_type,
        "labels": resolved_labels,
        "parent_epic_key": resolved_parent_epic_key,
        "custom_fields": resolved_custom_fields,
    }


def parse_custom_field_values(custom_field_pairs: Optional[list[str]]) -> dict:
    """Parse repeated --custom-field KEY=VALUE options into a dict."""
    parsed: dict = {}
    for pair in custom_field_pairs or []:
        if "=" not in pair:
            raise ValueError(
                f"Invalid --custom-field '{pair}'. Expected KEY=VALUE format."
            )
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Invalid --custom-field with empty key.")

        raw = value.strip()
        if not raw:
            parsed[key] = ""
            continue

        try:
            parsed[key] = json.loads(raw)
        except json.JSONDecodeError:
            parsed[key] = raw

    return parsed


def prompt_for_issue_details(
    jira: JiraClient,
    project_key: str,
    default_issue_type: str = "Story",
    default_labels: Optional[list[str]] = None,
    default_parent_epic_key: Optional[str] = None,
    default_custom_fields: Optional[dict] = None,
) -> Optional[dict]:
    """
    Interactively prompt for issue details.

    Returns issue details dict or None if cancelled.
    """
    with ensure_backspace_support():
        rprint("[bold cyan]Create new Jira issue[/bold cyan]")

        # Get available issue types
        issue_types = jira.get_issue_types(project_key)
        issue_type_names = (
            [it["name"] for it in issue_types]
            if issue_types
            else ["Story", "Task", "Bug"]
        )

        # Summary (required)
        summary = Prompt.ask("[yellow]Summary[/yellow] (required)")
        if not summary.strip():
            rprint("[red]Summary is required. Cancelled.[/red]")
            return None

        # Description (optional)
        description = Prompt.ask(
            "[yellow]Description[/yellow] (optional, press Enter to skip)", default=""
        )

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

        parent_epic_key = _prompt_for_parent_epic(
            issue_type,
            project_key,
            default_parent_epic_key,
        )

        # Labels (optional, comma-separated)
        default_labels_str = ",".join(default_labels) if default_labels else ""
        labels_input = Prompt.ask(
            "[yellow]Labels[/yellow] (comma-separated, optional)",
            default=default_labels_str,
        )
        labels = (
            [l.strip() for l in labels_input.split(",") if l.strip()]
            if labels_input
            else []
        )

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
            default=story_points_str,
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

        # Find story points field in metadata and add it if user provided
        if story_points is not None and metadata:
            for field_id, field_info in metadata.items():
                field_name = field_info.get("name", "")
                field_schema = field_info.get("schema", {})
                field_type = field_schema.get("type", "")

                # Look for story points field (common names and numeric type)
                if field_type == "number" and field_name.lower() in [
                    "story points",
                    "storypoints",
                    "story point estimate",
                ]:
                    custom_fields[field_id] = story_points
                    story_points_field_id = field_id
                    break

        if metadata:
            for field_id, field_info in metadata.items():
                # Skip standard fields we already handle
                if field_id in [
                    "summary",
                    "description",
                    "issuetype",
                    "project",
                    "labels",
                ]:
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
                    default_str = (
                        default_value if isinstance(default_value, str) else ""
                    )
                    value = Prompt.ask(
                        f"[yellow]{field_name}[/yellow] (required)", default=default_str
                    )
                    if value.strip():
                        custom_fields[field_id] = value
                elif field_type == "number":
                    # Numeric field (e.g., story points if it's required)
                    default_str = (
                        str(default_value)
                        if isinstance(default_value, (int, float))
                        else ""
                    )
                    value_str = Prompt.ask(
                        f"[yellow]{field_name}[/yellow] (required, numeric)",
                        default=default_str,
                    )
                    if value_str.strip():
                        try:
                            custom_fields[field_id] = float(value_str)
                        except ValueError:
                            rprint(f"[red]Invalid numeric value for {field_name}[/red]")
                elif field_type == "option":
                    # Single-select field
                    allowed_values = field_info.get("allowedValues", [])
                    if allowed_values:
                        options = [
                            v.get("value") or v.get("name") for v in allowed_values
                        ]
                        rprint(f"[dim]Available options: {', '.join(options)}[/dim]")
                        # Extract default from config if it exists
                        default_str = ""
                        if isinstance(default_value, dict) and "value" in default_value:
                            default_str = default_value["value"]
                        elif not default_str and options:
                            default_str = options[0]
                        value = Prompt.ask(
                            f"[yellow]{field_name}[/yellow] (required)",
                            default=default_str,
                        )
                        if value:
                            # Find the matching option
                            for av in allowed_values:
                                if av.get("value") == value or av.get("name") == value:
                                    custom_fields[field_id] = {
                                        "value": av.get("value") or av.get("name")
                                    }
                                    break
                elif field_type == "array" and field_schema.get("items") == "option":
                    # Multi-select field
                    allowed_values = field_info.get("allowedValues", [])
                    if allowed_values:
                        options = [
                            v.get("value") or v.get("name") for v in allowed_values
                        ]
                        rprint(f"[dim]Available options: {', '.join(options)}[/dim]")
                        # Extract default from config if it exists
                        default_str = ""
                        if isinstance(default_value, list):
                            default_str = ",".join(
                                [
                                    v.get("value", "")
                                    if isinstance(v, dict)
                                    else str(v)
                                    for v in default_value
                                ]
                            )
                        elif not default_str and options:
                            default_str = options[0]
                        value = Prompt.ask(
                            f"[yellow]{field_name}[/yellow] (comma-separated)",
                            default=default_str,
                        )
                        if value:
                            selected = [v.strip() for v in value.split(",")]
                            custom_fields[field_id] = [
                                {"value": s} for s in selected if s
                            ]
                else:
                    # Unsupported field type, show warning
                    rprint(
                        f"[yellow]Warning: Required field '{field_name}' "
                        f"(type: {field_type}) cannot be set automatically."
                        "[/yellow]"
                    )
                    rprint(
                        "[yellow]You may need to update the issue manually in "
                        "Jira.[/yellow]"
                    )

    return {
        "summary": summary,
        "description": description or None,
        "issue_type": issue_type,
        "labels": labels,
        "parent_epic_key": parent_epic_key,
        "custom_fields": custom_fields,
    }


def save_issue_defaults(
    repo_root: Path,
    issue_type: str,
    labels: list[str],
    parent_epic_key: Optional[str] = None,
    custom_fields: Optional[dict] = None,
) -> None:
    """
    Save issue defaults to project config.

    Updates the .pwm.toml file with the new defaults.
    """
    import tomllib
    import toml  # For writing TOML

    config_path = repo_root / ".pwm.toml"

    # Read existing config as dict
    existing_config = {}
    if config_path.exists():
        with config_path.open("rb") as f:
            existing_config = tomllib.load(f)

    # Update jira.issue_defaults section
    if "jira" not in existing_config:
        existing_config["jira"] = {}

    existing_config["jira"]["issue_defaults"] = {"issue_type": issue_type}

    if labels:
        existing_config["jira"]["issue_defaults"]["labels"] = labels

    if parent_epic_key:
        existing_config["jira"]["issue_defaults"]["parent_epic_key"] = (
            parent_epic_key
        )

    # Add custom fields if provided
    if custom_fields:
        existing_config["jira"]["issue_defaults"]["custom_fields"] = {}
        for field_id, value in custom_fields.items():
            existing_config["jira"]["issue_defaults"]["custom_fields"][field_id] = value

    # Write back to file
    with config_path.open("w") as f:
        toml.dump(existing_config, f)

    rprint(f"[dim]Saved defaults to {config_path}[/dim]")


def create_new_issue(
    jira: JiraClient,
    project_key: str,
    repo_root: Path,
    config: dict,
    *,
    non_interactive: bool = False,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    issue_type: Optional[str] = None,
    labels: Optional[list[str]] = None,
    story_points: Optional[float] = None,
    epic: Optional[str] = None,
    custom_fields: Optional[dict] = None,
    save_defaults: Optional[bool] = None,
) -> Optional[str]:
    """
    Create a new Jira issue interactively.

    Returns the issue key if successful, None otherwise.
    """
    # Get defaults from config
    defaults = config.get("jira", {}).get("issue_defaults", {})
    default_issue_type = defaults.get("issue_type", "Story")
    default_labels = defaults.get("labels", [])
    default_parent_epic_key = defaults.get("parent_epic_key")
    default_custom_fields = defaults.get("custom_fields", {})

    if non_interactive:
        if not summary:
            rprint(
                "[red]Error: --summary is required when using "
                "--non-interactive with --new.[/red]"
            )
            return None
        details = build_non_interactive_issue_details(
            jira=jira,
            project_key=project_key,
            config=config,
            summary=summary,
            description=description,
            issue_type=issue_type,
            labels=labels,
            story_points=story_points,
            parent_epic_key=epic,
            custom_fields=custom_fields,
        )
    else:
        # Prompt for details
        details = prompt_for_issue_details(
            jira,
            project_key,
            default_issue_type,
            default_labels,
            default_parent_epic_key,
            default_custom_fields,
        )

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
        parent_epic_key=details.get("parent_epic_key"),
        custom_fields=details.get("custom_fields", {}),
    )

    if not issue_key:
        rprint("[red]Failed to create issue.[/red]")
        return None

    rprint(f"[green]Created issue: {issue_key}[/green]")
    rprint(f"[dim]{jira.base_url}/browse/{issue_key}[/dim]")

    if details["issue_type"].strip().lower() == "epic":
        record_epic_in_history(issue_key, details["summary"], project_key)

    # Save defaults for next time
    should_save = False
    custom_fields_to_save = {}
    parent_epic_to_save = details.get("parent_epic_key")

    # Check if issue type or labels changed
    if (
        details["issue_type"] != default_issue_type
        or details["labels"] != default_labels
        or parent_epic_to_save != default_parent_epic_key
    ):
        should_save = True

    # Check if custom fields changed or are new
    current_custom_fields = details.get("custom_fields", {})
    if current_custom_fields:
        # Check if any custom fields differ from defaults
        for field_id, value in current_custom_fields.items():
            if (
                field_id not in default_custom_fields
                or default_custom_fields[field_id] != value
            ):
                should_save = True
                custom_fields_to_save[field_id] = value
        # Also include unchanged custom fields so we preserve them
        for field_id, value in default_custom_fields.items():
            if field_id not in custom_fields_to_save:
                custom_fields_to_save[field_id] = value

    if should_save:
        if save_defaults is None:
            prompt_text = (
                "Save issue type, labels, and custom fields as defaults?"
                if custom_fields_to_save
                else "Save issue type, labels, and parent epic as defaults?"
            )
            resolved_save_defaults = Confirm.ask(prompt_text, default=True)
        else:
            resolved_save_defaults = save_defaults

        if resolved_save_defaults:
            save_issue_defaults(
                repo_root,
                details["issue_type"],
                details["labels"],
                parent_epic_to_save,
                custom_fields_to_save if custom_fields_to_save else None,
            )

    return issue_key
