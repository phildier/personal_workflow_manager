from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


AGENT_DEFAULTS_PATH = Path.home() / ".config" / "pwm" / "agent-defaults.toml"
VALID_REPORTER_BEHAVIORS = {"auto", "self", "none"}


@dataclass(frozen=True)
class AgentDefaultsResolution:
    """Resolved agent-defaults payload for Jira issue creation."""

    overrides: dict[str, Any]
    warning: str | None = None


def _is_matching_rule(
    rule: dict[str, Any],
    project_key: str | None,
    repository_candidates: set[str],
) -> tuple[bool, int]:
    """Return whether a rule matches and its specificity score."""
    score = 0

    rule_project = rule.get("project")
    if rule_project is not None:
        if not isinstance(rule_project, str):
            return False, 0
        if not project_key or rule_project.upper() != project_key.upper():
            return False, 0
        score += 1

    rule_repository = rule.get("repository")
    if rule_repository is not None:
        if not isinstance(rule_repository, str):
            return False, 0
        if rule_repository.lower() not in repository_candidates:
            return False, 0
        score += 1

    if score == 0:
        return False, 0
    return True, score


def _to_label_list(raw_value: Any) -> list[str] | None:
    """Convert a raw labels value into a normalized label list."""
    if raw_value is None:
        return None
    if not isinstance(raw_value, list):
        return None

    out: list[str] = []
    for item in raw_value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped:
            out.append(stripped)
    return out


def _extract_rule_overrides(rule: dict[str, Any]) -> dict[str, Any]:
    """Extract supported issue-default fields from a matching rule."""
    overrides: dict[str, Any] = {}

    issue_type = rule.get("issue_type")
    if isinstance(issue_type, str) and issue_type.strip():
        overrides["issue_type"] = issue_type.strip()

    labels = _to_label_list(rule.get("labels"))
    if labels is not None:
        overrides["labels"] = labels

    reporter = rule.get("reporter")
    if isinstance(reporter, str):
        normalized = reporter.strip().lower()
        if normalized in VALID_REPORTER_BEHAVIORS:
            overrides["reporter_behavior"] = normalized

    custom_fields: dict[str, Any] = {}
    raw_custom_fields = rule.get("custom_fields")
    if isinstance(raw_custom_fields, dict):
        for field_id, value in raw_custom_fields.items():
            if isinstance(field_id, str) and field_id.strip():
                custom_fields[field_id.strip()] = value

    responsible_team = rule.get("responsible_team")
    if isinstance(responsible_team, dict):
        field_id = responsible_team.get("field")
        value = responsible_team.get("value")
        if isinstance(field_id, str) and field_id.strip() and value is not None:
            custom_fields[field_id.strip()] = {"value": value}

    if custom_fields:
        overrides["custom_fields"] = custom_fields

    return overrides


def load_agent_jira_defaults(
    project_key: str | None,
    github_repo: str | None,
    repo_name: str,
) -> AgentDefaultsResolution:
    """Load a matching Jira defaults profile from agent-defaults.toml."""
    if not AGENT_DEFAULTS_PATH.exists():
        return AgentDefaultsResolution(overrides={})

    try:
        with AGENT_DEFAULTS_PATH.open("rb") as fh:
            doc = tomllib.load(fh)
    except tomllib.TOMLDecodeError:
        return AgentDefaultsResolution(
            overrides={},
            warning=(
                "Ignoring malformed agent defaults file "
                f"at {AGENT_DEFAULTS_PATH}."
            ),
        )
    except OSError:
        return AgentDefaultsResolution(
            overrides={},
            warning=(
                "Unable to read agent defaults file "
                f"at {AGENT_DEFAULTS_PATH}; continuing without it."
            ),
        )

    rules = doc.get("defaults")
    if rules is None:
        return AgentDefaultsResolution(overrides={})
    if not isinstance(rules, list):
        return AgentDefaultsResolution(
            overrides={},
            warning=(
                "Ignoring agent defaults because 'defaults' must be an array "
                "of tables."
            ),
        )

    repository_candidates = {repo_name.lower()}
    if github_repo:
        repository_candidates.add(github_repo.lower())

    best_rule: dict[str, Any] | None = None
    best_score = -1
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        is_match, score = _is_matching_rule(
            rule,
            project_key=project_key,
            repository_candidates=repository_candidates,
        )
        if not is_match:
            continue
        if score >= best_score:
            best_rule = rule
            best_score = score

    if not best_rule:
        return AgentDefaultsResolution(overrides={})

    return AgentDefaultsResolution(overrides=_extract_rule_overrides(best_rule))
