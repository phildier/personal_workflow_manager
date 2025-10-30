from __future__ import annotations
from pathlib import Path
from typing import Tuple, Dict, Any
import os

from pwm.config.models import PWMConfig

try:  # Python 3.11+
    import tomllib as _toml
except Exception:  # pragma: no cover
    import tomli as _toml  # type: ignore

USER_CONFIG_PATH = Path.home() / ".config" / "pwm" / "config.toml"
PROJECT_CONFIG_BASENAME = ".pwm.toml"

def _load_toml(path: Path) -> Dict[str, Any]:
    with path.open("rb") as f:
        return _toml.load(f)

def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def load_merged_config(repo_root: Path) -> tuple[Dict[str, Any], "ContextMeta"]:
    from pwm.context.resolver import ContextMeta  # local import to avoid cycle

    # 1) Defaults from model
    base = PWMConfig().as_dict()

    # 2) User config
    user_cfg: Dict[str, Any] = {}
    if USER_CONFIG_PATH.exists():
        user_cfg = _load_toml(USER_CONFIG_PATH)

    # 3) Project config
    project_cfg_path = repo_root / PROJECT_CONFIG_BASENAME
    project_cfg: Dict[str, Any] = {}
    if project_cfg_path.exists():
        project_cfg = _load_toml(project_cfg_path)

    merged = _deep_merge(base, user_cfg)
    merged = _deep_merge(merged, project_cfg)

    # 4) Env overrides for common secrets/toggles
    env_overrides: Dict[str, Any] = {}
    _set(env_overrides, "jira.token", os.getenv("PWM_JIRA_TOKEN"))
    _set(env_overrides, "jira.base_url", os.getenv("PWM_JIRA_BASE_URL"))
    _set(env_overrides, "jira.email", os.getenv("PWM_JIRA_EMAIL"))
    _set(env_overrides, "github.token", os.getenv("GITHUB_TOKEN") or os.getenv("PWM_GITHUB_TOKEN"))

    merged = _deep_merge(merged, env_overrides)

    meta = ContextMeta(
        user_config_path=USER_CONFIG_PATH if USER_CONFIG_PATH.exists() else None,
        project_config_path=project_cfg_path if project_cfg_path.exists() else None,
        source_summary=_source_summary(USER_CONFIG_PATH, project_cfg_path, env_overrides),
    )

    return merged, meta

def _set(d: Dict[str, Any], dotted_key: str, value: Any | None) -> None:
    if value is None:
        return
    parts = dotted_key.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value

def _source_summary(user_path: Path, project_path: Path, env_overrides: Dict[str, Any]) -> str:
    parts = []
    if user_path.exists():
        parts.append("user")
    if project_path.exists():
        parts.append("project")
    if env_overrides:
        parts.append("env")
    return "+".join(parts) if parts else "defaults"
