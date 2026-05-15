from pwm.work.create_issue import (
    build_non_interactive_issue_details,
    parse_custom_field_values,
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
