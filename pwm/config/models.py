from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class JiraConfig(BaseModel):
    base_url: Optional[str] = None
    email: Optional[str] = None
    token: Optional[str] = None  # can be read from env
    project_key: Optional[str] = None

class GithubConfig(BaseModel):
    base_url: Optional[str] = None
    token: Optional[str] = None
    default_org: Optional[str] = None
    repo: Optional[str] = None  # org/repo override

class GitConfig(BaseModel):
    default_remote: str = "origin"

class BranchConfig(BaseModel):
    pattern: str = "feature/{issue_key}-{slug}"

class UIConfig(BaseModel):
    editor: Optional[str] = None

class PWMConfig(BaseModel):
    jira: JiraConfig = Field(default_factory=JiraConfig)
    github: GithubConfig = Field(default_factory=GithubConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    branch: BranchConfig = Field(default_factory=BranchConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
