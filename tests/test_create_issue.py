import pwm.work.epic_history as epic_history_module
from pwm.work.create_issue import (
    build_non_interactive_issue_details,
    parse_custom_field_values,
    record_epic_in_history,
)


def test_parse_custom_field_values_supports_string_and_json_values():
    values = parse_custom_field_values(
        [
            "customfield_100=plain-text",
            'customfield_200={"value":"Platform"}',
            "customfield_300=42",
            "customfield_400=[1,2,3]",
        ]
    )

    assert values["customfield_100"] == "plain-text"
    assert values["customfield_200"] == {"value": "Platform"}
    assert values["customfield_300"] == 42
    assert values["customfield_400"] == [1, 2, 3]


def test_parse_custom_field_values_rejects_invalid_pair():
    try:
        parse_custom_field_values(["bad-format"])
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Expected KEY=VALUE" in str(exc)


def test_build_non_interactive_issue_details_uses_defaults_and_overrides():
    class FakeJira:
        def get_create_metadata(self, _project_key, _issue_type):
            return {
                "customfield_team": {
                    "name": "Responsible Team",
                    "required": True,
                    "schema": {"type": "option"},
                },
                "customfield_points": {
                    "name": "Story Points",
                    "required": False,
                    "schema": {"type": "number"},
                },
            }

    config = {
        "jira": {
            "issue_defaults": {
                "issue_type": "Story",
                "labels": ["backend"],
                "custom_fields": {"customfield_team": {"value": "Platform"}},
            }
        }
    }

    details = build_non_interactive_issue_details(
        jira=FakeJira(),
        project_key="ABC",
        config=config,
        summary="Automate issue creation",
        description="No prompts",
        issue_type=None,
        labels=None,
        story_points=8.0,
        custom_fields={"customfield_extra": "x"},
    )

    assert details is not None
    assert details["issue_type"] == "Story"
    assert details["labels"] == ["backend"]
    assert details["custom_fields"]["customfield_team"] == {"value": "Platform"}
    assert details["custom_fields"]["customfield_points"] == 8.0
    assert details["custom_fields"]["customfield_extra"] == "x"


def test_build_non_interactive_issue_details_fails_on_missing_required_fields():
    class FakeJira:
        def get_create_metadata(self, _project_key, _issue_type):
            return {
                "customfield_team": {
                    "name": "Responsible Team",
                    "required": True,
                    "schema": {"type": "option"},
                }
            }

    details = build_non_interactive_issue_details(
        jira=FakeJira(),
        project_key="ABC",
        config={"jira": {"issue_defaults": {}}},
        summary="Automate issue creation",
    )

    assert details is None


def test_build_non_interactive_issue_details_includes_parent_epic_for_task():
    class FakeJira:
        def get_create_metadata(self, _project_key, _issue_type):
            return {}

    details = build_non_interactive_issue_details(
        jira=FakeJira(),
        project_key="ABC",
        config={"jira": {"issue_defaults": {}}},
        summary="Task with parent",
        issue_type="Task",
        parent_epic_key="ABC-777",
    )

    assert details is not None
    assert details["parent_epic_key"] == "ABC-777"


def test_build_non_interactive_issue_details_ignores_parent_for_epic_type():
    class FakeJira:
        def get_create_metadata(self, _project_key, _issue_type):
            return {}

    details = build_non_interactive_issue_details(
        jira=FakeJira(),
        project_key="ABC",
        config={"jira": {"issue_defaults": {}}},
        summary="Epic item",
        issue_type="Epic",
        parent_epic_key="ABC-777",
    )

    assert details is not None
    assert details["parent_epic_key"] is None


def test_record_epic_in_history_dedupes_and_updates_latest(monkeypatch, tmp_path):
    history_file = tmp_path / "epic_history.json"
    monkeypatch.setattr(epic_history_module, "EPIC_HISTORY_FILE", history_file)

    record_epic_in_history("ABC-1", "First epic", "ABC")
    record_epic_in_history("ABC-2", "Second epic", "ABC")
    record_epic_in_history("ABC-1", "First epic renamed", "ABC")

    saved = history_file.read_text(encoding="utf-8")
    assert "ABC-1" in saved
    assert "First epic renamed" in saved

    data = epic_history_module.load_epic_history()
    assert len(data) == 2
    assert data[0]["key"] == "ABC-1"
