
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import os

from pwm.config.models import PWMConfig
import tomllib as _toml

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

def load_merged_config(repo_root: Path):
    from pwm.context.resolver import ContextMeta

    base = PWMConfig().as_dict()
    user_cfg, project_cfg = {}, {}

    if USER_CONFIG_PATH.exists():
        user_cfg = _load_toml(USER_CONFIG_PATH)
    project_cfg_path = repo_root / PROJECT_CONFIG_BASENAME
    if project_cfg_path.exists():
        project_cfg = _load_toml(project_cfg_path)

    merged = _deep_merge(base, user_cfg)
    merged = _deep_merge(merged, project_cfg)

    env_overrides = {}
    if token := os.getenv("PWM_JIRA_TOKEN"):
        env_overrides.setdefault("jira", {})["token"] = token
    if base_url := os.getenv("PWM_JIRA_BASE_URL"):
        env_overrides.setdefault("jira", {})["base_url"] = base_url
    if email := os.getenv("PWM_JIRA_EMAIL"):
        env_overrides.setdefault("jira", {})["email"] = email
    if gh_token := os.getenv("GITHUB_TOKEN") or os.getenv("PWM_GITHUB_TOKEN"):
        env_overrides.setdefault("github", {})["token"] = gh_token
    if openai_key := os.getenv("PWM_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"):
        env_overrides.setdefault("openai", {})["api_key"] = openai_key

    merged = _deep_merge(merged, env_overrides)
    meta = ContextMeta(
        user_config_path=USER_CONFIG_PATH if USER_CONFIG_PATH.exists() else None,
        project_config_path=project_cfg_path if project_cfg_path.exists() else None,
        source_summary="+".join(filter(None, ["user" if user_cfg else None, "project" if project_cfg else None, "env" if env_overrides else None])) or "defaults",
    )
    return merged, meta
