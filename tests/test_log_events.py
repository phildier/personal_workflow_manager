import json

from pwm.log import events


def test_append_event_writes_jsonl_and_normalizes_values(tmp_path, monkeypatch):
    log_dir = tmp_path / "pwm"
    log_file = log_dir / "log.jsonl"
    monkeypatch.setattr(events, "LOG_DIR", log_dir)
    monkeypatch.setattr(events, "LOG_FILE", log_file)

    events.append_event(
        command="pr",
        args={
            "title": "short",
            "body": "x" * 200,
            "token": "secret-token",
        },
        details={
            "status": "success",
            "description": "y" * 180,
        },
    )

    lines = log_file.read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])

    assert row["command"] == "pr"
    assert row["args"]["title"] == "short"
    assert row["args"]["token"] == "<redacted>"
    assert row["args"]["body"].endswith("...")
    assert row["details"]["description"].endswith("...")


def test_append_event_rotates_file_when_max_size_exceeded(tmp_path, monkeypatch):
    log_dir = tmp_path / "pwm"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "log.jsonl"
    log_file.write_text("old-line\n")

    monkeypatch.setattr(events, "LOG_DIR", log_dir)
    monkeypatch.setattr(events, "LOG_FILE", log_file)

    events.append_event(
        command="ws",
        args={"new": True},
        details={"status": "success"},
        max_bytes=1,
    )

    rotated = [p for p in log_dir.iterdir() if p.name.startswith("log-")]
    assert rotated, "Expected rotated log file"
    assert log_file.exists()

    new_lines = log_file.read_text().splitlines()
    assert len(new_lines) == 1
    row = json.loads(new_lines[0])
    assert row["command"] == "ws"
