from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ContextMeta:
    user_config_path: Path | None
    project_config_path: Path | None
    source_summary: str
