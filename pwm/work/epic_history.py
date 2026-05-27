from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Optional

from rich import print as rprint
from rich.prompt import Confirm
from rich.table import Table

from pwm.context.resolver import resolve_context
from pwm.jira.client import JiraClient


EPIC_HISTORY_FILE = Path.home() / ".config" / "pwm" / "epic_history.json"
MAX_EPIC_HISTORY_ITEMS = 200
ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


def load_epic_history() -> list[dict]:
    """Load epic history entries from disk."""
    if not EPIC_HISTORY_FILE.exists():
        return []

    try:
        with EPIC_HISTORY_FILE.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    history: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        title = str(item.get("title", "")).strip()
        project_key = str(item.get("project_key", "")).strip()
        if not key or not title:
            continue
        history.append(
            {
                "key": key,
                "title": title,
                "project_key": project_key,
                "updated_at": str(item.get("updated_at", "")),
            }
        )

    return history


def save_epic_history(history: list[dict]) -> None:
    """Persist epic history to disk (best effort)."""
    try:
        EPIC_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with EPIC_HISTORY_FILE.open("w", encoding="utf-8") as file_obj:
            json.dump(history[:MAX_EPIC_HISTORY_ITEMS], file_obj, ensure_ascii=True)
    except OSError:
        return


def upsert_epic_history(epic_key: str, title: str, project_key: str) -> None:
    """Insert or refresh an epic in history."""
    cleaned_key = epic_key.strip()
    cleaned_title = title.strip()
    cleaned_project_key = project_key.strip()
    if not cleaned_key or not cleaned_title:
        return

    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    existing = load_epic_history()

    deduped = [entry for entry in existing if entry.get("key") != cleaned_key]
    deduped.insert(
        0,
        {
            "key": cleaned_key,
            "title": cleaned_title,
            "project_key": cleaned_project_key,
            "updated_at": updated_at,
        },
    )
    save_epic_history(deduped)


def clear_epic_history() -> None:
    """Clear history file contents."""
    if not EPIC_HISTORY_FILE.exists():
        return
    try:
        EPIC_HISTORY_FILE.unlink()
    except OSError:
        return


def _get_repo_default_parent_epic_key() -> Optional[str]:
    """Read parent epic default from local project config when available."""
    try:
        context = resolve_context()
    except Exception:
        return None

    config_path = context.repo_root / ".pwm.toml"
    if not config_path.exists():
        return None

    import tomllib

    try:
        with config_path.open("rb") as file_obj:
            data = tomllib.load(file_obj)
    except OSError:
        return None

    return data.get("jira", {}).get("issue_defaults", {}).get("parent_epic_key")


def _set_repo_default_parent_epic_key(epic_key: str) -> bool:
    """Set local project default parent epic key."""
    try:
        context = resolve_context()
    except Exception:
        return False

    config_path = context.repo_root / ".pwm.toml"
    existing_config = {}

    if config_path.exists():
        import tomllib

        try:
            with config_path.open("rb") as file_obj:
                existing_config = tomllib.load(file_obj)
        except OSError:
            return False

    if "jira" not in existing_config:
        existing_config["jira"] = {}
    if "issue_defaults" not in existing_config["jira"]:
        existing_config["jira"]["issue_defaults"] = {}

    existing_config["jira"]["issue_defaults"]["parent_epic_key"] = epic_key

    import toml

    try:
        with config_path.open("w", encoding="utf-8") as file_obj:
            toml.dump(existing_config, file_obj)
    except OSError:
        return False

    return True


def _clear_repo_default_parent_epic_key() -> bool:
    """Clear local project default parent epic key."""
    try:
        context = resolve_context()
    except Exception:
        return False

    config_path = context.repo_root / ".pwm.toml"
    if not config_path.exists():
        return True

    import tomllib
    import toml

    try:
        with config_path.open("rb") as file_obj:
            existing_config = tomllib.load(file_obj)
    except OSError:
        return False

    issue_defaults = existing_config.get("jira", {}).get("issue_defaults", {})
    issue_defaults.pop("parent_epic_key", None)

    try:
        with config_path.open("w", encoding="utf-8") as file_obj:
            toml.dump(existing_config, file_obj)
    except OSError:
        return False

    return True


def _lookup_epic_in_jira(epic_key: str) -> Optional[dict]:
    """Fetch epic details from Jira for cache hydration."""
    try:
        context = resolve_context()
    except Exception:
        return None

    jira = JiraClient.from_config(context.config)
    if not jira:
        return None

    issue = jira.get_issue(epic_key)
    if not issue:
        return None

    fields = issue.get("fields", {})
    issue_type_name = str((fields.get("issuetype") or {}).get("name", ""))
    if issue_type_name.strip().lower() != "epic":
        return None

    title = str(fields.get("summary", "")).strip()
    project_key = str((fields.get("project") or {}).get("key", "")).strip()
    if not title:
        return None

    return {
        "key": epic_key,
        "title": title,
        "project_key": project_key,
    }


def epic_history_command(
    project: Optional[str] = None,
    limit: int = 50,
    as_json: bool = False,
    clear: bool = False,
    yes: bool = False,
    set_default: Optional[str] = None,
    clear_default: bool = False,
) -> int:
    """Show or clear epic history cache."""
    if clear and set_default:
        rprint("[red]Error: --clear cannot be used with --set-default.[/red]")
        return 1
    if clear and clear_default:
        rprint("[red]Error: --clear cannot be used with --clear-default.[/red]")
        return 1
    if set_default and clear_default:
        rprint("[red]Error: --set-default cannot be used with --clear-default.[/red]")
        return 1

    if set_default:
        normalized_key = set_default.strip().upper()
        if not ISSUE_KEY_PATTERN.match(normalized_key):
            rprint("[red]Error: Invalid Jira key format for --set-default.[/red]")
            return 1

        entries = load_epic_history()
        in_cache = any(
            entry.get("key", "").upper() == normalized_key for entry in entries
        )

        if not in_cache:
            jira_epic = _lookup_epic_in_jira(normalized_key)
            if not jira_epic:
                rprint(
                    "[red]Error: Epic not found in cache and Jira lookup failed "
                    f"for {normalized_key}.[/red]"
                )
                rprint(
                    "[dim]Ensure Jira is configured and the key exists as an Epic.[/dim]"
                )
                return 1

            upsert_epic_history(
                jira_epic["key"],
                jira_epic["title"],
                jira_epic.get("project_key", ""),
            )
            rprint(
                "[cyan]Fetched epic from Jira and added to cache:[/cyan] "
                f"{normalized_key}"
            )

        if not _set_repo_default_parent_epic_key(normalized_key):
            rprint("[red]Error: Failed to save local default parent epic.[/red]")
            return 1

        rprint(f"[green]Default parent epic set to {normalized_key}.[/green]")
        return 0

    if clear_default:
        if not _clear_repo_default_parent_epic_key():
            rprint("[red]Error: Failed to clear local default parent epic.[/red]")
            return 1
        rprint("[green]Default parent epic cleared.[/green]")
        return 0

    if clear:
        if not yes and not Confirm.ask("Clear epic history cache?", default=False):
            rprint("[yellow]Cancelled.[/yellow]")
            return 1
        clear_epic_history()
        rprint("[green]Epic history cleared.[/green]")
        return 0

    entries = load_epic_history()
    if project:
        project_upper = project.strip().upper()
        entries = [
            entry for entry in entries if entry.get("project_key", "").upper() == project_upper
        ]

    if limit > 0:
        entries = entries[:limit]

    default_parent = _get_repo_default_parent_epic_key()
    for entry in entries:
        entry["is_default"] = bool(
            default_parent and entry.get("key", "").upper() == default_parent.upper()
        )

    if as_json:
        print(json.dumps(entries, ensure_ascii=True))
        return 0

    if not entries:
        rprint("[yellow]No epic history found.[/yellow]")
        rprint(f"[dim]Cache file: {EPIC_HISTORY_FILE}[/dim]")
        return 0

    table = Table(title="pwm epic history")
    table.add_column("Key", style="bold cyan")
    table.add_column("Title", style="white")
    table.add_column("Project", style="magenta")
    table.add_column("Updated", style="dim")
    table.add_column("Default", style="green")
    for entry in entries:
        table.add_row(
            entry.get("key", ""),
            entry.get("title", ""),
            entry.get("project_key", ""),
            entry.get("updated_at", ""),
            "yes" if entry.get("is_default") else "",
        )
    rprint(table)
    rprint(f"[dim]Cache file: {EPIC_HISTORY_FILE}[/dim]")
    return 0
